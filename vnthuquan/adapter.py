"""Legacy Vietnam Thu Quan site adapter."""

from __future__ import annotations

import re
import time
from html import unescape
from urllib.parse import parse_qs, quote, urljoin, urlparse, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from .errors import AssetDiscoveryError, LiveCheckError, NotFoundError, ParseError, SearchError
from .mirrors import DEFAULT_MIRROR, normalize_mirror
from .models import Author, BookMetadata, Category, FormatCategory, LinkInfo, MirrorStatus, SearchResult

FORMAT_IDS = {
    "text": 0,
    "image": 1,
    "pdf": 2,
    "audio": 3,
    "epub": 4,
}

FORMAT_NAMES = {value: key for key, value in FORMAT_IDS.items()}

CATEGORY_FALLBACK = [
    (1, "Truyen ngan"),
    (2, "truyen dai"),
    (3, "Bien khao, Tuy But, Tan Van"),
    (4, "Lich su, Da su"),
    (5, "Than Thoai, Co tich"),
    (6, "Kiem Hiep"),
    (7, "Trung Hoa, Huyen Huyen"),
    (8, "Hai Huoc, Tieu lam"),
    (9, "Khoa hoc, Ky Thuat"),
    (10, "Teen, Tuoi Hoa, Thieu Nhi"),
    (11, "Kinh Di, Ma quai"),
    (12, "Trinh Tham, Hinh Su"),
    (13, "Co Van Viet Nam"),
    (14, "Tuyen Tap, Tap Truyen"),
    (15, "Suy ngam, Lam Nguoi, Ky Nang Song"),
    (16, "Nhan Vat, Chan Dung"),
    (17, "Triet Hoc, Kinh Te, Tai Chinh"),
    (18, "Y Hoc, Suc Khoe"),
    (19, "Ngon Tinh, Lang Man"),
    (20, "Phieu Luu, Mao Hiem, Ly ky"),
    (21, "Hoi Ky, Tu Truyen"),
    (22, "Kinh Dien"),
    (23, "Tieu Thuyet"),
    (24, "Ton giao, Chinh Tri"),
    (25, "Truyen Tranh"),
    (26, "Cuoc Chien VN"),
    (27, "Kich, Kich ban"),
    (28, "Sieu Nhien, Huyen bi"),
    (31, "Khoa huyen, gia tuong"),
    (32, "Tien Hiep, Tu Chan"),
    (33, "Tam Ly, Xa Hoi, Hien Thuc"),
    (34, "Phong su, dieu tra, Du ky"),
    (35, "Tho, Truong Ca"),
    (36, "Van Hoc Mien Nam Truoc 75"),
]


def _quote_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            quote(parts.path),
            quote(parts.query, safe="=&?/:"),
            parts.fragment,
        )
    )


def _text(node) -> str | None:
    if node is None:
        return None
    value = unescape(node.get_text(" ", strip=True))
    return re.sub(r"\s+", " ", value).strip() or None


def _tid_from_url(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    tid = query.get("tid", [None])[0]
    if not tid:
        raise ParseError(f"Could not find tid in URL: {url}")
    return tid


def _int_param_from_url(url: str, key: str) -> int | None:
    query = parse_qs(urlparse(url).query)
    value = query.get(key, [None])[0]
    return int(value) if value and value.isdigit() else None


def _int_from_text(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"\D+", "", value)
    return int(digits) if digits else None


def _date_from_text(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b", value)
    return match.group(0) if match else None


def _clean_title(title: str, fmt: str | None = None) -> str:
    cleaned = re.sub(r"\s+", " ", title).strip(" ,-")
    if fmt:
        cleaned = re.sub(rf"\s*\({re.escape(fmt)}\)\s*$", "", cleaned, flags=re.I)
        cleaned = re.sub(rf"\s+{re.escape(fmt)}\s*$", "", cleaned, flags=re.I)
    return cleaned.strip(" ,-")


class LegacySiteAdapter:
    """Adapter for legacy ASP.NET Vietnam Thu Quan routes."""

    def __init__(
        self,
        mirror: str = DEFAULT_MIRROR,
        timeout: float = 30.0,
        retries: int = 2,
        session: requests.Session | None = None,
    ) -> None:
        self.mirror = normalize_mirror(mirror)
        self.timeout = timeout
        self.retries = retries
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "vnthuquan/0.1.0",
                "Cookie": "AspxAutoDetectCookieSupport=1",
            }
        )
        self.session.cookies.set("AspxAutoDetectCookieSupport", "1")

    def _url(self, path: str) -> str:
        return urljoin(f"{self.mirror}/", path.lstrip("/"))

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.request(method, _quote_url(url), timeout=self.timeout, **kwargs)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
        raise LiveCheckError(str(last_error)) from last_error

    def live_check(self) -> MirrorStatus:
        start = time.monotonic()
        try:
            response = self._request(
                "GET",
                self._url("/default.aspx?AspxAutoDetectCookieSupport=1"),
                allow_redirects=True,
            )
            elapsed = time.monotonic() - start
            return MirrorStatus(
                url=self.mirror,
                ok=response.ok,
                status_code=response.status_code,
                elapsed_seconds=round(elapsed, 3),
                error=None if response.ok else response.reason,
            )
        except Exception as exc:  # noqa: BLE001 - returned as status object
            return MirrorStatus(
                url=self.mirror,
                ok=False,
                elapsed_seconds=round(time.monotonic() - start, 3),
                error=str(exc),
            )

    def search(
        self,
        query: str,
        field: str = "title",
        format: str | list[str] | None = None,
        limit: int | None = None,
    ) -> list[SearchResult]:
        field_map = {"title": "tua", "author": "tacgia"}
        theo = field_map.get(field)
        if not theo:
            raise SearchError(f"Unsupported search field: {field}")
        response = self._request(
            "POST",
            self._url("/truyen/timkiem_ajax.aspx?"),
            data={"theo": theo, "chu": query},
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        )
        if not response.ok:
            raise SearchError(f"Search failed with HTTP {response.status_code}")
        results = self._parse_listing(response.text)
        results = self._filter_format(results, format)
        return results[:limit] if limit else results

    def list_author_books(
        self,
        author_id: str | int,
        format: str | list[str] | None = None,
        page: int = 1,
        limit: int | None = None,
    ) -> list[SearchResult]:
        if page < 1:
            raise SearchError("Author page must be >= 1")
        response = self._request(
            "GET",
            self._url(f"/truyen/tacpham.aspx?tranghientai={page}&tacgiaid={author_id}"),
        )
        if not response.ok:
            raise SearchError(f"Author listing failed with HTTP {response.status_code}")
        results = self._parse_listing(response.text)
        author_name = self._parse_author_name(response.text)
        author_id_int = int(author_id) if str(author_id).isdigit() else None
        for result in results:
            if result.author is None:
                result.author = author_name
            if result.author_id is None:
                result.author_id = author_id_int
        results = self._filter_format(results, format)
        return results[:limit] if limit else results

    def list_latest_books(
        self,
        format: str | list[str] | None = None,
        page: int = 1,
        limit: int | None = None,
    ) -> list[SearchResult]:
        if page < 1:
            raise SearchError("Latest page must be >= 1")
        response = self._request(
            "GET",
            self._url(f"/truyen/default.aspx?tranghientai={page}"),
        )
        if not response.ok:
            raise SearchError(f"Latest listing failed with HTTP {response.status_code}")
        results = self._parse_listing(response.text)
        results = self._filter_format(results, format)
        return results[:limit] if limit else results

    def list_title_initial_books(
        self,
        initial: str,
        format: str | list[str] | None = None,
        page: int = 1,
        limit: int | None = None,
    ) -> list[SearchResult]:
        if page < 1:
            raise SearchError("Title-initial page must be >= 1")
        initial = self._normalize_initial(initial)
        response = self._request(
            "GET",
            self._url(f"/truyen/mautu.aspx?tranghientai={page}&tua={quote(initial)}"),
        )
        if not response.ok:
            raise SearchError(f"Title-initial listing failed with HTTP {response.status_code}")
        results = self._parse_listing(response.text)
        results = self._filter_format(results, format)
        return results[:limit] if limit else results

    def list_most_viewed_books(
        self,
        format: str | list[str] | None = None,
        page: int = 1,
        limit: int | None = None,
    ) -> list[SearchResult]:
        if page < 1:
            raise SearchError("Most-viewed page must be >= 1")
        response = self._request(
            "GET",
            self._url(f"/truyen/xemnhieu.aspx?tranghientai={page}"),
        )
        if not response.ok:
            raise SearchError(f"Most-viewed listing failed with HTTP {response.status_code}")
        results = self._parse_listing(response.text)
        results = self._filter_format(results, format)
        return results[:limit] if limit else results

    def list_five_star_books(
        self,
        format: str | list[str] | None = None,
        page: int = 1,
        limit: int | None = None,
    ) -> list[SearchResult]:
        if page < 1:
            raise SearchError("Five-star page must be >= 1")
        response = self._request(
            "GET",
            self._url(f"/truyen/Namsao_moi.aspx?tranghientai={page}"),
        )
        if not response.ok:
            raise SearchError(f"Five-star listing failed with HTTP {response.status_code}")
        results = self._parse_listing(response.text)
        results = self._filter_format(results, format)
        return results[:limit] if limit else results

    def list_authors(
        self,
        initial: str,
        page: int = 1,
        limit: int | None = None,
    ) -> list[Author]:
        if page < 1:
            raise SearchError("Author page must be >= 1")
        initial = self._normalize_initial(initial)
        response = self._request(
            "GET",
            self._url(f"/truyen/tacgia.aspx?tranghientai={page}&tacgia={quote(initial)}"),
        )
        if not response.ok:
            raise SearchError(f"Author listing failed with HTTP {response.status_code}")
        authors = self._parse_authors(response.text, initial=initial)
        return authors[:limit] if limit else authors

    def list_category_books(
        self,
        category: str | int,
        format: str | list[str] | None = None,
        page: int = 1,
        limit: int | None = None,
    ) -> list[SearchResult]:
        if page < 1:
            raise SearchError("Category page must be >= 1")
        category_info = self.get_category(category)
        response = self._request(
            "GET",
            self._url(f"/truyen/theloai.aspx?tranghientai={page}&theloaiid={category_info.id}"),
        )
        if not response.ok:
            raise SearchError(f"Category listing failed with HTTP {response.status_code}")
        results = self._parse_listing(response.text)
        for result in results:
            if result.category_id is None:
                result.category_id = category_info.id
            if result.category_name is None:
                result.category_name = category_info.name
        results = self._filter_format(results, format)
        return results[:limit] if limit else results

    def list_format_books(
        self,
        format: str,
        page: int = 1,
        limit: int | None = None,
    ) -> list[SearchResult]:
        if page < 1:
            raise SearchError("Format page must be >= 1")
        fmt_id = FORMAT_IDS.get(format.lower())
        if fmt_id is None:
            raise SearchError(f"Unsupported format: {format}")
        response = self._request(
            "GET",
            self._url(f"/truyen/dangsach.aspx?tranghientai={page}&dangsach={fmt_id}"),
        )
        if not response.ok:
            raise SearchError(f"Format listing failed with HTTP {response.status_code}")
        results = self._parse_listing(response.text)
        results = self._filter_format(results, format)
        return results[:limit] if limit else results

    def get_book(self, url_or_tid: str) -> BookMetadata:
        url = self.book_url(url_or_tid)
        response = self._request("GET", url)
        if not response.ok:
            raise NotFoundError(f"Book page failed with HTTP {response.status_code}: {url}")
        return self._parse_book_detail(response.text, url)

    def book_url(self, url_or_tid: str) -> str:
        if url_or_tid.startswith("http://") or url_or_tid.startswith("https://"):
            return url_or_tid
        return self._url(f"/truyen/truyen.aspx?tid={url_or_tid}")

    def discover_links(self, book: BookMetadata, formats: list[str] | None = None) -> list[LinkInfo]:
        requested = {fmt.lower() for fmt in formats} if formats else None
        links = [
            LinkInfo(
                kind="book_page",
                format=book.format,
                url=book.url,
                mirror=book.mirror,
                is_direct_asset=False,
            )
        ]
        fmt = (book.format or "").lower()
        if requested and fmt not in requested:
            return links
        if fmt == "epub":
            links.extend(self._discover_epub_links(book))
        elif fmt == "pdf":
            links.extend(self._discover_pdf_links(book))
        elif fmt == "audio":
            links.extend(self._discover_audio_links(book))
        elif fmt == "text":
            links.append(
                LinkInfo(
                    kind="reader",
                    format="text",
                    url=book.url,
                    mirror=book.mirror,
                    is_direct_asset=False,
                    notes=["text entries are read chapter-by-chapter; no direct ebook asset"],
                )
            )
        return links

    def list_categories(self) -> list[Category]:
        response = self._request("GET", self._url("/truyen/"))
        if not response.ok:
            return [Category(id=cid, name=name) for cid, name in CATEGORY_FALLBACK]
        matches = re.findall(r"doitrang\((\d+)\)\">([^<]+)</span>", response.text)
        if not matches:
            return [Category(id=cid, name=name) for cid, name in CATEGORY_FALLBACK]
        return [Category(id=int(cid), name=unescape(name).strip()) for cid, name in matches]

    def get_category(self, value: str | int) -> Category:
        categories = self.list_categories()
        normalized = str(value).casefold().strip()
        for category in categories:
            if str(category.id) == normalized or category.name.casefold() == normalized:
                return self._category_with_counts(category)
        raise NotFoundError(f"Category not found: {value}")

    def list_formats(self) -> list[FormatCategory]:
        formats: list[FormatCategory] = []
        for slug, fmt_id in FORMAT_IDS.items():
            formats.append(self._format_with_counts(FormatCategory(id=fmt_id, name=slug.title(), slug=slug)))
        return formats

    def _parse_listing(self, html: str) -> list[SearchResult]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[SearchResult] = []
        seen: set[str] = set()
        for item in soup.select(".danhsach"):
            href = None
            for anchor in item.find_all("a", href=True):
                if "truyen.aspx?tid=" in anchor["href"]:
                    href = anchor["href"]
                    break
            if not href:
                continue
            url = urljoin(self._url("/truyen/"), href)
            tid = _tid_from_url(url)
            if tid in seen:
                continue
            seen.add(tid)
            title = _text(item.select_one(".truyen-title a")) or _text(item.find("img")) or tid
            author_anchor = item.select_one(".author a")
            author = _text(author_anchor) or _text(item.select_one(".author"))
            author_id = None
            if author_anchor:
                author_id = _int_param_from_url(author_anchor.get("href", ""), "tacgiaid")
            fmt = _text(item.select_one(".label-scan"))
            fmt = fmt.lower() if fmt else None
            date_or_views = _text(item.select_one(".label-time"))
            category_anchor = item.select_one(".label-theloai a")
            category_id = None
            category_name = None
            if category_anchor:
                category_name = _text(category_anchor)
                match = re.search(r"theloaiid=(\d+)", category_anchor.get("href", ""))
                category_id = int(match.group(1)) if match else None
            results.append(
                SearchResult(
                    tid=tid,
                    title=title,
                    author=author,
                    format=fmt,
                    url=url,
                    mirror=self.mirror,
                    author_id=author_id,
                    category_id=category_id,
                    category_name=category_name,
                    date_or_views=date_or_views,
                    added_date=_date_from_text(date_or_views),
                    views=_int_from_text(date_or_views) if date_or_views and "xem" in date_or_views.casefold() else None,
                )
            )
        return results

    def _parse_authors(self, html: str, initial: str | None = None) -> list[Author]:
        soup = BeautifulSoup(html, "html.parser")
        authors: list[Author] = []
        seen: set[tuple[int | None, str]] = set()
        for anchor in soup.find_all("a", href=re.compile(r"tacpham\.aspx\?tacgiaid=")):
            name = _text(anchor)
            if not name:
                continue
            url = urljoin(self._url("/truyen/"), anchor["href"])
            author_id = _int_param_from_url(url, "tacgiaid")
            key = (author_id, name.casefold())
            if key in seen:
                continue
            seen.add(key)
            authors.append(
                Author(
                    name=name,
                    id=author_id,
                    url=url if author_id is not None else None,
                    mirror=self.mirror,
                    initial=initial,
                )
            )
        return authors

    def _filter_format(
        self,
        results: list[SearchResult],
        format: str | list[str] | None = None,
    ) -> list[SearchResult]:
        formats = self._normalize_formats(format)
        if not formats:
            return results
        return [
            result
            for result in results
            if (result.format or "").lower() in formats
            or any(fmt in (result.title or "").lower() for fmt in formats)
        ]

    def _normalize_formats(self, format: str | list[str] | None = None) -> list[str]:
        if not format:
            return []
        raw_values = [format] if isinstance(format, str) else list(format)
        values: list[str] = []
        for raw in raw_values:
            for part in str(raw).split(","):
                value = part.strip().lower()
                if value:
                    values.append(value)
        unsupported = [value for value in values if value not in FORMAT_IDS]
        if unsupported:
            raise SearchError(f"Unsupported format: {', '.join(unsupported)}")
        return list(dict.fromkeys(values))

    def _normalize_initial(self, initial: str) -> str:
        value = initial.strip()
        if not value:
            raise SearchError("Initial must not be empty")
        if value.casefold() in {"#", "number", "numbers", "num", "0-9"}:
            return "1"
        return value[0]

    def _parse_author_name(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        for heading in soup.find_all(["h1", "h2", "h3"]):
            text = _text(heading)
            if not text:
                continue
            normalized = re.sub(r"\s+", " ", text)
            match = re.search(r"T\s*ác\s+Giả:\s*(.+)", normalized, flags=re.I)
            if match:
                return match.group(1).strip()
        return None

    def _parse_book_detail(self, html: str, url: str) -> BookMetadata:
        tid = _tid_from_url(url)
        fmt = self._detect_format(html)
        tuaid = self._detect_tuaid(html)
        soup = BeautifulSoup(html, "html.parser")
        author_anchor = soup.find("a", href=re.compile(r"tacpham\.aspx\?tacgiaid="))
        author = _text(author_anchor)
        raw_title = None
        if author_anchor and author_anchor.parent:
            parent_text = _text(author_anchor.parent)
            if parent_text and author and f" - {author}" in parent_text:
                raw_title = parent_text.split(f" - {author}", 1)[0]
        if not raw_title and soup.title and soup.title.string:
            match = re.search(r"Mời đọc tác phẩm:\s*(.*?),\s*-", soup.title.string)
            raw_title = unescape(match.group(1)) if match else soup.title.string
        title = _clean_title(raw_title or tid, fmt)
        return BookMetadata(
            tid=tid,
            title=title,
            author=author,
            format=fmt,
            url=url,
            mirror=self.mirror,
            tuaid=tuaid,
            raw_title=raw_title,
        )

    def _detect_format(self, html: str) -> str | None:
        if "chuonghoi_epub2.aspx" in html:
            return "epub"
        if "chuonghoi_pdf.aspx" in html:
            return "pdf"
        if "chuonghoi_audio.aspx" in html:
            return "audio"
        if "chuonghoi_moi.aspx" in html:
            return "text"
        return None

    def _detect_tuaid(self, html: str) -> str | None:
        patterns = [
            r'thong_so\+="&tuaid=";\s*thong_so\+="(\d+)"',
            r"tuaid=(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None

    def _post_chapter_endpoint(self, endpoint: str, book: BookMetadata) -> str:
        if not book.tuaid:
            raise AssetDiscoveryError(f"Book has no tuaid: {book.url}")
        response = self._request(
            "POST",
            self._url(f"/truyen/{endpoint}"),
            data={"tuaid": book.tuaid, "chuongid": ""},
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        )
        if not response.ok:
            raise AssetDiscoveryError(f"Asset AJAX failed with HTTP {response.status_code}")
        return response.text

    def _discover_epub_links(self, book: BookMetadata) -> list[LinkInfo]:
        html = self._post_chapter_endpoint("chuonghoi_epub2.aspx?", book)
        soup = BeautifulSoup(html, "html.parser")
        iframe = soup.find("iframe", src=True)
        if not iframe:
            raise AssetDiscoveryError("Could not find EPUB iframe")
        reader_url = urljoin(self._url("/truyen/"), iframe["src"])
        query = parse_qs(urlparse(reader_url).query)
        asset_url = query.get("bookPath", [None])[0]
        if not asset_url:
            raise AssetDiscoveryError("Could not find EPUB bookPath")
        reader = LinkInfo(
            kind="reader",
            format="epub",
            url=reader_url,
            mirror=self.mirror,
            is_direct_asset=False,
        )
        asset = self._asset_link("epub", asset_url)
        return [reader, asset]

    def _discover_pdf_links(self, book: BookMetadata) -> list[LinkInfo]:
        html = self._post_chapter_endpoint("chuonghoi_pdf.aspx?", book)
        soup = BeautifulSoup(html, "html.parser")
        iframe = soup.find("iframe", src=True)
        if not iframe:
            raise AssetDiscoveryError("Could not find PDF iframe")
        reader_url = urljoin(self._url("/truyen/"), iframe["src"])
        reader_response = self._request("GET", reader_url)
        if not reader_response.ok:
            raise AssetDiscoveryError(f"PDF reader failed with HTTP {reader_response.status_code}")
        restricted = "enableDownload:false" in reader_response.text.replace(" ", "")
        match = re.search(r'source\s*:\s*"([^"]+\.pdf)"', reader_response.text)
        links = [
            LinkInfo(
                kind="reader",
                format="pdf",
                url=reader_url,
                mirror=self.mirror,
                is_direct_asset=False,
                restricted_by_site_ui=restricted,
            )
        ]
        if match:
            links.append(
                self._asset_link(
                    "pdf",
                    urljoin(reader_url, match.group(1)),
                    restricted_by_site_ui=restricted,
                )
            )
        return links

    def _discover_audio_links(self, book: BookMetadata) -> list[LinkInfo]:
        html = self._post_chapter_endpoint("chuonghoi_audio.aspx?", book)
        soup = BeautifulSoup(html, "html.parser")
        iframe = soup.find("iframe", src=True)
        if not iframe:
            raise AssetDiscoveryError("Could not find audio iframe")
        reader_url = urljoin(self._url("/truyen/"), iframe["src"])
        reader_response = self._request("GET", reader_url)
        if not reader_response.ok:
            raise AssetDiscoveryError(f"Audio reader failed with HTTP {reader_response.status_code}")
        reader = LinkInfo(
            kind="reader",
            format="audio",
            url=reader_url,
            mirror=self.mirror,
            is_direct_asset=False,
        )
        reader_soup = BeautifulSoup(reader_response.text, "html.parser")
        assets = []
        for anchor in reader_soup.find_all("a", href=True):
            if anchor["href"].lower().endswith(".mp3"):
                assets.append(self._asset_link("audio", urljoin(reader_url, anchor["href"])))
        return [reader, *assets]

    def _asset_link(
        self,
        fmt: str,
        url: str,
        restricted_by_site_ui: bool | None = None,
    ) -> LinkInfo:
        content_type = None
        content_length = None
        try:
            response = self._request("HEAD", url, allow_redirects=True)
            if response.ok:
                content_type = response.headers.get("Content-Type")
                if response.headers.get("Content-Length"):
                    content_length = int(response.headers["Content-Length"])
        except Exception:
            pass
        return LinkInfo(
            kind="asset",
            format=fmt,
            url=url,
            mirror=self.mirror,
            content_type=content_type,
            content_length=content_length,
            is_direct_asset=True,
            restricted_by_site_ui=restricted_by_site_ui,
        )

    def _category_with_counts(self, category: Category) -> Category:
        response = self._request(
            "GET",
            self._url(f"/truyen/theloai.aspx?theloaiid={category.id}"),
        )
        if response.ok:
            match = re.search(r'<span class="tinhtong">\s*([0-9]+)\s*Tác', response.text)
            pages = re.findall(rf"tranghientai=(\d+)&theloaiid={category.id}", response.text)
            category.count = int(match.group(1)) if match else None
            category.pages = max(map(int, pages), default=1)
        return category

    def _format_with_counts(self, fmt: FormatCategory) -> FormatCategory:
        response = self._request(
            "GET",
            self._url(f"/truyen/dangsach.aspx?tranghientai=1&dangsach={fmt.id}"),
        )
        if response.ok:
            match = re.search(r'<span class="tacgiad">\s*([0-9]+)\s*Tác', response.text)
            pages = re.findall(rf"tranghientai=(\d+)&dangsach={fmt.id}", response.text)
            fmt.count = int(match.group(1)) if match else None
            fmt.pages = max(map(int, pages), default=1)
        return fmt
