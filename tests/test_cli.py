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
        "archive",
        "completion",
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


def test_search_parser_accepts_jobs_and_print_fields() -> None:
    parser = build_parser()

    args = parser.parse_args(
        ["search", "--format", "epub", "--jobs", "auto", "--print", "title,url"]
    )

    assert args.command == "search"
    assert args.jobs == "auto"
    assert args.print_fields == ["title,url"]


def test_subcommands_accept_json_after_command() -> None:
    parser = build_parser()

    search_args = parser.parse_args(["search", "--format", "epub", "--json"])
    download_args = parser.parse_args(["download", "--title", "Mưa Đỏ", "--json"])

    assert search_args.json
    assert download_args.json


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


def test_download_parser_accepts_queue_archive_template_and_external_flags() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "download",
            "--all",
            "--category",
            "23",
            "--format",
            "epub",
            "--manifest",
            "queue.json",
            "--filename-template",
            "{title} [{tid}]",
            "--jobs",
            "auto",
            "--progress",
            "--epubcheck",
            "--no-archive",
        ]
    )

    assert args.command == "download"
    assert args.all
    assert args.category == ["23"]
    assert args.manifest == "queue.json"
    assert args.filename_template == "{title} [{tid}]"
    assert args.jobs == "auto"
    assert args.progress
    assert args.epubcheck
    assert args.no_archive


def test_download_parser_accepts_from_manifest() -> None:
    parser = build_parser()

    args = parser.parse_args(["download", "--from-manifest", "queue.json", "--execute"])

    assert args.command == "download"
    assert args.from_manifest == "queue.json"
    assert args.execute


def test_validate_parser_accepts_strict_flag() -> None:
    parser = build_parser()

    args = parser.parse_args(["validate", "book.epub", "--strict"])

    assert args.command == "validate"
    assert args.strict


def test_validate_parser_accepts_external_flags() -> None:
    parser = build_parser()

    args = parser.parse_args(["validate", "book.epub", "--external", "--ace"])

    assert args.external
    assert args.ace


def test_archive_and_completion_commands_parse() -> None:
    parser = build_parser()

    archive_args = parser.parse_args(["archive", "list", "--limit", "3", "--print", "title,path"])
    completion_args = parser.parse_args(["completion", "bash"])

    assert archive_args.command == "archive"
    assert archive_args.archive_command == "list"
    assert archive_args.limit == 3
    assert completion_args.command == "completion"
    assert completion_args.shell == "bash"
