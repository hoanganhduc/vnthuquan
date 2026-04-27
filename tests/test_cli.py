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
        "categories",
        "formats",
        "mirrors",
        "config",
        "doctor",
    ]:
        assert command in help_text
