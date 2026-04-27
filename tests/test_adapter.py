from __future__ import annotations

import pytest
import requests

from vnthuquan.adapter import LegacySiteAdapter
from vnthuquan.errors import AssetDiscoveryError
from vnthuquan.models import BookMetadata, Category


class Response:
    ok = True
    status_code = 200

    def __init__(self, text: str) -> None:
        self.text = text


class CategoryAdapter(LegacySiteAdapter):
    def __init__(self, html: str) -> None:
        super().__init__(mirror="http://example.test")
        self.html = html
        self.requested_url: str | None = None

    def get_category(self, value: str | int) -> Category:
        assert str(value) == "23"
        return Category(id=23, name="Tiểu Thuyết")

    def _request(self, method: str, url: str, **kwargs) -> Response:
        self.requested_url = url
        return Response(self.html)


class PdfAdapter(LegacySiteAdapter):
    def __init__(self) -> None:
        super().__init__(mirror="http://example.test")

    def _post_chapter_endpoint(self, endpoint, book):
        return '<iframe src="noidung_pdf.aspx?tid=abc123"></iframe>'

    def _request(self, method: str, url: str, **kwargs) -> Response:
        if method == "GET":
            return Response(
                """
                <script>
                var option_df_111 = {
                  "enableDownload":"false",
                  "source":"../userfiles/files/pdf/book.pdf"
                };
                </script>
                """
            )
        return Response("")


class PartialTextAdapter(LegacySiteAdapter):
    def __init__(self) -> None:
        super().__init__(mirror="http://example.test")

    def _request(self, method: str, url: str, **kwargs) -> Response:
        return Response(
            """
            <acronym title="First Chapter">
              <li onClick="noidung1('tuaid=99&chuongid=1')"><a href="#phandau">Chương 1</a></li>
            </acronym>
            <acronym title="Second Chapter">
              <li onClick="noidung1('tuaid=99&chuongid=2')"><a href="#phandau">Chương 2</a></li>
            </acronym>
            """
        )

    def _post_text_chapter(self, book: BookMetadata, chapter_id: str) -> str:
        if chapter_id == "1":
            return """
            <span class="tuahoi1">First Chapter</span>
            <div class="chuhoavn"><p>Readable chapter.</p></div>
            """
        return '<span class="tuahoi1">Second Chapter</span><div class="chuhoavn"></div>'


def test_parse_listing_extracts_search_result() -> None:
    html = """
    <div class="danhsach">
      <a target="_self" href="truyen.aspx?tid=abc123"><img alt="Example - Author"></a>
      <span class="label-title label-time">11.10.2024</span>
      <span class="label-title label-scan">Epub</span>
      <div class="truyen-title"><a href="truyen.aspx?tid=abc123">Example Book</a></div>
      <span class="author"><a href="tacpham.aspx?tacgiaid=1">Example Author</a></span>
      <span class="label-title label-theloai"><a href="theloai.aspx?theloaiid=23">Tiểu Thuyết</a></span>
    </div>
    """
    adapter = LegacySiteAdapter()

    results = adapter._parse_listing(html)

    assert len(results) == 1
    assert results[0].tid == "abc123"
    assert results[0].title == "Example Book"
    assert results[0].author == "Example Author"
    assert results[0].author_id == 1
    assert results[0].format == "epub"
    assert results[0].category_id == 23
    assert results[0].added_date == "11.10.2024"


def test_parse_listing_extracts_view_counts() -> None:
    html = """
    <div class="danhsach">
      <a href="truyen.aspx?tid=abc123">Example Book</a>
      <span class="label-title label-time">Số lượt xem: 12345</span>
      <span class="label-title label-scan">Text</span>
      <div class="truyen-title"><a href="truyen.aspx?tid=abc123">Example Book</a></div>
      <span class="author"><a href="tacpham.aspx?tacgiaid=1">Example Author</a></span>
    </div>
    """
    adapter = LegacySiteAdapter()

    results = adapter._parse_listing(html)

    assert results[0].date_or_views == "Số lượt xem: 12345"
    assert results[0].views == 12345


def test_list_latest_books_uses_default_route() -> None:
    html = """
    <div class="danhsach">
      <a href="truyen.aspx?tid=abc123">Example Book</a>
      <span class="label-title label-scan">Text</span>
      <div class="truyen-title"><a href="truyen.aspx?tid=abc123">Example Book</a></div>
    </div>
    """
    adapter = LegacySiteAdapter(mirror="http://example.test")
    requested_url = None

    def request(method, url, **kwargs):
        nonlocal requested_url
        requested_url = url
        return Response(html)

    adapter._request = request  # type: ignore[method-assign]

    results = adapter.list_latest_books(page=4)

    assert "default.aspx?tranghientai=4" in (requested_url or "")
    assert len(results) == 1


def test_list_authors_parses_initial_page() -> None:
    html = """
    <a href="tacpham.aspx?tacgiaid=1163">A . F . Herold</a>
    <a href="tacpham.aspx?tacgiaid=8455">A Bạch Bạch</a>
    <a href="tacpham.aspx?tacgiaid=">1000min</a>
    """
    adapter = LegacySiteAdapter(mirror="http://example.test")
    requested_url = None

    def request(method, url, **kwargs):
        nonlocal requested_url
        requested_url = url
        return Response(html)

    adapter._request = request  # type: ignore[method-assign]

    authors = adapter.list_authors("A", page=2)

    assert "tacgia.aspx?tranghientai=2" in (requested_url or "")
    assert "tacgia=A" in (requested_url or "")
    assert [author.name for author in authors] == ["A . F . Herold", "A Bạch Bạch", "1000min"]
    assert authors[0].id == 1163
    assert authors[2].id is None


def test_list_ranked_routes() -> None:
    html = """
    <div class="danhsach">
      <a href="truyen.aspx?tid=abc123">Example Book</a>
      <span class="label-title label-time">Số lượt xem: 12345</span>
      <span class="label-title label-scan">Text</span>
      <div class="truyen-title"><a href="truyen.aspx?tid=abc123">Example Book</a></div>
    </div>
    """
    adapter = LegacySiteAdapter(mirror="http://example.test")
    requested_urls: list[str] = []

    def request(method, url, **kwargs):
        requested_urls.append(url)
        return Response(html)

    adapter._request = request  # type: ignore[method-assign]

    assert adapter.list_most_viewed_books(page=3)[0].views == 12345
    assert adapter.list_five_star_books(page=5)[0].tid == "abc123"
    assert "xemnhieu.aspx?tranghientai=3" in requested_urls[0]
    assert "Namsao_moi.aspx?tranghientai=5" in requested_urls[1]


def test_list_title_initial_uses_mautu_route() -> None:
    html = """
    <div class="danhsach">
      <a href="truyen.aspx?tid=abc123">A Book</a>
      <span class="label-title label-scan">Text</span>
      <div class="truyen-title"><a href="truyen.aspx?tid=abc123">A Book</a></div>
    </div>
    """
    adapter = LegacySiteAdapter(mirror="http://example.test")
    requested_url = None

    def request(method, url, **kwargs):
        nonlocal requested_url
        requested_url = url
        return Response(html)

    adapter._request = request  # type: ignore[method-assign]

    results = adapter.list_title_initial_books("A", page=2)

    assert "mautu.aspx?tranghientai=2" in (requested_url or "")
    assert "tua=A" in (requested_url or "")
    assert results[0].title == "A Book"


def test_list_category_books_fills_missing_category_metadata() -> None:
    html = """
    <div class="danhsach">
      <a href="truyen.aspx?tid=abc123">Example Book</a>
      <span class="label-title label-scan">Text</span>
      <div class="truyen-title"><a href="truyen.aspx?tid=abc123">Example Book</a></div>
      <span class="author"><a href="tacpham.aspx?tacgiaid=1">Example Author</a></span>
    </div>
    """
    adapter = CategoryAdapter(html)

    results = adapter.list_category_books(23, page=2)

    assert "tranghientai=2" in (adapter.requested_url or "")
    assert "theloaiid=23" in (adapter.requested_url or "")
    assert len(results) == 1
    assert results[0].category_id == 23
    assert results[0].category_name == "Tiểu Thuyết"


def test_list_author_books_fills_missing_author_metadata() -> None:
    html = """
    <h2>T ác Giả: Example Author</h2>
    <div class="danhsach">
      <a href="truyen.aspx?tid=abc123">Example Book</a>
      <span class="label-title label-scan">Text</span>
      <div class="truyen-title"><a href="truyen.aspx?tid=abc123">Example Book</a></div>
    </div>
    """
    adapter = LegacySiteAdapter(mirror="http://example.test")
    adapter._request = lambda method, url, **kwargs: Response(html)  # type: ignore[method-assign]

    results = adapter.list_author_books(1, page=3)

    assert len(results) == 1
    assert results[0].author == "Example Author"
    assert results[0].author_id == 1


def test_parse_text_chapters_extracts_chapter_ids_and_titles() -> None:
    html = """
    <acronym title="First Chapter">
      <li onClick="noidung1('tuaid=99&chuongid=1')"><a href="#phandau">Chương 1</a></li>
    </acronym>
    <acronym title="Second Chapter">
      <li onClick="noidung1('tuaid=99&chuongid=2')"><a href="#phandau">Chương 2</a></li>
    </acronym>
    """
    adapter = LegacySiteAdapter()

    chapters = adapter._parse_text_chapters(html, "99")

    assert chapters == [("1", "Chương 1", "First Chapter"), ("2", "Chương 2", "Second Chapter")]


def test_parse_text_chapter_extracts_heading_and_body() -> None:
    html = """
    <span class="tuahoi1">First Chapter</span>
    <div class="chuhoavn">
      <p>First paragraph.</p>
      <p>Second paragraph.</p>
    </div>
    """
    adapter = LegacySiteAdapter()

    heading, body = adapter._parse_text_chapter(html)

    assert heading == "First Chapter"
    assert body == "First paragraph.\n\nSecond paragraph."


def test_discover_pdf_links_parses_quoted_source_and_restriction() -> None:
    adapter = PdfAdapter()
    book = adapter.get_book("abc123")
    book.format = "pdf"
    book.tuaid = "1"

    links = adapter._discover_pdf_links(book)

    assert links[0].restricted_by_site_ui is True
    assert links[1].url == "http://example.test/userfiles/files/pdf/book.pdf"
    assert links[1].restricted_by_site_ui is True


def test_export_text_fails_when_any_discovered_chapter_is_unreadable() -> None:
    adapter = PartialTextAdapter()
    book = BookMetadata(
        tid="abc123",
        title="Text Book",
        author=None,
        format="text",
        url="http://example.test/truyen/truyen.aspx?tid=abc123",
        mirror="http://example.test",
        tuaid="99",
    )

    with pytest.raises(AssetDiscoveryError, match="Missing readable text"):
        adapter.export_text(book)


def test_request_cache_reuses_non_streaming_response() -> None:
    session = requests.Session()
    calls = 0

    def request(method, url, timeout, **kwargs):
        nonlocal calls
        calls += 1
        response = requests.Response()
        response.status_code = 200
        response.reason = "OK"
        response.url = url
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        response.encoding = "utf-8"
        response._content = b"cached response"
        return response

    session.request = request  # type: ignore[method-assign]
    adapter = LegacySiteAdapter(
        mirror="http://example.test",
        cache_ttl=30,
        request_interval=0,
        session=session,
    )

    first = adapter._request("GET", "http://example.test/one")
    second = adapter._request("GET", "http://example.test/one")

    assert first.text == "cached response"
    assert second.text == "cached response"
    assert calls == 1
