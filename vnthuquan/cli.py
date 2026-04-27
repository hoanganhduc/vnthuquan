"""Command-line interface for vnthuquan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __description__, __version__
from .client import VnThuQuanClient
from .config import default_config_path, load_config, set_config_value, unset_config_value
from .errors import VnThuQuanError
from .mirrors import DEFAULT_MIRROR


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    return value


def _emit(value: Any, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(_jsonable(value), ensure_ascii=False, indent=2))
    elif isinstance(value, str):
        print(value)
    else:
        print(json.dumps(_jsonable(value), ensure_ascii=False, indent=2))


def _selector_from_args(args: argparse.Namespace) -> dict[str, str]:
    selector = {
        "title": getattr(args, "title", None),
        "url": getattr(args, "url", None),
        "id": getattr(args, "id", None),
    }
    active = [key for key, value in selector.items() if value]
    if len(active) != 1:
        raise argparse.ArgumentTypeError(
            "Exactly one selector is required: --title, --url, or --id"
        )
    return {key: value for key, value in selector.items() if value}


def _client(args: argparse.Namespace) -> VnThuQuanClient:
    config = load_config(args.config)
    return VnThuQuanClient(
        mirror=getattr(args, "mirror", None) or config.default_mirror,
        config=config,
        config_path=args.config,
        timeout=args.timeout if args.timeout is not None else config.timeout,
        retries=args.retries if args.retries is not None else config.retries,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vnthuquan", description=__description__)
    parser.add_argument("--version", action="version", version=f"vnthuquan {__version__}")
    parser.add_argument("--list", action="store_true", help="List available commands")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-essential output")
    parser.add_argument("--debug", action="store_true", help="Show debug details on errors")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--config", help="Path to config JSON")
    parser.add_argument("--timeout", type=float, help="HTTP timeout in seconds")
    parser.add_argument("--retries", type=int, help="HTTP retry count")

    subparsers = parser.add_subparsers(dest="command")

    search = subparsers.add_parser("search", help="Search or list books")
    search.add_argument(
        "query", nargs="*", help="Search query; repeat for multiple title/all-field queries"
    )
    search.add_argument(
        "--title", action="append", help="Search by title; repeat for multiple titles"
    )
    search.add_argument(
        "--author", action="append", help="Search by author; repeat for multiple authors"
    )
    search.add_argument(
        "--author-id",
        action="append",
        help="List or search books by author ID; repeat for multiple IDs",
    )
    search.add_argument(
        "--category",
        action="append",
        help="List or search within a category; repeat for multiple categories",
    )
    search.add_argument(
        "--field",
        choices=["title", "author", "category", "author-id", "author_id", "all"],
        default="title",
    )
    search.add_argument("--all", action="store_true", help="Search title and author fields")
    search.add_argument("--exact", action="store_true", help="Require exact title/author matches")
    search.add_argument(
        "--format", action="append", help="Filter by format; repeat or use comma-separated values"
    )
    search.add_argument("--limit", type=int)
    search.add_argument("--page", type=int, default=1)
    search.set_defaults(func=cmd_search)

    show = subparsers.add_parser("show", help="Show metadata, assets, or links")
    _add_selector_args(show)
    show.add_argument("--assets", action="store_true", help="Discover asset links")
    show.add_argument("--links", action="store_true", help="Show shareable links")
    show.add_argument("--index", type=int, help="Resolve title search result by index")
    show.add_argument("--exact", action="store_true", help="Require exact title match")
    show.set_defaults(func=cmd_show)

    download = subparsers.add_parser("download", help="Plan or execute an ebook download")
    _add_selector_args(download)
    download.add_argument("--format", default="epub", choices=["epub", "pdf", "text", "audio"])
    download.add_argument("--out", help="Output directory")
    download.add_argument("--index", type=int, help="Resolve title search result by index")
    download.add_argument("--exact", action="store_true", help="Require exact title match")
    download.add_argument("--mirror", help="Use a specific mirror")
    download.add_argument("--dry-run", action="store_true", help="Show plan without downloading")
    download.add_argument("--execute", action="store_true", help="Download and write files")
    download.add_argument("--overwrite", action="store_true", help="Replace existing output")
    download.add_argument(
        "--keep-invalid", action="store_true", help="Keep partial file if validation fails"
    )
    download.add_argument("--no-verify", action="store_true", help="Skip post-download validation")
    download.add_argument(
        "--strict-verify", action="store_true", help="Use stricter post-download validation"
    )
    download.add_argument(
        "--no-failover",
        action="store_true",
        help="Do not retry known mirrors after download failure",
    )
    download.add_argument("--manifest", help="Write download manifest JSON")
    download.set_defaults(func=cmd_download)

    validate = subparsers.add_parser("validate", help="Validate a saved ebook file")
    validate.add_argument("path")
    validate.add_argument(
        "--format", default="auto", choices=["auto", "epub", "pdf", "text", "audio"]
    )
    validate.add_argument(
        "--strict", action="store_true", help="Treat structural warnings as validation errors"
    )
    validate.set_defaults(func=cmd_validate)

    list_cmd = subparsers.add_parser("list", help="List site indexes and ranked book lists")
    list_sub = list_cmd.add_subparsers(dest="list_command", required=True)
    list_latest = list_sub.add_parser("latest", help="List latest/newly added books")
    _add_listing_args(list_latest, include_format=True)
    list_latest.set_defaults(func=cmd_list_latest)
    list_authors = list_sub.add_parser("authors", help="List authors by initial")
    list_authors.add_argument(
        "--initial", required=True, help="Initial letter; use # for numeric authors"
    )
    _add_listing_args(list_authors)
    list_authors.set_defaults(func=cmd_list_authors)
    list_title_initial = list_sub.add_parser("title-initial", help="List books by title initial")
    list_title_initial.add_argument("initial", help="Initial letter; use # for numeric titles")
    _add_listing_args(list_title_initial, include_format=True)
    list_title_initial.set_defaults(func=cmd_list_title_initial)
    list_most_viewed = list_sub.add_parser("most-viewed", help="List most-viewed books")
    _add_listing_args(list_most_viewed, include_format=True)
    list_most_viewed.set_defaults(func=cmd_list_most_viewed)
    list_five_star = list_sub.add_parser("five-star", help="List five-star/rated books")
    _add_listing_args(list_five_star, include_format=True)
    list_five_star.set_defaults(func=cmd_list_five_star)
    list_category = list_sub.add_parser("category", help="List books in a category")
    list_category.add_argument("category", help="Category ID or exact category name")
    _add_listing_args(list_category, include_format=True)
    list_category.set_defaults(func=cmd_list_category)
    list_author = list_sub.add_parser("author", help="List books by author ID")
    list_author.add_argument("author_id", help="Author ID")
    _add_listing_args(list_author, include_format=True)
    list_author.set_defaults(func=cmd_list_author)
    list_format = list_sub.add_parser("format", help="List books by format")
    list_format.add_argument("format", choices=["text", "image", "pdf", "audio", "epub"])
    _add_listing_args(list_format)
    list_format.set_defaults(func=cmd_list_format)
    list_top = list_sub.add_parser("top", help="List derived top books by category or author")
    target = list_top.add_mutually_exclusive_group(required=True)
    target.add_argument("--category", help="Category ID or exact category name")
    target.add_argument("--author-id", help="Author ID")
    target.add_argument("--author", help="Exact author name")
    list_top.add_argument("--source", default="most-viewed", choices=["most-viewed", "five-star"])
    list_top.add_argument(
        "--scan-pages", type=int, default=10, help="Number of ranked pages to scan before filtering"
    )
    list_top.add_argument(
        "--format", action="append", help="Filter by format; repeat or use comma-separated values"
    )
    list_top.add_argument("--limit", type=int, default=20)
    list_top.set_defaults(func=cmd_list_top)

    categories = subparsers.add_parser("categories", help="List or inspect categories")
    category_sub = categories.add_subparsers(dest="category_command", required=True)
    category_list = category_sub.add_parser("list", help="List categories")
    category_list.set_defaults(func=cmd_categories_list)
    category_show = category_sub.add_parser("show", help="Show one category")
    category_show.add_argument("category")
    category_show.set_defaults(func=cmd_categories_show)

    formats = subparsers.add_parser("formats", help="List site formats")
    format_sub = formats.add_subparsers(dest="format_command", required=True)
    format_list = format_sub.add_parser("list", help="List formats")
    format_list.set_defaults(func=cmd_formats_list)

    mirrors = subparsers.add_parser("mirrors", help="Manage mirrors")
    mirror_sub = mirrors.add_subparsers(dest="mirror_command", required=True)
    mirror_list = mirror_sub.add_parser("list", help="List known mirrors")
    mirror_list.set_defaults(func=cmd_mirrors_list)
    mirror_check = mirror_sub.add_parser("check", help="Check known mirrors")
    mirror_check.set_defaults(func=cmd_mirrors_check)
    mirror_use = mirror_sub.add_parser("use", help="Set default mirror")
    mirror_use.add_argument("url")
    mirror_use.set_defaults(func=cmd_mirrors_use)
    mirror_reset = mirror_sub.add_parser("reset", help="Reset default mirror")
    mirror_reset.set_defaults(func=cmd_mirrors_reset)

    config = subparsers.add_parser("config", help="Manage config")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_path = config_sub.add_parser("path", help="Show config path")
    config_path.set_defaults(func=cmd_config_path)
    config_show = config_sub.add_parser("show", help="Show config")
    config_show.set_defaults(func=cmd_config_show)
    config_set = config_sub.add_parser("set", help="Set config key")
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_set.set_defaults(func=cmd_config_set)
    config_unset = config_sub.add_parser("unset", help="Unset config key")
    config_unset.add_argument("key")
    config_unset.set_defaults(func=cmd_config_unset)

    doctor = subparsers.add_parser("doctor", help="Check environment and mirror health")
    doctor.add_argument("--mirror", help="Mirror to check")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def _add_selector_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--title", help="Resolve by title")
    parser.add_argument("--url", help="Resolve by book URL")
    parser.add_argument("--id", help="Resolve by tid")


def _add_listing_args(parser: argparse.ArgumentParser, include_format: bool = False) -> None:
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int)
    if include_format:
        parser.add_argument(
            "--format",
            action="append",
            help="Filter by format; repeat or use comma-separated values",
        )


def _print_results(results: list[Any]) -> None:
    for idx, result in enumerate(results):
        author = f" - {result.author}" if result.author else ""
        fmt = f" [{result.format}]" if result.format else ""
        print(f"[{idx}] {result.title}{author}{fmt}")
        if result.category_name:
            print(f"    Category: {result.category_name}")
        if result.views is not None:
            print(f"    Views: {result.views}")
        elif result.added_date:
            print(f"    Date: {result.added_date}")
        print(f"    {result.url}")


def _print_authors(authors: list[Any]) -> None:
    for idx, author in enumerate(authors):
        author_id = author.id if author.id is not None else "unknown"
        print(f"[{idx}] {author.name} (id={author_id})")
        if author.url:
            print(f"    {author.url}")


def cmd_search(args: argparse.Namespace) -> int:
    client = _client(args)
    query = list(args.query or [])
    field = args.field
    if args.all:
        field = "all"
    titles = list(args.title or [])
    authors = list(args.author or [])
    if field == "title" and query and not args.all:
        titles.extend(query)
        query = []
    elif field == "author" and query and not args.all:
        authors.extend(query)
        query = []
    if args.author_id:
        if field in {"category"}:
            raise argparse.ArgumentTypeError("--field category requires --category")
    if args.category and field == "category":
        field = "all"
    results = client.search(
        query,
        field=field,
        titles=titles,
        authors=authors,
        formats=args.format,
        categories=args.category,
        author_ids=args.author_id,
        limit=args.limit,
        page=args.page,
        exact=args.exact,
    )
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        _print_results(results)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    client = _client(args)
    selector = _selector_from_args(args)
    payload = client.show(
        selector, assets=args.assets, links=args.links, index=args.index, exact=args.exact
    )
    if args.json:
        _emit({"ok": True, **payload}, True)
    else:
        book = payload["book"]
        print(f"Title: {book.title}")
        if book.author:
            print(f"Author: {book.author}")
        print(f"Format: {book.format or 'unknown'}")
        print(f"Book page: {book.url}")
        if payload.get("links"):
            print("\nLinks:")
            for link in payload["links"]:
                label = f"{link.kind}"
                if link.format:
                    label += f" ({link.format})"
                print(f"- {label}: {link.url}")
                if link.content_type:
                    print(f"  Content-Type: {link.content_type}")
                if link.content_length is not None:
                    print(f"  Size: {link.content_length} bytes")
                if link.restricted_by_site_ui:
                    print("  Note: direct download is restricted by the site UI")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    client = _client(args)
    selector = _selector_from_args(args)
    result = client.download(
        selector,
        format=args.format,
        out_dir=args.out,
        dry_run=not args.execute,
        execute=args.execute,
        index=args.index,
        exact=args.exact,
        overwrite=args.overwrite,
        keep_invalid=args.keep_invalid,
        no_verify=args.no_verify,
        strict_verify=args.strict_verify,
        failover=not args.no_failover and not args.mirror,
        manifest=args.manifest,
    )
    if args.json:
        _emit(result, True)
    elif result.plan.dry_run:
        plan = result.plan
        print("Dry run: no file downloaded.")
        print(f"Title: {plan.book.title}")
        if plan.book.author:
            print(f"Author: {plan.book.author}")
        print(f"Format: {plan.format}")
        print(f"Mirror: {plan.mirror}")
        print(f"Asset URL: {plan.asset.url}")
        if plan.assets:
            print(f"Asset count: {len(plan.assets)}")
            if plan.format == "audio":
                for asset in plan.assets:
                    print(f"- {asset.url}")
        if plan.asset.content_type:
            print(f"Content-Type: {plan.asset.content_type}")
        if plan.asset.content_length is not None:
            print(f"Expected size: {plan.asset.content_length} bytes")
        if plan.warnings:
            print("Warnings:")
            for warning in plan.warnings:
                print(f"- {warning}")
        print(f"Output: {plan.output_path}")
        print(f"Temp file: {plan.partial_path}")
        print("Planned validation:")
        for check in plan.validation_checks:
            print(f"- {check}")
    elif result.skipped:
        print(f"Skipped existing valid file: {result.path}")
    else:
        print(f"Saved: {result.path}")
        if result.validation:
            print(f"SHA256: {result.validation.sha256}")
        if result.manifest_path:
            print(f"Manifest: {result.manifest_path}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    client = _client(args)
    result = client.validate(args.path, format=args.format, strict=args.strict)
    if args.json:
        _emit({"ok": result.ok, "validation": result}, True)
    else:
        print(f"Path: {result.path}")
        print(f"OK: {result.ok}")
        print(f"SHA256: {result.sha256}")
        print(f"Size: {result.size_bytes}")
        print(f"Title: {result.metadata_title}")
        print(f"Creator: {result.metadata_creator}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"- {warning}")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"- {error}")
    return 0 if result.ok else 7


def cmd_list_latest(args: argparse.Namespace) -> int:
    results = _client(args).list_latest(formats=args.format, limit=args.limit, page=args.page)
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        _print_results(results)
    return 0


def cmd_list_authors(args: argparse.Namespace) -> int:
    authors = _client(args).list_authors(args.initial, limit=args.limit, page=args.page)
    if args.json:
        _emit({"ok": True, "authors": authors}, True)
    else:
        _print_authors(authors)
    return 0


def cmd_list_title_initial(args: argparse.Namespace) -> int:
    results = _client(args).list_by_title_initial(
        args.initial, formats=args.format, limit=args.limit, page=args.page
    )
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        _print_results(results)
    return 0


def cmd_list_most_viewed(args: argparse.Namespace) -> int:
    results = _client(args).list_most_viewed(formats=args.format, limit=args.limit, page=args.page)
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        _print_results(results)
    return 0


def cmd_list_five_star(args: argparse.Namespace) -> int:
    results = _client(args).list_five_star(formats=args.format, limit=args.limit, page=args.page)
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        _print_results(results)
    return 0


def cmd_list_category(args: argparse.Namespace) -> int:
    results = _client(args).list_by_category(
        args.category, formats=args.format, limit=args.limit, page=args.page
    )
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        _print_results(results)
    return 0


def cmd_list_author(args: argparse.Namespace) -> int:
    results = _client(args).list_by_author(
        args.author_id, formats=args.format, limit=args.limit, page=args.page
    )
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        _print_results(results)
    return 0


def cmd_list_format(args: argparse.Namespace) -> int:
    results = _client(args).list_by_format(args.format, limit=args.limit, page=args.page)
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        _print_results(results)
    return 0


def cmd_list_top(args: argparse.Namespace) -> int:
    client = _client(args)
    if args.category is not None:
        results = client.list_top_by_category(
            args.category,
            source=args.source,
            scan_pages=args.scan_pages,
            formats=args.format,
            limit=args.limit,
        )
        target = {"category": args.category}
    else:
        results = client.list_top_by_author(
            author_id=args.author_id,
            author=args.author,
            source=args.source,
            scan_pages=args.scan_pages,
            formats=args.format,
            limit=args.limit,
        )
        target = {"author_id": args.author_id, "author": args.author}
    if args.json:
        _emit(
            {
                "ok": True,
                "derived": True,
                "source": args.source,
                "scan_pages": args.scan_pages,
                "target": target,
                "results": results,
            },
            True,
        )
    else:
        print(f"Derived top list from {args.source}; scanned up to {args.scan_pages} page(s).")
        _print_results(results)
    return 0


def cmd_categories_list(args: argparse.Namespace) -> int:
    categories = _client(args).list_categories()
    if args.json:
        _emit({"ok": True, "categories": categories}, True)
    else:
        for category in categories:
            print(f"{category.id:>2}  {category.name}")
    return 0


def cmd_categories_show(args: argparse.Namespace) -> int:
    category = _client(args).get_category(args.category)
    if args.json:
        _emit({"ok": True, "category": category}, True)
    else:
        print(f"ID: {category.id}")
        print(f"Name: {category.name}")
        print(f"Count: {category.count if category.count is not None else 'unknown'}")
        print(f"Pages: {category.pages if category.pages is not None else 'unknown'}")
    return 0


def cmd_formats_list(args: argparse.Namespace) -> int:
    formats = _client(args).list_formats()
    if args.json:
        _emit({"ok": True, "formats": formats}, True)
    else:
        for fmt in formats:
            count = fmt.count if fmt.count is not None else "unknown"
            print(f"{fmt.slug:<6} {fmt.id:<2} count={count}")
    return 0


def cmd_mirrors_list(args: argparse.Namespace) -> int:
    client = _client(args)
    mirrors = client.list_mirrors()
    if args.json:
        _emit({"ok": True, "mirrors": mirrors}, True)
    else:
        for mirror in mirrors:
            print(mirror)
    return 0


def cmd_mirrors_check(args: argparse.Namespace) -> int:
    statuses = _client(args).check_mirrors()
    if args.json:
        _emit({"ok": all(status.ok for status in statuses), "mirrors": statuses}, True)
    else:
        for status in statuses:
            marker = "ok" if status.ok else "failed"
            detail = status.status_code if status.status_code is not None else status.error
            print(f"{status.url}: {marker} ({detail})")
    return 0 if all(status.ok for status in statuses) else 5


def cmd_mirrors_use(args: argparse.Namespace) -> int:
    config = set_config_value("default_mirror", args.url, args.config)
    _emit(
        {"ok": True, "config": config.to_dict()}
        if args.json
        else f"Default mirror: {config.default_mirror}",
        args.json,
    )
    return 0


def cmd_mirrors_reset(args: argparse.Namespace) -> int:
    config = set_config_value("default_mirror", DEFAULT_MIRROR, args.config)
    _emit(
        {"ok": True, "config": config.to_dict()}
        if args.json
        else f"Default mirror: {config.default_mirror}",
        args.json,
    )
    return 0


def cmd_config_path(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser() if args.config else default_config_path()
    _emit({"ok": True, "path": str(path)} if args.json else str(path), args.json)
    return 0


def cmd_config_show(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    _emit(
        {"ok": True, "config": config.to_dict()}
        if args.json
        else json.dumps(config.to_dict(), indent=2),
        args.json,
    )
    return 0


def cmd_config_set(args: argparse.Namespace) -> int:
    config = set_config_value(args.key, args.value, args.config)
    _emit({"ok": True, "config": config.to_dict()} if args.json else "Config updated", args.json)
    return 0


def cmd_config_unset(args: argparse.Namespace) -> int:
    config = unset_config_value(args.key, args.config)
    _emit({"ok": True, "config": config.to_dict()} if args.json else "Config updated", args.json)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    client = VnThuQuanClient(mirror=args.mirror or config.default_mirror, config=config)
    live = client.live_check()
    download_dir = Path(config.download_dir or "~/Downloads/vnthuquan").expanduser()
    payload = {
        "ok": live.ok,
        "version": __version__,
        "config_path": str(
            Path(args.config).expanduser() if args.config else default_config_path()
        ),
        "download_dir": str(download_dir),
        "download_dir_exists": download_dir.exists(),
        "mirror": live,
    }
    if args.json:
        _emit(payload, True)
    else:
        print(f"vnthuquan: {__version__}")
        print(f"Config: {payload['config_path']}")
        print(f"Download dir: {payload['download_dir']} (exists={payload['download_dir_exists']})")
        print(f"Mirror: {live.url} ok={live.ok} status={live.status_code} error={live.error}")
    return 0 if live.ok else 5


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list:
        for command in [
            "search",
            "show",
            "download",
            "validate",
            "list",
            "categories",
            "formats",
            "mirrors",
            "config",
            "doctor",
        ]:
            print(command)
        return 0
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except argparse.ArgumentTypeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except VnThuQuanError as exc:
        if getattr(args, "json", False):
            _emit(
                {
                    "ok": False,
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                        "exit_code": exc.exit_code,
                    },
                },
                True,
            )
        else:
            print(f"Error: {exc}", file=sys.stderr)
            if getattr(args, "debug", False):
                raise
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 - final CLI guardrail
        if getattr(args, "json", False):
            _emit(
                {
                    "ok": False,
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                        "exit_code": 1,
                    },
                },
                True,
            )
        else:
            print(f"Error: {exc}", file=sys.stderr)
            if getattr(args, "debug", False):
                raise
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
