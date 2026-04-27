# vnthuquan

`vnthuquan` is a Python package and CLI for discovering books on Vietnam Thu
Quan legacy mirrors and downloading EPUB assets exposed by the site.

The first version is intentionally conservative: downloads are dry-run by
default, EPUB is the only supported download format, and validation reports what
can be proven structurally without claiming canonical completeness.

## Current Scope

Supported in `0.1.0`:

- search books
- show metadata
- show reader/direct links
- dry-run EPUB downloads
- execute EPUB downloads with validation
- validate saved EPUB files
- list categories and formats
- check mirrors and basic environment health

Deferred:

- PDF/audio/text downloads
- text export
- bulk category downloads
- top lists
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

Search:

```bash
vnthuquan search "cthulhu"
```

Show metadata and links:

```bash
vnthuquan show --title "Lời hiệu triệu của Cthulhu" --links
```

Dry-run a download:

```bash
vnthuquan download --title "Lời hiệu triệu của Cthulhu" --format epub --out ~/Downloads
```

Execute a download:

```bash
vnthuquan download --title "Lời hiệu triệu của Cthulhu" --format epub --out ~/Downloads --execute
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
