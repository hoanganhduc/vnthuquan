from __future__ import annotations

from vnthuquan.external_validators import select_external_validators, validate_external


def test_select_external_validators_for_epub() -> None:
    selected = select_external_validators("book.epub", external=True)

    assert selected == ["epubcheck", "ace"]


def test_validate_external_reports_missing_tool(monkeypatch) -> None:
    monkeypatch.setattr("vnthuquan.external_validators.shutil.which", lambda name: None)

    results = validate_external("book.epub", ["epubcheck"])

    assert len(results) == 1
    assert not results[0].ok
    assert results[0].error == "tool not found: epubcheck"
