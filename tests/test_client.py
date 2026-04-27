from __future__ import annotations

from vnthuquan.client import VnThuQuanClient
from vnthuquan.config import Config
from vnthuquan.models import DownloadPlan, DownloadResult, LinkInfo
from vnthuquan.models import BookMetadata, SearchResult


class FakeAdapter:
    mirror = "http://example.test"

    def __init__(self) -> None:
        self.searched_format: str | None = None
        self.fetched_url: str | None = None

    def search(self, query: str, field: str = "title", format: str | None = None, limit: int | None = None):
        self.searched_format = format
        results = [
            SearchResult(
                tid="winter",
                title="cuộc thanh trừng mùa đông (epub)",
                author="john sandford",
                format="epub",
                url="http://example.test/truyen/truyen.aspx?tid=winter",
                mirror=self.mirror,
            ),
            SearchResult(
                tid="mua-do",
                title="mưa đỏ (epub)",
                author="chu lai",
                format="epub",
                url="http://example.test/truyen/truyen.aspx?tid=mua-do",
                mirror=self.mirror,
            ),
        ]
        return results[:limit] if limit else results

    def get_book(self, url_or_tid: str) -> BookMetadata:
        self.fetched_url = url_or_tid
        return BookMetadata(
            tid=url_or_tid.rsplit("=", 1)[-1],
            title="mưa đỏ" if "mua-do" in url_or_tid else "cuộc thanh trừng mùa đông",
            author="chu lai" if "mua-do" in url_or_tid else "john sandford",
            format="epub",
            url=url_or_tid,
            mirror=self.mirror,
            tuaid="1",
        )


def test_resolve_book_prefers_single_clean_exact_title_match() -> None:
    client = VnThuQuanClient(config=Config())
    fake = FakeAdapter()
    client.adapter = fake  # type: ignore[assignment]

    book = client.resolve_book({"title": "Mưa Đỏ"}, search_format="epub")

    assert fake.searched_format == "epub"
    assert fake.fetched_url == "http://example.test/truyen/truyen.aspx?tid=mua-do"
    assert book.title == "mưa đỏ"


def test_write_manifest_preserves_manifest_path(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    manifest = tmp_path / "manifest.json"
    book = BookMetadata(
        tid="mua-do",
        title="Mưa Đỏ",
        author="Chu Lai",
        format="epub",
        url="http://example.test/truyen/truyen.aspx?tid=mua-do",
        mirror="http://example.test",
    )
    result = DownloadResult(
        ok=True,
        plan=DownloadPlan(
            selector={"title": "Mưa Đỏ"},
            book=book,
            format="epub",
            mirror="http://example.test",
            asset=LinkInfo(
                kind="asset",
                format="epub",
                url="http://example.test/Mua-Do.epub",
                mirror="http://example.test",
            ),
            output_path=str(tmp_path / "book.epub"),
            partial_path=str(tmp_path / "book.epub.partial"),
            dry_run=False,
            validation_checks=[],
        ),
        manifest_path=str(manifest),
    )

    client.write_manifest(result, manifest)

    assert f'"manifest_path": "{manifest}"' in manifest.read_text(encoding="utf-8")
