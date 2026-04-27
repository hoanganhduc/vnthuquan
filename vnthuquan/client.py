"""High-level public client."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .adapter import FORMAT_IDS, LegacySiteAdapter
from .config import Config, load_config, resolve_download_dir
from .errors import (
    AmbiguousResultError,
    DownloadError,
    FilesystemError,
    NotFoundError,
    UnsupportedFormatError,
    ValidationError,
)
from .mirrors import list_mirrors, normalize_mirror
from .models import (
    BookMetadata,
    Category,
    DownloadPlan,
    DownloadResult,
    FormatCategory,
    LinkInfo,
    MirrorStatus,
    SearchResult,
)
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


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold().strip()


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "book"


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
        self.adapter = LegacySiteAdapter(
            mirror=selected_mirror,
            timeout=timeout if timeout is not None else self.config.timeout,
            retries=retries if retries is not None else self.config.retries,
        )

    @property
    def mirror(self) -> str:
        return self.adapter.mirror

    def live_check(self, mirror: str | None = None) -> MirrorStatus:
        adapter = self.adapter if mirror is None else LegacySiteAdapter(mirror=mirror)
        return adapter.live_check()

    def check_mirrors(self) -> list[MirrorStatus]:
        return [LegacySiteAdapter(mirror=mirror).live_check() for mirror in list_mirrors()]

    def search(
        self,
        query: str,
        field: str = "title",
        format: str | None = None,
        limit: int | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        if page != 1:
            raise NotFoundError("Search pagination is not supported by the live AJAX endpoint")
        return self.adapter.search(query=query, field=field, format=format, limit=limit)

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
        exact_matches = [result for result in results if _norm(_result_title(result)) == _norm(value)]
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
            preview = "; ".join(f"[{idx}] {item.title} - {item.author or 'unknown'}" for idx, item in enumerate(results[:10]))
            raise AmbiguousResultError(f"Multiple matches found. Use --index N. Matches: {preview}")
        return self.adapter.get_book(results[0].url)

    def discover_assets(self, book: BookMetadata) -> list[LinkInfo]:
        return self.adapter.discover_links(book)

    def get_asset_links(self, book: BookMetadata, formats: list[str] | None = None) -> list[LinkInfo]:
        return self.adapter.discover_links(book, formats=formats)

    def get_download_link(self, book: BookMetadata, format: str = "epub") -> LinkInfo:
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
    ) -> DownloadPlan:
        if format != "epub":
            raise UnsupportedFormatError("MVP downloads support EPUB only")
        book = self.resolve_book(selector, index=index, exact=exact, search_format=format)
        asset = self.get_download_link(book, format=format)
        output_dir = resolve_download_dir(out_dir, self.config)
        filename_parts = [book.title]
        if book.author:
            filename_parts.append(book.author)
        filename_parts.append("vnthuquan")
        filename = _safe_filename(" - ".join(filename_parts)) + ".epub"
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
            validation_checks=EPUB_VALIDATION_CHECKS,
            warnings=[],
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
        manifest: str | None = None,
    ) -> DownloadResult:
        dry_run = not execute if dry_run else dry_run
        plan = self.plan_download(selector, format=format, out_dir=out_dir, index=index, exact=exact, dry_run=dry_run)
        if dry_run:
            return DownloadResult(ok=True, plan=plan, warnings=["dry-run: no file downloaded"])

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
            raise FilesystemError(f"Could not create output directory {output_path.parent}: {exc}") from exc

        expected_size = plan.asset.content_length
        try:
            with requests.get(plan.asset.url, stream=True, timeout=self.config.timeout) as response:
                if not response.ok:
                    raise DownloadError(f"Download failed with HTTP {response.status_code}")
                if response.headers.get("Content-Length"):
                    expected_size = int(response.headers["Content-Length"])
                with partial_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            handle.write(chunk)
        except Exception as exc:
            if partial_path.exists() and not keep_invalid:
                partial_path.unlink(missing_ok=True)
            if isinstance(exc, DownloadError):
                raise
            raise DownloadError(f"Download failed: {exc}") from exc

        validation = None
        if not no_verify:
            validation = validate_file(partial_path, format=format, expected_size=expected_size)
            if not validation.ok:
                if not keep_invalid:
                    partial_path.unlink(missing_ok=True)
                raise ValidationError("; ".join(validation.errors) or "validation failed")

        os.replace(partial_path, output_path)
        if validation:
            validation.path = str(output_path)
        result = DownloadResult(ok=True, plan=plan, path=str(output_path), validation=validation)
        if manifest:
            result.manifest_path = str(Path(manifest).expanduser())
            self.write_manifest(result, manifest)
        return result

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

    def validate(self, path: str | Path, format: str = "auto"):
        return validate_file(path, format=format)

    def list_categories(self) -> list[Category]:
        return self.adapter.list_categories()

    def get_category(self, category_id_or_slug: str | int) -> Category:
        return self.adapter.get_category(category_id_or_slug)

    def list_formats(self) -> list[FormatCategory]:
        return self.adapter.list_formats()

    def list_mirrors(self) -> list[str]:
        return list_mirrors()

    def list_format_ids(self) -> dict[str, int]:
        return dict(FORMAT_IDS)
