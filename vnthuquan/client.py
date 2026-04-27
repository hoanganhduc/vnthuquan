"""High-level public client."""

from __future__ import annotations

import json
import os
import re
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .adapter import FORMAT_IDS, LegacySiteAdapter
from .archive import DownloadArchive, record_from_result, resolve_archive_path
from .config import Config, default_cache_path, load_config, resolve_download_dir
from .errors import (
    AmbiguousResultError,
    AssetDiscoveryError,
    ConfigError,
    DownloadError,
    FilesystemError,
    LiveCheckError,
    NotFoundError,
    SearchError,
    UnsupportedFormatError,
    ValidationError,
)
from .external_validators import validate_external as run_external_validators
from .mirrors import list_mirrors, normalize_mirror
from .models import (
    Author,
    BookMetadata,
    Category,
    DownloadArchiveRecord,
    DownloadPlan,
    DownloadQueue,
    DownloadQueueItem,
    DownloadResult,
    ExternalValidationResult,
    FormatCategory,
    LinkInfo,
    MirrorStatus,
    ResourceProfile,
    SearchResult,
)
from .queue import make_queue, read_queue, write_queue
from .resources import detect_resources, resolve_jobs
from .validators import validate_file

EPUB_VALIDATION_CHECKS = [
    "byte count matches Content-Length when available",
    "SHA256 is computed",
    "EPUB ZIP opens",
    "mimetype is application/epub+zip",
    "META-INF/container.xml exists",
    "OPF package exists",
    "manifest and spine files are readable",
    "TOC/nav is reported when available",
    "demo/sample markers are scanned heuristically",
]

PDF_VALIDATION_CHECKS = [
    "byte count matches Content-Length when available",
    "SHA256 is computed",
    "PDF header is present",
    "PDF EOF marker is reported when available",
    "content is large enough to be readable",
]

TEXT_VALIDATION_CHECKS = [
    "SHA256 is computed",
    "generated file is valid UTF-8",
    "text is non-empty and large enough to be readable",
    "demo/sample markers are scanned heuristically",
]

AUDIO_VALIDATION_CHECKS = [
    "SHA256 is computed",
    "audio bundle ZIP opens",
    "bundle contains MP3 files",
    "each MP3 entry has an MP3 header",
]

DOWNLOAD_EXTENSIONS = {
    "epub": ".epub",
    "pdf": ".pdf",
    "text": ".txt",
    "audio": ".zip",
}

DOWNLOAD_VALIDATION_CHECKS = {
    "epub": EPUB_VALIDATION_CHECKS,
    "pdf": PDF_VALIDATION_CHECKS,
    "text": TEXT_VALIDATION_CHECKS,
    "audio": AUDIO_VALIDATION_CHECKS,
}

_FAILOVER_ERRORS = (
    AssetDiscoveryError,
    DownloadError,
    LiveCheckError,
    NotFoundError,
    SearchError,
    ValidationError,
)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold().strip()


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "book"


def _render_filename_template(template: str, book: BookMetadata, fmt: str) -> str:
    values = {
        "title": book.title,
        "author": book.author or "unknown author",
        "format": fmt,
        "tid": book.tid,
    }
    try:
        rendered = template.format(**values)
    except KeyError as exc:
        allowed = ", ".join(sorted(values))
        raise ConfigError(f"Unsupported filename template field {exc}; allowed: {allowed}") from exc
    return _safe_filename(rendered)


def _filename_from_url(url: str, fallback: str) -> str:
    path = unquote(urlparse(url).path)
    name = Path(path).name
    return _safe_filename(name) if name else fallback


def _unique_filename(name: str, used: set[str]) -> str:
    base = Path(name).stem or "asset"
    suffix = Path(name).suffix
    candidate = name
    counter = 2
    while candidate in used:
        candidate = f"{base}-{counter}{suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def _as_list(value: Any, split_commas: bool = False) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items: list[Any] = []
        for item in value:
            items.extend(_as_list(item, split_commas=split_commas))
        return items
    if split_commas and isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [value]


def _unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _clean_search_title(title: str, fmt: str | None = None) -> str:
    cleaned = re.sub(r"\s+", " ", title).strip(" ,-")
    if fmt:
        cleaned = re.sub(rf"\s*\({re.escape(fmt)}\)\s*$", "", cleaned, flags=re.I)
        cleaned = re.sub(rf"\s+{re.escape(fmt)}\s*$", "", cleaned, flags=re.I)
    return cleaned.strip(" ,-")


def _result_title(result: SearchResult) -> str:
    return _clean_search_title(result.title, result.format)


class VnThuQuanClient:
    """Public wrapper client for Vietnam Thu Quan legacy mirrors."""

    def __init__(
        self,
        mirror: str | None = None,
        config: Config | None = None,
        config_path: str | Path | None = None,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> None:
        self.config = config or load_config(config_path)
        selected_mirror = normalize_mirror(mirror or self.config.default_mirror)
        self._mirror_pinned = mirror is not None
        self._timeout = timeout if timeout is not None else self.config.timeout
        self._retries = retries if retries is not None else self.config.retries
        self.adapter = self._make_adapter(selected_mirror)

    def _make_adapter(self, mirror: str) -> LegacySiteAdapter:
        cache_path = self.config.cache_path
        if self.config.cache_ttl_seconds > 0 and not cache_path:
            cache_path = str(default_cache_path())
        return LegacySiteAdapter(
            mirror=mirror,
            timeout=self._timeout,
            retries=self._retries,
            cache_ttl=self.config.cache_ttl_seconds,
            cache_path=cache_path,
            request_interval=self.config.request_interval_seconds,
            retry_backoff=self.config.retry_backoff_seconds,
            retry_jitter=self.config.retry_jitter_seconds,
        )

    def _worker_client(self, jobs: int = 1, search: bool = False) -> "VnThuQuanClient":
        config = self.config
        if jobs > 1:
            resources = detect_resources()
            interval = resources.suggested_request_interval_seconds
            if search:
                interval = max(interval, 0.2)
            config = replace(
                self.config,
                request_interval_seconds=max(self.config.request_interval_seconds, interval),
                cache_ttl_seconds=0.0,
                cache_path=None,
            )
        return VnThuQuanClient(
            mirror=self.mirror,
            config=config,
            timeout=self._timeout,
            retries=self._retries,
        )

    def _resolve_search_jobs(self, jobs: str | int | None) -> int:
        if jobs is None:
            return 1
        if isinstance(jobs, str) and jobs.casefold().strip() == "auto":
            return detect_resources().suggested_search_jobs
        return max(int(jobs), 1)

    def _collect_parallel(
        self,
        values: list[Any],
        jobs: str | int | None,
        callback,
    ) -> list[Any]:
        resolved_jobs = self._resolve_search_jobs(jobs)
        if resolved_jobs <= 1 or len(values) <= 1:
            results: list[Any] = []
            for value in values:
                results.extend(callback(self, value))
            return results
        ordered: list[list[Any] | None] = [None] * len(values)
        with ThreadPoolExecutor(max_workers=resolved_jobs) as pool:
            future_map = {
                pool.submit(callback, self._worker_client(resolved_jobs, search=True), value): idx
                for idx, value in enumerate(values)
            }
            for future in as_completed(future_map):
                ordered[future_map[future]] = future.result()
        results = []
        for chunk in ordered:
            if chunk:
                results.extend(chunk)
        return results

    @property
    def mirror(self) -> str:
        return self.adapter.mirror

    def live_check(self, mirror: str | None = None) -> MirrorStatus:
        adapter = self.adapter if mirror is None else self._make_adapter(normalize_mirror(mirror))
        return adapter.live_check()

    def check_mirrors(self) -> list[MirrorStatus]:
        return [self._make_adapter(mirror).live_check() for mirror in list_mirrors()]

    def search(
        self,
        query: str | list[str] | None = None,
        field: str = "title",
        format: str | list[str] | None = None,
        category: str | int | list[str | int] | None = None,
        author_id: str | int | list[str | int] | None = None,
        titles: str | list[str] | None = None,
        authors: str | list[str] | None = None,
        categories: str | int | list[str | int] | None = None,
        author_ids: str | int | list[str | int] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
        exact: bool = False,
        jobs: str | int | None = None,
    ) -> list[SearchResult]:
        field = field.replace("-", "_").lower()
        format_values = self._normalize_formats(formats if formats is not None else format)
        query_values = [str(value) for value in _as_list(query)]
        title_values = [str(value) for value in _as_list(titles)]
        author_values = [str(value) for value in _as_list(authors)]
        category_values = _as_list(category) + _as_list(categories)
        author_id_values = _as_list(author_id) + _as_list(author_ids)

        if field == "author_id" and not author_id_values:
            author_id_values.extend(query_values)
            query_values = []
        elif field == "category" and not category_values:
            category_values.extend(query_values)
            query_values = []
        elif field == "title":
            title_values.extend(query_values)
            query_values = []
        elif field == "author":
            author_values.extend(query_values)
            query_values = []
        elif field != "all":
            raise NotFoundError(f"Unsupported search field: {field}")

        title_values = [str(value) for value in _unique(title_values)]
        author_values = [str(value) for value in _unique(author_values)]
        query_values = [str(value) for value in _unique(query_values)]
        category_values = _unique(category_values)
        author_id_values = _unique(author_id_values)

        if category_values:
            results = self._collect_parallel(
                category_values,
                jobs,
                lambda client, category_value: client.adapter.list_category_books(
                    category_value,
                    format=format_values,
                    page=page,
                ),
            )
            results = self._filter_author_ids(results, author_id_values)
            results = self._filter_search_results(
                results,
                titles=title_values,
                authors=author_values,
                queries=query_values,
                exact=exact,
            )
            results = self._dedupe_results(results)
            return results[:limit] if limit else results

        if author_id_values:
            results = self._collect_parallel(
                author_id_values,
                jobs,
                lambda client, author_id_value: client.adapter.list_author_books(
                    author_id_value,
                    format=format_values,
                    page=page,
                ),
            )
            results = self._filter_search_results(
                results,
                titles=title_values,
                authors=author_values,
                queries=query_values,
                exact=exact,
            )
            results = self._dedupe_results(results)
            return results[:limit] if limit else results

        if title_values or author_values or query_values:
            if page != 1:
                raise NotFoundError(
                    "Search pagination is only supported for category, author ID, and format listings"
                )
            requests_to_run = (
                [("title", title) for title in title_values]
                + [("author", author) for author in author_values]
                + [("all", value) for value in query_values]
            )
            results = self._collect_parallel(
                requests_to_run,
                jobs,
                lambda client, request: (
                    client.adapter.search(
                        query=request[1],
                        field=request[0],
                        format=format_values,
                    )
                    if request[0] != "all"
                    else [
                        *client.adapter.search(
                            query=request[1],
                            field="title",
                            format=format_values,
                        ),
                        *client.adapter.search(
                            query=request[1],
                            field="author",
                            format=format_values,
                        ),
                    ]
                ),
            )
            results = self._dedupe_results(results)
            results = self._filter_search_results(
                results,
                titles=title_values,
                authors=author_values,
                queries=query_values,
                exact=exact,
            )
            return results[:limit] if limit else results

        if format_values:
            results = self._collect_parallel(
                format_values,
                jobs,
                lambda client, format_value: client.adapter.list_format_books(
                    format=format_value,
                    page=page,
                ),
            )
            results = self._dedupe_results(results)
            return results[:limit] if limit else results

        raise NotFoundError("Search requires a query, --category, --author-id, or --format")

    def _normalize_formats(self, formats: str | list[str] | None = None) -> list[str]:
        values = [str(value).lower() for value in _as_list(formats, split_commas=True)]
        unsupported = [value for value in values if value not in FORMAT_IDS]
        if unsupported:
            raise UnsupportedFormatError(f"Unsupported format: {', '.join(unsupported)}")
        return [str(value) for value in _unique(values)]

    def search_by_title(
        self,
        title: str | list[str],
        exact: bool = False,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        jobs: str | int | None = None,
    ) -> list[SearchResult]:
        return self.search(
            titles=title,
            exact=exact,
            format=format,
            formats=formats,
            limit=limit,
            jobs=jobs,
        )

    def search_by_author(
        self,
        author: str | list[str],
        exact: bool = False,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        jobs: str | int | None = None,
    ) -> list[SearchResult]:
        return self.search(
            authors=author,
            exact=exact,
            format=format,
            formats=formats,
            limit=limit,
            jobs=jobs,
        )

    def search_by_author_id(
        self,
        author_id: str | int | list[str | int],
        query: str | list[str] | None = None,
        field: str = "all",
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
        exact: bool = False,
        jobs: str | int | None = None,
    ) -> list[SearchResult]:
        return self.search(
            query,
            field=field,
            format=format,
            formats=formats,
            author_ids=author_id,
            limit=limit,
            page=page,
            exact=exact,
            jobs=jobs,
        )

    def search_by_category(
        self,
        category: str | int | list[str | int],
        query: str | list[str] | None = None,
        field: str = "all",
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
        exact: bool = False,
        jobs: str | int | None = None,
    ) -> list[SearchResult]:
        return self.search(
            query,
            field=field,
            format=format,
            formats=formats,
            categories=category,
            limit=limit,
            page=page,
            exact=exact,
            jobs=jobs,
        )

    def list_by_format(
        self,
        format: str | list[str],
        limit: int | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        return self.search(None, format=format, limit=limit, page=page)

    def search_all(
        self,
        query: str | list[str],
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        exact: bool = False,
        jobs: str | int | None = None,
    ) -> list[SearchResult]:
        return self.search(
            query,
            field="all",
            format=format,
            formats=formats,
            limit=limit,
            exact=exact,
            jobs=jobs,
        )

    def show(
        self,
        selector: dict[str, str],
        assets: bool = False,
        links: bool = False,
        index: int | None = None,
        exact: bool = False,
    ) -> dict[str, Any]:
        book = self.resolve_book(selector, index=index, exact=exact)
        result: dict[str, Any] = {"book": book}
        if assets or links:
            result["links"] = self.get_asset_links(book)
        return result

    def resolve_book(
        self,
        selector: dict[str, str],
        index: int | None = None,
        exact: bool = False,
        search_format: str | None = None,
    ) -> BookMetadata:
        active = [(key, value) for key, value in selector.items() if value]
        if len(active) != 1:
            raise ValueError("Exactly one selector is required")
        key, value = active[0]
        if key == "url" or key == "id":
            return self.adapter.get_book(value)
        if key != "title":
            raise ValueError(f"Unsupported selector: {key}")
        results = self.search(value, field="title", format=search_format)
        exact_matches = [
            result for result in results if _norm(_result_title(result)) == _norm(value)
        ]
        if exact:
            results = exact_matches
        if not results:
            raise NotFoundError(f"No book found for title: {value}")
        if index is not None:
            try:
                return self.adapter.get_book(results[index].url)
            except IndexError as exc:
                raise NotFoundError(f"Search result index out of range: {index}") from exc
        if len(exact_matches) == 1:
            return self.adapter.get_book(exact_matches[0].url)
        if len(exact_matches) > 1:
            results = exact_matches
        if len(results) > 1:
            preview = "; ".join(
                f"[{idx}] {item.title} - {item.author or 'unknown'}"
                for idx, item in enumerate(results[:10])
            )
            raise AmbiguousResultError(f"Multiple matches found. Use --index N. Matches: {preview}")
        return self.adapter.get_book(results[0].url)

    def _dedupe_results(self, results: list[SearchResult]) -> list[SearchResult]:
        deduped: list[SearchResult] = []
        seen: set[str] = set()
        for result in results:
            key = result.tid or result.url
            if key in seen:
                continue
            seen.add(key)
            deduped.append(result)
        return deduped

    def _filter_search_results(
        self,
        results: list[SearchResult],
        titles: list[str] | None = None,
        authors: list[str] | None = None,
        queries: list[str] | None = None,
        exact: bool = False,
    ) -> list[SearchResult]:
        title_values = titles or []
        author_values = authors or []
        query_values = queries or []
        if not title_values and not author_values and not query_values:
            return results
        return [
            result
            for result in results
            if self._matches_any_search_value(
                result, title_values, author_values, query_values, exact
            )
        ]

    def _filter_author_ids(
        self,
        results: list[SearchResult],
        author_ids: list[Any],
    ) -> list[SearchResult]:
        if not author_ids:
            return results
        wanted = {str(value) for value in author_ids}
        return [
            result
            for result in results
            if result.author_id is not None and str(result.author_id) in wanted
        ]

    def _matches_any_search_value(
        self,
        result: SearchResult,
        titles: list[str],
        authors: list[str],
        queries: list[str],
        exact: bool,
    ) -> bool:
        result_title = _norm(_result_title(result))
        result_author = _norm(result.author) if result.author else None

        for title in titles:
            needle = _norm(title)
            if (result_title == needle) if exact else (needle in result_title):
                return True
        for author in authors:
            if result_author is None:
                continue
            needle = _norm(author)
            if (result_author == needle) if exact else (needle in result_author):
                return True
        for query in queries:
            needle = _norm(query)
            title_match = (result_title == needle) if exact else (needle in result_title)
            author_match = bool(
                result_author
                and ((result_author == needle) if exact else (needle in result_author))
            )
            if title_match or author_match:
                return True
        return False

    def discover_assets(self, book: BookMetadata) -> list[LinkInfo]:
        return self.adapter.discover_links(book)

    def get_asset_links(
        self, book: BookMetadata, formats: list[str] | None = None
    ) -> list[LinkInfo]:
        return self.adapter.discover_links(book, formats=formats)

    def get_download_link(self, book: BookMetadata, format: str = "epub") -> LinkInfo:
        format = format.lower()
        for link in self.get_asset_links(book, formats=[format]):
            if link.kind == "asset" and link.format == format:
                return link
        raise NotFoundError(f"No {format} asset link found for {book.title}")

    def plan_download(
        self,
        selector: dict[str, str],
        format: str = "epub",
        out_dir: str | None = None,
        index: int | None = None,
        exact: bool = False,
        dry_run: bool = True,
        filename_template: str | None = None,
    ) -> DownloadPlan:
        format = format.lower()
        if format not in DOWNLOAD_EXTENSIONS:
            raise UnsupportedFormatError(f"Downloads do not support format: {format}")
        book = self.resolve_book(selector, index=index, exact=exact, search_format=format)
        book_format = (book.format or "").lower()
        if book_format and book_format != format:
            raise UnsupportedFormatError(
                f"Selected book is format '{book_format}', not requested format '{format}'"
            )
        warnings: list[str] = []
        assets: list[LinkInfo] = []
        if format == "text":
            asset = LinkInfo(
                kind="generated_text",
                format="text",
                url=book.url,
                mirror=self.mirror,
                is_direct_asset=False,
                notes=["generated from the site's text chapter reader"],
            )
        elif format == "audio":
            links = self.get_asset_links(book, formats=["audio"])
            assets = [link for link in links if link.kind == "asset" and link.format == "audio"]
            if not assets:
                raise NotFoundError(f"No audio asset links found for {book.title}")
            total_size = None
            known_sizes = [
                asset.content_length for asset in assets if asset.content_length is not None
            ]
            if len(known_sizes) == len(assets):
                total_size = sum(known_sizes)
            asset = LinkInfo(
                kind="asset_bundle",
                format="audio",
                url=book.url,
                mirror=self.mirror,
                content_length=total_size,
                is_direct_asset=False,
                notes=[f"bundle of {len(assets)} MP3 asset(s)"],
            )
        else:
            asset = self.get_download_link(book, format=format)
            assets = [asset]
            if format == "pdf" and asset.restricted_by_site_ui:
                warnings.append("PDF reader marks direct download as restricted by the site UI")
        output_dir = resolve_download_dir(out_dir, self.config)
        filename = _render_filename_template(
            filename_template or self.config.filename_template,
            book,
            format,
        )
        if Path(filename).suffix.lower() != DOWNLOAD_EXTENSIONS[format]:
            filename += DOWNLOAD_EXTENSIONS[format]
        output_path = output_dir / filename
        return DownloadPlan(
            selector={key: value for key, value in selector.items() if value},
            book=book,
            format=format,
            mirror=self.mirror,
            asset=asset,
            output_path=str(output_path),
            partial_path=str(output_path) + ".partial",
            dry_run=dry_run,
            validation_checks=DOWNLOAD_VALIDATION_CHECKS[format],
            assets=assets,
            warnings=warnings,
        )

    def download(
        self,
        selector: dict[str, str],
        format: str = "epub",
        out_dir: str | None = None,
        dry_run: bool = True,
        execute: bool = False,
        index: int | None = None,
        exact: bool = False,
        overwrite: bool = False,
        keep_invalid: bool = False,
        no_verify: bool = False,
        strict_verify: bool = False,
        failover: bool | None = None,
        manifest: str | None = None,
        archive: bool = True,
        archive_path: str | None = None,
        filename_template: str | None = None,
        external_validators: list[str] | None = None,
        external_timeout: float = 120.0,
    ) -> DownloadResult:
        dry_run = not execute
        if dry_run:
            plan = self.plan_download(
                selector,
                format=format,
                out_dir=out_dir,
                index=index,
                exact=exact,
                dry_run=True,
                filename_template=filename_template,
            )
            if manifest:
                queue = make_queue(
                    [
                        DownloadQueueItem(
                            selector=plan.selector,
                            format=plan.format,
                            out_dir=out_dir,
                            index=index,
                            exact=exact,
                            filename_template=filename_template,
                        )
                    ],
                    source={"kind": "single-download-dry-run"},
                )
                write_queue(queue, manifest)
            return DownloadResult(
                ok=True,
                plan=plan,
                manifest_path=str(Path(manifest).expanduser()) if manifest else None,
                warnings=["dry-run: no file downloaded"],
            )

        if failover is None:
            failover = not self._mirror_pinned
        attempted: list[tuple[str, Exception]] = []
        original_adapter = self.adapter
        mirrors = [self.mirror]
        if failover:
            mirrors.extend(
                mirror for mirror in list_mirrors() if normalize_mirror(mirror) != self.mirror
            )
        for attempt_index, mirror in enumerate(mirrors):
            if attempt_index:
                self.adapter = self._make_adapter(mirror)
            try:
                plan = self.plan_download(
                    selector,
                    format=format,
                    out_dir=out_dir,
                    index=index,
                    exact=exact,
                    dry_run=False,
                    filename_template=filename_template,
                )
                result = self._execute_download_plan(
                    plan,
                    format=format,
                    overwrite=overwrite,
                    keep_invalid=keep_invalid,
                    no_verify=no_verify,
                    strict_verify=strict_verify,
                    manifest=manifest,
                    external_validators=external_validators,
                    external_timeout=external_timeout,
                )
                if archive:
                    result.archive_path = str(self.record_download(result, archive_path))
                if attempted:
                    failed = "; ".join(f"{mirror}: {exc}" for mirror, exc in attempted)
                    result.warnings.append(
                        f"download succeeded after mirror failover; previous failures: {failed}"
                    )
                return result
            except _FAILOVER_ERRORS as exc:
                attempted.append((mirror, exc))
                if not failover:
                    raise
                continue
            except Exception:
                if attempt_index:
                    self.adapter = original_adapter
                raise
        self.adapter = original_adapter
        failed = "; ".join(f"{mirror}: {exc}" for mirror, exc in attempted)
        raise DownloadError(f"Download failed on all attempted mirrors: {failed}")

    def record_download(
        self,
        result: DownloadResult,
        archive_path: str | Path | None = None,
    ) -> Path:
        path = resolve_archive_path(archive_path, self.config)
        archive = DownloadArchive(path)
        archive.append(record_from_result(result))
        return path

    def list_archive(
        self,
        archive_path: str | Path | None = None,
        limit: int | None = None,
    ) -> list[DownloadArchiveRecord]:
        return DownloadArchive(resolve_archive_path(archive_path, self.config)).read(limit=limit)

    def build_download_queue(
        self,
        format: str = "epub",
        out_dir: str | None = None,
        query: str | list[str] | None = None,
        category: str | int | list[str | int] | None = None,
        author_id: str | int | list[str | int] | None = None,
        limit: int | None = None,
        page: int = 1,
        pages: int = 1,
        filename_template: str | None = None,
    ) -> DownloadQueue:
        if pages < 1:
            raise NotFoundError("pages must be >= 1")
        results: list[SearchResult] = []
        per_page_limit = None if pages > 1 else limit
        for page_number in range(page, page + pages):
            results.extend(
                self.search(
                    query=query,
                    field="all",
                    format=format,
                    categories=category,
                    author_ids=author_id,
                    limit=per_page_limit,
                    page=page_number,
                )
            )
            if limit and len(results) >= limit:
                break
        results = self._dedupe_results(results)
        if limit:
            results = results[:limit]
        items = [
            DownloadQueueItem(
                selector={"url": result.url},
                format=format,
                out_dir=out_dir,
                filename_template=filename_template,
            )
            for result in results
        ]
        return make_queue(
            items,
            source={
                "kind": "download-all",
                "query": query,
                "category": category,
                "author_id": author_id,
                "format": format,
                "limit": limit,
                "page": page,
                "pages": pages,
            },
        )

    def write_queue_manifest(self, queue: DownloadQueue, path: str | Path) -> Path:
        return write_queue(queue, path)

    def read_queue_manifest(self, path: str | Path) -> DownloadQueue:
        return read_queue(path)

    def download_from_manifest(
        self,
        path: str | Path,
        execute: bool = False,
        jobs: str | int | None = 1,
        overwrite: bool = False,
        keep_invalid: bool = False,
        no_verify: bool = False,
        strict_verify: bool = False,
        failover: bool | None = None,
        archive: bool = True,
        archive_path: str | None = None,
        external_validators: list[str] | None = None,
        external_timeout: float = 120.0,
        progress_callback=None,
    ) -> list[DownloadResult]:
        return self.download_queue(
            self.read_queue_manifest(path),
            execute=execute,
            jobs=jobs,
            overwrite=overwrite,
            keep_invalid=keep_invalid,
            no_verify=no_verify,
            strict_verify=strict_verify,
            failover=failover,
            archive=archive,
            archive_path=archive_path,
            external_validators=external_validators,
            external_timeout=external_timeout,
            progress_callback=progress_callback,
        )

    def download_queue(
        self,
        queue: DownloadQueue,
        execute: bool = False,
        jobs: str | int | None = 1,
        overwrite: bool = False,
        keep_invalid: bool = False,
        no_verify: bool = False,
        strict_verify: bool = False,
        failover: bool | None = None,
        archive: bool = True,
        archive_path: str | None = None,
        external_validators: list[str] | None = None,
        external_timeout: float = 120.0,
        progress_callback=None,
    ) -> list[DownloadResult]:
        resolved_jobs = resolve_jobs(jobs, default=1)
        if not execute:
            resolved_jobs = 1
        if resolved_jobs == 1:
            results = []
            total = len(queue.items)
            for idx, item in enumerate(queue.items, start=1):
                result = self.download(
                    item.selector,
                    format=item.format,
                    out_dir=item.out_dir,
                    execute=execute,
                    overwrite=overwrite,
                    keep_invalid=keep_invalid,
                    no_verify=no_verify,
                    strict_verify=strict_verify,
                    failover=failover,
                    archive=False,
                    filename_template=item.filename_template,
                    index=item.index,
                    exact=item.exact,
                    external_validators=external_validators,
                    external_timeout=external_timeout,
                )
                results.append(result)
                if progress_callback:
                    progress_callback(idx, total, result)
        else:
            resources = detect_resources()
            worker_config = replace(
                self.config,
                request_interval_seconds=max(
                    self.config.request_interval_seconds,
                    resources.suggested_request_interval_seconds,
                ),
                cache_ttl_seconds=0.0,
                cache_path=None,
            )

            def run_item(item: DownloadQueueItem) -> DownloadResult:
                worker = VnThuQuanClient(
                    mirror=self.mirror,
                    config=worker_config,
                    timeout=self._timeout,
                    retries=self._retries,
                )
                return worker.download(
                    item.selector,
                    format=item.format,
                    out_dir=item.out_dir,
                    execute=True,
                    overwrite=overwrite,
                    keep_invalid=keep_invalid,
                    no_verify=no_verify,
                    strict_verify=strict_verify,
                    failover=failover,
                    archive=False,
                    filename_template=item.filename_template,
                    index=item.index,
                    exact=item.exact,
                    external_validators=external_validators,
                    external_timeout=external_timeout,
                )

            results = []
            with ThreadPoolExecutor(max_workers=resolved_jobs) as pool:
                future_map = {
                    pool.submit(run_item, item): idx for idx, item in enumerate(queue.items)
                }
                ordered: list[DownloadResult | None] = [None] * len(queue.items)
                for future in as_completed(future_map):
                    idx = future_map[future]
                    result = future.result()
                    ordered[idx] = result
                    if progress_callback:
                        progress_callback(
                            len([item for item in ordered if item is not None]),
                            len(queue.items),
                            result,
                        )
                results = [result for result in ordered if result is not None]
        if archive and execute:
            for result in results:
                result.archive_path = str(self.record_download(result, archive_path))
        return results

    def detect_resources(self) -> ResourceProfile:
        return detect_resources()

    def validate_external(
        self,
        path: str | Path,
        validators: list[str],
        timeout: float = 120.0,
    ) -> list[ExternalValidationResult]:
        return run_external_validators(path, validators, timeout=timeout)

    def _execute_download_plan(
        self,
        plan: DownloadPlan,
        format: str,
        overwrite: bool,
        keep_invalid: bool,
        no_verify: bool,
        strict_verify: bool,
        manifest: str | None,
        external_validators: list[str] | None,
        external_timeout: float,
    ) -> DownloadResult:
        output_path = Path(plan.output_path)
        partial_path = Path(plan.partial_path)
        if output_path.exists() and not overwrite:
            existing_validation = validate_file(output_path, format=format)
            if existing_validation.ok:
                return DownloadResult(
                    ok=True,
                    plan=plan,
                    path=str(output_path),
                    skipped=True,
                    validation=existing_validation,
                    warnings=["existing valid file skipped; use --overwrite to replace"],
                )
            raise FilesystemError(f"Output file already exists: {output_path}")

        if output_path.exists() and overwrite:
            output_path.unlink()
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FilesystemError(
                f"Could not create output directory {output_path.parent}: {exc}"
            ) from exc

        try:
            partial_path.unlink(missing_ok=True)
            expected_size = self._write_download_partial(plan, partial_path)
        except Exception as exc:
            if partial_path.exists() and not keep_invalid:
                partial_path.unlink(missing_ok=True)
            if isinstance(exc, DownloadError):
                raise
            raise DownloadError(f"Download failed: {exc}") from exc

        validation = None
        if not no_verify:
            validation = validate_file(
                partial_path, format=format, expected_size=expected_size, strict=strict_verify
            )
            if not validation.ok:
                if not keep_invalid:
                    partial_path.unlink(missing_ok=True)
                raise ValidationError("; ".join(validation.errors) or "validation failed")

        os.replace(partial_path, output_path)
        if validation:
            validation.path = str(output_path)
        external_results = []
        if external_validators:
            external_results = self.validate_external(
                output_path, external_validators, timeout=external_timeout
            )
            failed = [item for item in external_results if not item.ok]
            if failed:
                if not keep_invalid:
                    output_path.unlink(missing_ok=True)
                messages = [item.error or item.stderr or f"{item.name} failed" for item in failed]
                raise ValidationError("; ".join(messages))
        result = DownloadResult(ok=True, plan=plan, path=str(output_path), validation=validation)
        if external_results:
            result.warnings.extend(
                f"external validator {item.name} passed" for item in external_results if item.ok
            )
        if manifest:
            result.manifest_path = str(Path(manifest).expanduser())
            self.write_manifest(result, manifest)
        return result

    def _write_download_partial(self, plan: DownloadPlan, partial_path: Path) -> int | None:
        if plan.format == "text":
            text = self.adapter.export_text(plan.book)
            partial_path.write_text(text, encoding="utf-8")
            return partial_path.stat().st_size
        if plan.format == "audio":
            self._write_audio_bundle(plan, partial_path)
            return None
        return self._write_direct_asset(plan.asset, partial_path)

    def _write_direct_asset(self, asset: LinkInfo, partial_path: Path) -> int | None:
        expected_size = asset.content_length
        response = self.adapter._request("GET", asset.url, stream=True)
        try:
            if not response.ok:
                raise DownloadError(f"Download failed with HTTP {response.status_code}")
            if response.headers.get("Content-Length"):
                expected_size = int(response.headers["Content-Length"])
            with partial_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        handle.write(chunk)
        finally:
            response.close()
        return expected_size

    def _write_audio_bundle(self, plan: DownloadPlan, partial_path: Path) -> None:
        if not plan.assets:
            raise DownloadError("Audio download plan contains no MP3 assets")
        used_names: set[str] = set()
        manifest_assets = []
        with zipfile.ZipFile(partial_path, "w", compression=zipfile.ZIP_STORED) as archive:
            for index, asset in enumerate(plan.assets, start=1):
                fallback = f"track-{index:03d}.mp3"
                entry_name = _unique_filename(_filename_from_url(asset.url, fallback), used_names)
                written = 0
                response = self.adapter._request("GET", asset.url, stream=True)
                try:
                    if not response.ok:
                        raise DownloadError(
                            f"Audio download failed with HTTP {response.status_code}: {asset.url}"
                        )
                    with archive.open(entry_name, "w") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                written += len(chunk)
                                handle.write(chunk)
                finally:
                    response.close()
                if asset.content_length is not None and written != asset.content_length:
                    raise DownloadError(
                        f"Audio byte count mismatch for {asset.url}: "
                        f"expected {asset.content_length}, got {written}"
                    )
                manifest_assets.append(
                    {
                        "entry": entry_name,
                        "url": asset.url,
                        "content_type": asset.content_type,
                        "content_length": asset.content_length,
                        "downloaded_bytes": written,
                    }
                )
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "title": plan.book.title,
                        "author": plan.book.author,
                        "source": plan.book.url,
                        "mirror": plan.mirror,
                        "assets": manifest_assets,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )

    def write_manifest(self, result: DownloadResult, path: str | Path) -> Path:
        manifest_path = Path(path).expanduser()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = result.to_dict()
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(manifest_path.parent),
            delete=False,
        ) as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            temp_name = handle.name
        os.replace(temp_name, manifest_path)
        return manifest_path

    def validate(self, path: str | Path, format: str = "auto", strict: bool = False):
        return validate_file(path, format=format, strict=strict)

    def list_categories(self) -> list[Category]:
        return self.adapter.list_categories()

    def get_category(self, category_id_or_slug: str | int) -> Category:
        return self.adapter.get_category(category_id_or_slug)

    def list_formats(self) -> list[FormatCategory]:
        return self.adapter.list_formats()

    def list_latest(
        self,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        format_values = self._normalize_formats(formats if formats is not None else format)
        return self.adapter.list_latest_books(format=format_values, page=page, limit=limit)

    def list_authors(
        self,
        initial: str,
        limit: int | None = None,
        page: int = 1,
    ) -> list[Author]:
        return self.adapter.list_authors(initial=initial, page=page, limit=limit)

    def list_by_title_initial(
        self,
        initial: str,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        format_values = self._normalize_formats(formats if formats is not None else format)
        return self.adapter.list_title_initial_books(
            initial=initial, format=format_values, page=page, limit=limit
        )

    def list_most_viewed(
        self,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        format_values = self._normalize_formats(formats if formats is not None else format)
        return self.adapter.list_most_viewed_books(format=format_values, page=page, limit=limit)

    def list_five_star(
        self,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        format_values = self._normalize_formats(formats if formats is not None else format)
        return self.adapter.list_five_star_books(format=format_values, page=page, limit=limit)

    def list_by_category(
        self,
        category: str | int,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        format_values = self._normalize_formats(formats if formats is not None else format)
        return self.adapter.list_category_books(
            category=category, format=format_values, page=page, limit=limit
        )

    def list_by_author(
        self,
        author_id: str | int,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        format_values = self._normalize_formats(formats if formats is not None else format)
        return self.adapter.list_author_books(
            author_id=author_id, format=format_values, page=page, limit=limit
        )

    def list_mirrors(self) -> list[str]:
        return list_mirrors()

    def list_format_ids(self) -> dict[str, int]:
        return dict(FORMAT_IDS)

    def list_top_by_category(
        self,
        category: str | int,
        source: str = "most-viewed",
        scan_pages: int = 10,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = 20,
    ) -> list[SearchResult]:
        category_info = self.get_category(category)
        results: list[SearchResult] = []
        for result in self._scan_ranked_source(source, scan_pages, format, formats):
            if result.category_id == category_info.id or _norm(result.category_name or "") == _norm(
                category_info.name
            ):
                results.append(result)
                if limit and len(results) >= limit:
                    break
        return self._dedupe_results(results)

    def list_top_by_author(
        self,
        author_id: str | int | None = None,
        author: str | None = None,
        source: str = "most-viewed",
        scan_pages: int = 10,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
        limit: int | None = 20,
    ) -> list[SearchResult]:
        if author_id is None and not author:
            raise NotFoundError("list_top_by_author requires author_id or author")
        wanted_id = int(author_id) if author_id is not None and str(author_id).isdigit() else None
        wanted_author = _norm(author) if author else None
        results: list[SearchResult] = []
        for result in self._scan_ranked_source(source, scan_pages, format, formats):
            id_matches = wanted_id is not None and result.author_id == wanted_id
            name_matches = wanted_author is not None and _norm(result.author or "") == wanted_author
            if id_matches or name_matches:
                results.append(result)
                if limit and len(results) >= limit:
                    break
        return self._dedupe_results(results)

    def _scan_ranked_source(
        self,
        source: str,
        scan_pages: int,
        format: str | list[str] | None = None,
        formats: str | list[str] | None = None,
    ) -> list[SearchResult]:
        if scan_pages < 1:
            raise NotFoundError("scan_pages must be >= 1")
        normalized_source = source.replace("_", "-").casefold().strip()
        results: list[SearchResult] = []
        for page in range(1, scan_pages + 1):
            if normalized_source in {"most-viewed", "popular", "views"}:
                page_results = self.list_most_viewed(format=format, formats=formats, page=page)
            elif normalized_source in {"five-star", "5-star", "rated", "rating"}:
                page_results = self.list_five_star(format=format, formats=formats, page=page)
            else:
                raise NotFoundError(f"Unsupported top-list source: {source}")
            results.extend(page_results)
        return self._dedupe_results(results)
