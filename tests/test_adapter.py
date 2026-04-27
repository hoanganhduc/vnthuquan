from __future__ import annotations

from vnthuquan.adapter import LegacySiteAdapter


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
    assert results[0].format == "epub"
    assert results[0].category_id == 23
