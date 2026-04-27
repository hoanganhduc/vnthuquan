from __future__ import annotations

from pathlib import Path

import pytest

from vnthuquan.client import VnThuQuanClient
from vnthuquan.config import Config
from vnthuquan.errors import DownloadError, UnsupportedFormatError
from vnthuquan.models import Author, Category, DownloadPlan, DownloadResult, LinkInfo
from vnthuquan.models import BookMetadata, SearchResult


def format_values(format) -> list[str]:
    if not format:
        return []
    values = format if isinstance(format, list) else [format]
    return [part for value in values for part in str(value).split(",") if part]


class FakeAdapter:
    def __init__(
        self, mirror: str = "http://example.test", stream_bytes: bytes | None = None
    ) -> None:
        self.mirror = mirror
        self.searched_format: str | None = None
        self.fetched_url: str | None = None
        self.stream_bytes = stream_bytes if stream_bytes is not None else b"ID3" + b"\0" * 2048

    def search(
        self, query: str, field: str = "title", format: str | None = None, limit: int | None = None
    ):
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
            SearchResult(
                tid="pdf-book",
                title="pdf book (pdf)",
                author="pdf author",
                format="pdf",
                url="http://example.test/truyen/truyen.aspx?tid=pdf-book",
                mirror=self.mirror,
            ),
            SearchResult(
                tid="audio-book",
                title="audio book (audio)",
                author="audio author",
                format="audio",
                url="http://example.test/truyen/truyen.aspx?tid=audio-book",
                mirror=self.mirror,
            ),
            SearchResult(
                tid="text-book",
                title="text book",
                author="text author",
                format="text",
                url="http://example.test/truyen/truyen.aspx?tid=text-book",
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
            title=self._book_title(url_or_tid),
            author=self._book_author(url_or_tid),
            format=self._book_format(url_or_tid),
            url=url_or_tid,
            mirror=self.mirror,
            tuaid="1",
        )

    def _book_title(self, value: str) -> str:
        if "mua-do" in value:
            return "mưa đỏ"
        if "pdf-book" in value:
            return "pdf book"
        if "audio-book" in value:
            return "audio book"
        if "text-book" in value:
            return "text book"
        return "cuộc thanh trừng mùa đông"

    def _book_author(self, value: str) -> str:
        if "mua-do" in value:
            return "chu lai"
        if "pdf-book" in value:
            return "pdf author"
        if "audio-book" in value:
            return "audio author"
        if "text-book" in value:
            return "text author"
        return "john sandford"

    def _book_format(self, value: str) -> str:
        if "pdf-book" in value:
            return "pdf"
        if "audio-book" in value:
            return "audio"
        if "text-book" in value:
            return "text"
        return "epub"

    def discover_links(self, book: BookMetadata, formats=None):
        if book.format == "epub":
            return [
                LinkInfo(
                    kind="reader", format="epub", url=f"{book.url}#reader", mirror=self.mirror
                ),
                LinkInfo(
                    kind="asset",
                    format="epub",
                    url="http://example.test/book.epub",
                    mirror=self.mirror,
                    content_type="application/epub+zip",
                    content_length=1024,
                    is_direct_asset=True,
                ),
            ]
        if book.format == "pdf":
            return [
                LinkInfo(kind="reader", format="pdf", url=f"{book.url}#reader", mirror=self.mirror),
                LinkInfo(
                    kind="asset",
                    format="pdf",
                    url="http://example.test/book.pdf",
                    mirror=self.mirror,
                    content_type="application/pdf",
                    content_length=2048,
                    is_direct_asset=True,
                    restricted_by_site_ui=True,
                ),
            ]
        if book.format == "audio":
            return [
                LinkInfo(
                    kind="reader", format="audio", url=f"{book.url}#reader", mirror=self.mirror
                ),
                LinkInfo(
                    kind="asset",
                    format="audio",
                    url="http://example.test/audio/track-001.mp3",
                    mirror=self.mirror,
                    content_type="audio/mpeg",
                    content_length=4096,
                    is_direct_asset=True,
                ),
                LinkInfo(
                    kind="asset",
                    format="audio",
                    url="http://example.test/audio/track-002.mp3",
                    mirror=self.mirror,
                    content_type="audio/mpeg",
                    content_length=4096,
                    is_direct_asset=True,
                ),
            ]
        if book.format == "text":
            return [
                LinkInfo(
                    kind="reader",
                    format="text",
                    url=book.url,
                    mirror=self.mirror,
                    is_direct_asset=False,
                )
            ]
        return []

    def _request(self, method: str, url: str, **kwargs):
        class Response:
            ok = True
            status_code = 200

            def __init__(self, content: bytes) -> None:
                self.headers = {"Content-Length": str(len(content))}
                self._content = content

            def iter_content(self, chunk_size):
                yield self._content

            def close(self):
                return None

        return Response(self.stream_bytes)

    def export_text(self, book: BookMetadata) -> str:
        return f"{book.title}\nSource: {book.url}\n\n" + ("Readable text. " * 40)

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

    def list_title_initial_books(
        self, initial: str, format=None, page: int = 1, limit: int | None = None
    ):
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


def test_plan_download_supports_pdf_with_restriction_warning(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    plan = client.plan_download({"title": "pdf book"}, format="pdf", out_dir=str(tmp_path))

    assert plan.format == "pdf"
    assert plan.output_path.endswith(".pdf")
    assert plan.asset.url == "http://example.test/book.pdf"
    assert plan.asset.restricted_by_site_ui is True
    assert plan.warnings


def test_plan_download_supports_audio_bundle(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    plan = client.plan_download({"title": "audio book"}, format="audio", out_dir=str(tmp_path))

    assert plan.format == "audio"
    assert plan.output_path.endswith(".zip")
    assert plan.asset.kind == "asset_bundle"
    assert len(plan.assets) == 2


def test_plan_download_supports_generated_text(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    plan = client.plan_download({"title": "text book"}, format="text", out_dir=str(tmp_path))

    assert plan.format == "text"
    assert plan.output_path.endswith(".txt")
    assert plan.asset.kind == "generated_text"


def test_plan_download_uses_filename_template(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    plan = client.plan_download(
        {"title": "Mưa Đỏ"},
        format="epub",
        out_dir=str(tmp_path),
        filename_template="{title} [{format}] [{tid}]",
    )

    assert Path(plan.output_path).name == "mưa đỏ [epub] [mua-do].epub"


def test_plan_download_rejects_format_mismatch(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    with pytest.raises(UnsupportedFormatError, match="not requested format"):
        client.plan_download(
            {"url": "http://example.test/truyen/truyen.aspx?tid=pdf-book"},
            format="text",
            out_dir=str(tmp_path),
        )


def test_download_without_execute_stays_dry_run(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    result = client.download(
        {"title": "Mưa Đỏ"},
        format="epub",
        out_dir=str(tmp_path),
        dry_run=False,
        execute=False,
    )

    assert result.ok
    assert result.plan.dry_run
    assert result.path is None
    assert not list(tmp_path.iterdir())


def test_dry_run_manifest_writes_download_queue(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]
    manifest = tmp_path / "queue.json"

    result = client.download(
        {"title": "Mưa Đỏ"},
        format="epub",
        out_dir=str(tmp_path),
        execute=False,
        manifest=str(manifest),
    )

    assert result.manifest_path == str(manifest)
    assert '"items"' in manifest.read_text(encoding="utf-8")
    assert '"selector"' in manifest.read_text(encoding="utf-8")


def test_build_download_queue_from_category(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    queue = client.build_download_queue(
        format="epub",
        out_dir=str(tmp_path),
        category=23,
        limit=5,
    )

    assert len(queue.items) == 1
    assert queue.items[0].selector == {"url": "http://example.test/truyen/truyen.aspx?tid=mua-do"}
    assert queue.items[0].format == "epub"


def test_download_from_manifest_executes_queue_without_archive(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter(stream_bytes=b"downloaded bytes")  # type: ignore[assignment]
    queue = client.build_download_queue(format="epub", out_dir=str(tmp_path), category=23)
    manifest = tmp_path / "queue.json"
    client.write_queue_manifest(queue, manifest)

    results = client.download_from_manifest(
        manifest,
        execute=True,
        no_verify=True,
        archive=False,
    )

    assert len(results) == 1
    assert results[0].path is not None
    assert Path(results[0].path).read_bytes() == b"downloaded bytes"


def test_download_records_archive(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter(stream_bytes=b"downloaded bytes")  # type: ignore[assignment]
    archive = tmp_path / "downloads.jsonl"

    result = client.download(
        {"title": "Mưa Đỏ"},
        format="epub",
        out_dir=str(tmp_path),
        execute=True,
        no_verify=True,
        archive_path=str(archive),
    )

    assert result.archive_path == str(archive)
    text = archive.read_text(encoding="utf-8")
    assert '"tid": "mua-do"' in text
    assert '"sha256"' in text


def test_audio_download_fails_on_track_byte_mismatch(tmp_path) -> None:
    client = VnThuQuanClient(config=Config())
    client.adapter = FakeAdapter()  # type: ignore[assignment]

    with pytest.raises(DownloadError, match="Audio byte count mismatch"):
        client.download(
            {"title": "audio book"},
            format="audio",
            out_dir=str(tmp_path),
            execute=True,
            no_verify=True,
        )

    assert not list(tmp_path.glob("*.partial"))


def test_download_fails_over_to_second_mirror(tmp_path, monkeypatch) -> None:
    class FailingAdapter(FakeAdapter):
        def _request(self, method: str, url: str, **kwargs):
            raise DownloadError("primary mirror failed")

    client = VnThuQuanClient(config=Config())
    client.adapter = FailingAdapter("http://vietnamthuquan.eu")  # type: ignore[assignment]

    def make_adapter(mirror: str):
        return FakeAdapter(mirror=mirror, stream_bytes=b"downloaded bytes")

    monkeypatch.setattr(
        "vnthuquan.client.list_mirrors",
        lambda: ["http://vietnamthuquan.eu", "http://vnthuquan.net"],
    )
    monkeypatch.setattr(client, "_make_adapter", make_adapter)

    result = client.download(
        {"title": "Mưa Đỏ"},
        format="epub",
        out_dir=str(tmp_path),
        execute=True,
        no_verify=True,
    )

    assert result.path is not None
    assert Path(result.path).read_bytes() == b"downloaded bytes"
    assert result.plan.mirror == "http://vnthuquan.net"
    assert result.warnings


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
