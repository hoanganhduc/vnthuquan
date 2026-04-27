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
