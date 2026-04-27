# vnthuquan

<div align="center">
  <a href="https://www.buymeacoffee.com/hoanganhduc" target="_blank" rel="noopener noreferrer">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40" style="margin-right: 10px;" />
  </a>
  <a href="https://ko-fi.com/hoanganhduc" target="_blank" rel="noopener noreferrer">
    <img src="https://storage.ko-fi.com/cdn/kofi3.png?v=3" alt="Ko-fi" height="40" />
  </a>
  <a href="https://bmacc.app/tip/hoanganhduc" target="_blank" rel="noopener noreferrer">
    <img src="https://bmacc.app/images/bmacc-logo.png" alt="Buy Me a Crypto Coffee" style="height: 40px;" />
  </a>
</div>

![Release](https://img.shields.io/github/v/release/hoanganhduc/vnthuquan?include_prereleases&label=release)
![Tag](https://img.shields.io/github/v/tag/hoanganhduc/vnthuquan?label=tag&sort=semver)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
[![Docs](https://github.com/hoanganhduc/vnthuquan/actions/workflows/docs.yml/badge.svg)](https://github.com/hoanganhduc/vnthuquan/actions/workflows/docs.yml)
![GitHub](https://img.shields.io/badge/GitHub-Repo-black?logo=github)
![Status](https://img.shields.io/badge/status-pre--release-yellow)
![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![EPUB](https://img.shields.io/badge/EPUB-downloads-orange?logo=bookstack)

`vnthuquan` is a Python package and CLI for discovering books on Vietnam Thu
Quan legacy mirrors and downloading EPUB assets exposed by the site.

The first version is intentionally conservative: downloads are dry-run by
default, EPUB is the only supported download format, and validation reports what
can be proven structurally without claiming canonical completeness.

## Current Scope

Supported in `0.1.0`:

- search books
- search by one or more titles, authors, author IDs, categories, formats, or all fields
- show metadata
- show reader/direct links
- dry-run EPUB downloads
- execute EPUB downloads with validation
- validate saved EPUB files
- list categories and formats
- list latest books, authors, title initials, most-viewed books, five-star books, category books, author books, and format books
- derive top books by category or author from bounded scans of global ranked lists
- check mirrors and basic environment health

Deferred:

- PDF/audio/text downloads
- text export
- bulk category downloads
- native per-category/per-author top routes if the site adds them later
- persistent cache
- parallel downloads

## Installation

```bash
git clone https://github.com/hoanganhduc/vnthuquan.git
cd vnthuquan
bash scripts/install.sh
source ~/.vnthuquan/bin/activate
vnthuquan --version
```

Developer install:

```bash
bash scripts/dev_install.sh
source ~/.vnthuquan/bin/activate
vnthuquan --help
```

## Quick Usage

Search with one selector:

```bash
vnthuquan search "cthulhu"
vnthuquan search --title "Mưa Đỏ" --exact
vnthuquan search --author "Kim Dung" --format epub
vnthuquan search --category 23 --format epub --page 1 --limit 10
```

Use repeated flags when you want more than one value. Values within the same
selector are combined as OR filters:

```bash
vnthuquan search --title "Mưa Đỏ" --title "Ăn Mày Dĩ Vãng"
vnthuquan search --author "Kim Dung" --author "Chu Lai" --format epub --format pdf
vnthuquan search --author-id 42 --author-id 1600 --limit 10
vnthuquan search --category 23 --category 26 --format epub --limit 10
```

Formats can be repeated or comma-separated:

```bash
vnthuquan search --author "Kim Dung" --format pdf,epub
vnthuquan search --author "Kim Dung" --format pdf --format epub
```

Combine different filter families when the site exposes enough metadata. For
example, this searches two authors, keeps only EPUB/PDF results, and limits the
display:

```bash
vnthuquan search \
  --author "Kim Dung" \
  --author "Chu Lai" \
  --format epub,pdf \
  --limit 10
```

Search title and author fields together:

```bash
vnthuquan search "Chu Lai" --all --limit 10
vnthuquan search "Mưa Đỏ" "Thiên Long Bát Bộ" --all --format epub
```

List by category, author ID, or format:

```bash
vnthuquan categories list
vnthuquan categories show 23
vnthuquan formats list
vnthuquan list category 23 --format epub --page 1
vnthuquan list author 284 --format epub --page 1
vnthuquan list format epub --page 1 --limit 10
vnthuquan search --category 23 --category 26 --format epub --page 1
vnthuquan search --author-id 42 --author-id 1600 --format epub --page 1
vnthuquan search --format pdf,epub --page 1 --limit 10
```

List site indexes and rankings:

```bash
vnthuquan list latest --page 1 --limit 10
vnthuquan list authors --initial A --page 1
vnthuquan list title-initial A --format epub --page 1
vnthuquan list most-viewed --page 1 --limit 10
vnthuquan list five-star --page 1 --limit 10
```

Derived top lists scan global ranked pages and filter locally because the site
does not expose native per-category or per-author ranking routes:

```bash
vnthuquan list top --category 6 --source most-viewed --scan-pages 20 --limit 10
vnthuquan list top --author-id 284 --source most-viewed --scan-pages 20 --limit 10
```

Return machine-readable output:

```bash
vnthuquan --json search --title "Mưa Đỏ" --title "Thiên Long Bát Bộ" --format epub
vnthuquan --json list authors --initial A --page 1
```

Python wrapper examples:

```python
from vnthuquan import VnThuQuanClient

client = VnThuQuanClient()

results = client.search(
    titles=["Mưa Đỏ", "Thiên Long Bát Bộ"],
    formats=["epub"],
    limit=10,
)

author_results = client.search_by_author(
    ["Kim Dung", "Chu Lai"],
    formats="epub,pdf",
    limit=10,
)

latest = client.list_latest(limit=10)
authors = client.list_authors("A", limit=30)
top_kiem_hiep = client.list_top_by_category(6, source="most-viewed", scan_pages=20, limit=10)
```

Show metadata and links:

```bash
vnthuquan show --title "Lời hiệu triệu của Cthulhu" --links
```

Dry-run a download:

```bash
vnthuquan download \
  --title "Lời hiệu triệu của Cthulhu" \
  --format epub \
  --out ~/Downloads \
  --dry-run
```

Execute a download:

```bash
vnthuquan download \
  --title "Lời hiệu triệu của Cthulhu" \
  --format epub \
  --out ~/Downloads \
  --execute
```

Validate an EPUB:

```bash
vnthuquan validate ~/Downloads/book.epub
```

## Safety

This tool discovers links exposed by the site. Users are responsible for making
sure they have the right to download or use any material. Validation confirms
transfer and EPUB structure; it does not prove that an ebook matches a canonical
edition unless an external source is checked separately.
