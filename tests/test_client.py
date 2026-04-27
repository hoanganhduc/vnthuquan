from __future__ import annotations

from vnthuquan.client import VnThuQuanClient
from vnthuquan.config import Config
from vnthuquan.models import Author, Category, DownloadPlan, DownloadResult, LinkInfo
from vnthuquan.models import BookMetadata, SearchResult


def format_values(format) -> list[str]:
    if not format:
        return []
    values = format if isinstance(format, list) else [format]
    return [part for value in values for part in str(value).split(",") if part]


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
        formats = format_values(format)
        if formats:
            results = [result for result in results if result.format in formats]
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

    def list_category_books(
        self,
        category,
        format: str | None = None,
        page: int = 1,
        limit: int | None = None,
    ):
        results = [
            SearchResult(
                tid="mua-do",
                title="mưa đỏ (epub)",
                author="chu lai",
                format="epub",
                url="http://example.test/truyen/truyen.aspx?tid=mua-do",
                mirror=self.mirror,
                category_id=23,
                category_name="Tiểu Thuyết",
            ),
            SearchResult(
                tid="winter",
                title="cuộc thanh trừng mùa đông",
                author="john sandford",
                format="text",
                url="http://example.test/truyen/truyen.aspx?tid=winter",
                mirror=self.mirror,
                category_id=23,
                category_name="Tiểu Thuyết",
            ),
        ]
        formats = format_values(format)
        if formats:
            results = [result for result in results if result.format in formats]
        return results[:limit] if limit else results

    def list_author_books(
        self,
        author_id,
        format: str | None = None,
        page: int = 1,
        limit: int | None = None,
    ):
        results = [
            SearchResult(
                tid="mua-do",
                title="mưa đỏ (epub)",
                author="chu lai",
                format="epub",
                url="http://example.test/truyen/truyen.aspx?tid=mua-do",
                mirror=self.mirror,
                author_id=int(author_id),
            ),
            SearchResult(
                tid="pho",
                title="phố",
                author="chu lai",
                format="text",
                url="http://example.test/truyen/truyen.aspx?tid=pho",
                mirror=self.mirror,
                author_id=int(author_id),
            ),
        ]
        formats = format_values(format)
        if formats:
            results = [result for result in results if result.format in formats]
        return results[:limit] if limit else results

    def list_format_books(self, format: str, page: int = 1, limit: int | None = None):
        results = [
            SearchResult(
                tid="mua-do",
                title="mưa đỏ (epub)",
                author="chu lai",
                format=format,
                url="http://example.test/truyen/truyen.aspx?tid=mua-do",
                mirror=self.mirror,
            )
        ]
        return results[:limit] if limit else results

    def list_latest_books(self, format=None, page: int = 1, limit: int | None = None):
        results = [
            SearchResult(
                tid="latest",
                title="latest book",
                author="new author",
                format="text",
                url="http://example.test/truyen/truyen.aspx?tid=latest",
                mirror=self.mirror,
                added_date="24.4.2026",
                date_or_views="24.4.2026",
            )
        ]
        return results[:limit] if limit else results

    def list_authors(self, initial: str, page: int = 1, limit: int | None = None):
        authors = [
            Author(
                name="A Author",
                id=1,
                url="http://example.test/truyen/tacpham.aspx?tacgiaid=1",
                mirror=self.mirror,
                initial=initial,
            )
        ]
        return authors[:limit] if limit else authors

    def list_title_initial_books(self, initial: str, format=None, page: int = 1, limit: int | None = None):
        results = [
            SearchResult(
                tid="a-book",
                title="a book",
                author="A Author",
                format="epub",
                url="http://example.test/truyen/truyen.aspx?tid=a-book",
                mirror=self.mirror,
            )
        ]
        return results[:limit] if limit else results

    def list_most_viewed_books(self, format=None, page: int = 1, limit: int | None = None):
        results = [
            SearchResult(
                tid="top-kim",
                title="top kim",
                author="kim dung",
                format="text",
                url="http://example.test/truyen/truyen.aspx?tid=top-kim",
                mirror=self.mirror,
                author_id=284,
                category_id=6,
                category_name="Kiếm Hiệp",
                views=100,
                date_or_views="Số lượt xem: 100",
            ),
            SearchResult(
                tid="top-other",
                title="top other",
                author="other",
                format="text",
                url="http://example.test/truyen/truyen.aspx?tid=top-other",
                mirror=self.mirror,
                author_id=999,
                category_id=23,
                category_name="Tiểu Thuyết",
                views=90,
                date_or_views="Số lượt xem: 90",
            ),
        ]
        formats = format_values(format)
        if formats:
            results = [result for result in results if result.format in formats]
        return results[:limit] if limit else results

    def list_five_star_books(self, format=None, page: int = 1, limit: int | None = None):
        return self.list_most_viewed_books(format=format, page=page, limit=limit)

    def get_category(self, value):
        assert str(value) == "6"
        return Category(id=6, name="Kiếm Hiệp")


def test_resolve_book_prefers_single_clean_exact_title_match() -> None:
    client = VnThuQuanClient(config=Config())
    fake = FakeAdapter()
    client.adapter = fake  # type: ignore[assignment]

    book = client.resolve_book({"title": "Mưa Đỏ"}, search_format="epub")

    assert fake.searched_format == ["epub"]
    assert fake.fetched_url == "http://example.test/truyen/truyen.aspx?tid=mua-do"
    assert book.title == "mưa đỏ"


def test_search_by_category_filters_title_and_format() -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    results = client.search_by_category(23, query="mưa", field="title", format="epub")

    assert len(results) == 1
    assert results[0].tid == "mua-do"
    assert results[0].category_name == "Tiểu Thuyết"


def test_search_by_author_id_filters_exact_title() -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    results = client.search_by_author_id(42, query="Mưa Đỏ", field="title", exact=True)

    assert len(results) == 1
    assert results[0].tid == "mua-do"
    assert results[0].author_id == 42


def test_search_all_dedupes_title_and_author_results() -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    results = client.search_all("mưa")

    assert [result.tid for result in results] == ["mua-do"]


def test_search_accepts_multiple_titles_authors_and_formats() -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    results = client.search(
        titles=["Mưa", "cuộc"],
        authors=["chu lai"],
        formats=["epub,text"],
    )

    assert {result.tid for result in results} == {"mua-do", "winter"}


def test_client_exposes_native_list_methods() -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    assert client.list_latest(limit=1)[0].tid == "latest"
    assert client.list_authors("A")[0].name == "A Author"
    assert client.list_by_title_initial("A")[0].tid == "a-book"
    assert client.list_most_viewed(limit=1)[0].views == 100


def test_client_derives_top_by_category_and_author() -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    category_results = client.list_top_by_category(6, scan_pages=2, limit=5)
    author_results = client.list_top_by_author(author_id=284, scan_pages=2, limit=5)

    assert [result.tid for result in category_results] == ["top-kim"]
    assert [result.tid for result in author_results] == ["top-kim"]


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
