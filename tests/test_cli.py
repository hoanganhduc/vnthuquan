from __future__ import annotations

from vnthuquan.cli import build_parser


def test_parser_has_mvp_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()

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
        assert command in help_text


def test_search_parser_accepts_category_without_query() -> None:
    parser = build_parser()

    args = parser.parse_args(["search", "--category", "23", "--format", "epub", "--limit", "5"])

    assert args.command == "search"
    assert args.category == ["23"]
    assert args.format == ["epub"]
    assert args.limit == 5


def test_search_parser_accepts_explicit_author() -> None:
    parser = build_parser()

    args = parser.parse_args(["search", "--author", "Chu Lai"])

    assert args.command == "search"
    assert args.author == ["Chu Lai"]


def test_search_parser_accepts_author_id_and_exact() -> None:
    parser = build_parser()

    args = parser.parse_args(["search", "Mưa Đỏ", "--author-id", "42", "--exact"])

    assert args.command == "search"
    assert args.query == ["Mưa Đỏ"]
    assert args.author_id == ["42"]
    assert args.exact


def test_search_parser_accepts_all_fields_flag() -> None:
    parser = build_parser()

    args = parser.parse_args(["search", "Chu Lai", "--all"])

    assert args.command == "search"
    assert args.all


def test_search_parser_accepts_repeated_and_comma_formats() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "search",
            "--author",
            "Kim Dung",
            "--author",
            "Chu Lai",
            "--format",
            "pdf,epub",
            "--format",
            "text",
        ]
    )

    assert args.author == ["Kim Dung", "Chu Lai"]
    assert args.format == ["pdf,epub", "text"]


def test_list_parser_accepts_latest() -> None:
    parser = build_parser()

    args = parser.parse_args(["list", "latest", "--page", "2", "--format", "epub", "--limit", "5"])

    assert args.command == "list"
    assert args.list_command == "latest"
    assert args.page == 2
    assert args.format == ["epub"]
    assert args.limit == 5


def test_list_parser_accepts_authors_by_initial() -> None:
    parser = build_parser()

    args = parser.parse_args(["list", "authors", "--initial", "A", "--page", "2"])

    assert args.command == "list"
    assert args.list_command == "authors"
    assert args.initial == "A"
    assert args.page == 2


def test_list_parser_accepts_derived_top_target() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "list",
            "top",
            "--category",
            "6",
            "--source",
            "most-viewed",
            "--scan-pages",
            "20",
            "--format",
            "epub,pdf",
        ]
    )

    assert args.command == "list"
    assert args.list_command == "top"
    assert args.category == "6"
    assert args.scan_pages == 20
    assert args.format == ["epub,pdf"]


def test_download_parser_accepts_failover_and_strict_verify_flags() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "download",
            "--title",
            "Mưa Đỏ",
            "--execute",
            "--strict-verify",
            "--no-failover",
        ]
    )

    assert args.command == "download"
    assert args.strict_verify
    assert args.no_failover


def test_validate_parser_accepts_strict_flag() -> None:
    parser = build_parser()

    args = parser.parse_args(["validate", "book.epub", "--strict"])

    assert args.command == "validate"
    assert args.strict
