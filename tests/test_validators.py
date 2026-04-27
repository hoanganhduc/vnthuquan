from __future__ import annotations

import zipfile
from pathlib import Path

from vnthuquan.validators import validate_epub


def make_epub(path: Path, broken_spine: bool = False) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        zf.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Example Book</dc:title>
    <dc:creator>Example Author</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
  </spine>
</package>
""",
        )
        zf.writestr("OEBPS/nav.xhtml", "<html><body><nav>Contents</nav></body></html>")
        if not broken_spine:
            zf.writestr("OEBPS/chap1.xhtml", "<html><body><p>Hello world.</p></body></html>")


def test_validate_epub_accepts_valid_package(tmp_path: Path) -> None:
    epub = tmp_path / "book.epub"
    make_epub(epub)

    result = validate_epub(epub, expected_size=epub.stat().st_size)

    assert result.ok
    assert result.transfer_complete is True
    assert result.file_type_valid
    assert result.container_valid
    assert result.content_readable
    assert result.metadata_title == "Example Book"
    assert result.metadata_creator == "Example Author"


def test_validate_epub_rejects_missing_spine_file(tmp_path: Path) -> None:
    epub = tmp_path / "broken.epub"
    make_epub(epub, broken_spine=True)

    result = validate_epub(epub)

    assert not result.ok
    assert any("spine files missing" in error for error in result.errors)


def test_validate_epub_rejects_html_renamed_epub(tmp_path: Path) -> None:
    epub = tmp_path / "not-book.epub"
    epub.write_text("<html>not an epub</html>", encoding="utf-8")

    result = validate_epub(epub)

    assert not result.ok
    assert any("valid ZIP" in error for error in result.errors)
