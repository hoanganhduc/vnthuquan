"""Command-line interface for vnthuquan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __description__, __version__
from .client import VnThuQuanClient
from .config import default_config_path, load_config, save_config, set_config_value, unset_config_value
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
        raise argparse.ArgumentTypeError("Exactly one selector is required: --title, --url, or --id")
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

    search = subparsers.add_parser("search", help="Search books")
    search.add_argument("query")
    search.add_argument("--field", choices=["title", "author"], default="title")
    search.add_argument("--format", choices=["text", "epub", "pdf", "audio", "image"])
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

    download = subparsers.add_parser("download", help="Plan or execute an EPUB download")
    _add_selector_args(download)
    download.add_argument("--format", default="epub", choices=["epub"])
    download.add_argument("--out", help="Output directory")
    download.add_argument("--index", type=int, help="Resolve title search result by index")
    download.add_argument("--exact", action="store_true", help="Require exact title match")
    download.add_argument("--mirror", help="Use a specific mirror")
    download.add_argument("--dry-run", action="store_true", help="Show plan without downloading")
    download.add_argument("--execute", action="store_true", help="Download and write files")
    download.add_argument("--overwrite", action="store_true", help="Replace existing output")
    download.add_argument("--resume", action="store_true", help="Reserved for future resumable downloads")
    download.add_argument("--keep-invalid", action="store_true", help="Keep partial file if validation fails")
    download.add_argument("--no-verify", action="store_true", help="Skip post-download validation")
    download.add_argument("--no-failover", action="store_true", help="Reserved for future failover control")
    download.add_argument("--manifest", help="Write download manifest JSON")
    download.set_defaults(func=cmd_download)

    validate = subparsers.add_parser("validate", help="Validate a saved EPUB")
    validate.add_argument("path")
    validate.add_argument("--format", default="auto", choices=["auto", "epub"])
    validate.set_defaults(func=cmd_validate)

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


def cmd_search(args: argparse.Namespace) -> int:
    client = _client(args)
    results = client.search(args.query, field=args.field, format=args.format, limit=args.limit, page=args.page)
    if args.json:
        _emit({"ok": True, "results": results}, True)
    else:
        for idx, result in enumerate(results):
            author = f" - {result.author}" if result.author else ""
            fmt = f" [{result.format}]" if result.format else ""
            print(f"[{idx}] {result.title}{author}{fmt}")
            print(f"    {result.url}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    client = _client(args)
    selector = _selector_from_args(args)
    payload = client.show(selector, assets=args.assets, links=args.links, index=args.index, exact=args.exact)
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
        if plan.asset.content_type:
            print(f"Content-Type: {plan.asset.content_type}")
        if plan.asset.content_length is not None:
            print(f"Expected size: {plan.asset.content_length} bytes")
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
    result = client.validate(args.path, format=args.format)
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
    _emit({"ok": True, "config": config.to_dict()} if args.json else f"Default mirror: {config.default_mirror}", args.json)
    return 0


def cmd_mirrors_reset(args: argparse.Namespace) -> int:
    config = set_config_value("default_mirror", DEFAULT_MIRROR, args.config)
    _emit({"ok": True, "config": config.to_dict()} if args.json else f"Default mirror: {config.default_mirror}", args.json)
    return 0


def cmd_config_path(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser() if args.config else default_config_path()
    _emit({"ok": True, "path": str(path)} if args.json else str(path), args.json)
    return 0


def cmd_config_show(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    _emit({"ok": True, "config": config.to_dict()} if args.json else json.dumps(config.to_dict(), indent=2), args.json)
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
        "config_path": str(Path(args.config).expanduser() if args.config else default_config_path()),
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
