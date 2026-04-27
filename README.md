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
[![CI](https://github.com/hoanganhduc/vnthuquan/actions/workflows/ci.yml/badge.svg)](https://github.com/hoanganhduc/vnthuquan/actions/workflows/ci.yml)
[![Docs](https://github.com/hoanganhduc/vnthuquan/actions/workflows/docs.yml/badge.svg)](https://github.com/hoanganhduc/vnthuquan/actions/workflows/docs.yml)
![GitHub](https://img.shields.io/badge/GitHub-Repo-black?logo=github)
![Status](https://img.shields.io/badge/status-pre--release-yellow)
![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![Formats](https://img.shields.io/badge/formats-epub%20%7C%20pdf%20%7C%20text%20%7C%20audio-orange?logo=bookstack)

`vnthuquan` is a Python package and CLI for discovering books on Vietnam Thu
Quan legacy mirrors and downloading ebook assets exposed by the site.

The first version is intentionally conservative: downloads are dry-run by
default, validation reports what can be proven structurally without claiming
canonical completeness, and links are discovered live instead of guessed.

## Current Scope

Supported in `0.1.1`:

- search books
- search by one or more titles, authors, author IDs, categories, formats, or all fields
- show metadata
- show reader/direct links
- dry-run downloads for EPUB, PDF, generated text, and audio ZIP bundles
- execute EPUB, PDF, generated text, and audio downloads with validation
- validate saved EPUB, PDF, text, and audio files
- list categories and formats
- list latest books, authors, title initials, most-viewed books, five-star books, category books, author books, and format books
- derive top books by category or author from bounded scans of global ranked lists
- check mirrors and basic environment health
- automatic download failover across known mirrors unless a mirror is pinned
- opt-in strict validation with `--strict` and `--strict-verify`
- polite request pacing and optional request caching foundations

Deferred:

- bulk category downloads
- native per-category/per-author top routes if the site adds them later
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

Download by format
------------------

Search the format first, then pass either the title, URL, or TID to
`download`. A dry run is the recommended first step because it shows the exact
asset URL, output path, expected size when available, and validation checks.

```bash
vnthuquan search --format pdf --limit 5
vnthuquan search --format text --limit 5
vnthuquan search --format audio --limit 5
```

```bash
vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --format pdf --out ~/Downloads --dry-run
vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --format text --out ~/Downloads --dry-run
vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --format audio --out ~/Downloads --dry-run
```

Use `--execute` after reviewing the dry-run plan:

```bash
vnthuquan download --title "Some PDF Title" --format pdf --out ~/Downloads --execute
vnthuquan download --title "Some Text Title" --format text --out ~/Downloads --execute
vnthuquan download --title "Some Audio Title" --format audio --out ~/Downloads --execute
```

Downloads retry other known mirrors after download or validation failures. Use
`--no-failover` to keep a failing download on the selected mirror. When
`--mirror` is provided, the CLI treats it as pinned and does not silently switch
mirrors.

Format behavior:

- `epub` saves the direct EPUB asset.
- `pdf` saves the PDF source exposed by the site reader and warns when the reader marks direct download as disabled.
- `text` walks the site text chapter list and writes one UTF-8 `.txt` export.
- `audio` packages all discovered MP3 files into one `.zip` with a `manifest.json`.
- `image` entries can be searched and listed, but executable image downloads are not implemented because the site does not expose one stable ebook-level image asset route.

For audio, dry-run first and check `Expected size`; some bundles are hundreds
of MB. For text, validation proves the generated file is readable UTF-8, not
that the source site contains every canonical chapter.

Validate a downloaded file:

```bash
vnthuquan validate ~/Downloads/book.epub
vnthuquan validate ~/Downloads/book.pdf --format pdf
vnthuquan validate ~/Downloads/book.txt --format text
vnthuquan validate ~/Downloads/book.zip --format audio
vnthuquan validate ~/Downloads/book.zip --format audio --strict
```

## Safety

This tool discovers links exposed by the site. Users are responsible for making
sure they have the right to download or use any material. Validation confirms
transfer and file structure; it does not prove that an ebook matches a canonical
edition unless an external source is checked separately.

## Acknowledgements

This package was implemented with help from ChatGPT Codex.
