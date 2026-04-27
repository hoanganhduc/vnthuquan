# vnthuquan Project Documentation

## Architecture

`vnthuquan` separates site-specific parsing from the public client. The
`LegacySiteAdapter` owns ASP.NET route details, cookies, parser rules, and asset
discovery. `VnThuQuanClient` exposes stable methods and handles download
planning, output paths, and validation.

## Download Flow

1. Resolve one selector: title, URL, or tid.
2. Fetch book metadata.
3. Discover format-specific links through the site AJAX endpoint or reader page.
4. Build a dry-run `DownloadPlan`.
5. If `--execute` is supplied, stream or generate to `.partial`.
6. Validate the saved format.
7. Atomically rename the file after validation.
8. Record a JSONL archive entry unless archive recording is disabled.

Direct and audio asset downloads use the same adapter session as search and
listing, so cookies, headers, retries, request pacing, and optional cache
settings are consistent. Executed downloads retry other known mirrors after
download or validation failures unless failover is disabled or the user pins a
specific mirror.

Supported executable formats:

- `epub`: direct EPUB asset.
- `pdf`: PDF source exposed by the reader; the plan warns when the reader marks direct download disabled.
- `text`: generated UTF-8 export assembled from text chapter AJAX responses.
- `audio`: ZIP bundle of discovered MP3 files plus `manifest.json`.

The CLI keeps downloads dry-run by default. Dry-run output is part of the
normal workflow because it exposes the exact asset URL, planned output path,
warnings, expected size when available, and validation checks before any file is
written.

Bulk downloads use a queue-first workflow. `download --all` resolves a bounded
set of results and writes a queue manifest; `download --from-manifest` executes
that reviewed queue. Parallel queue execution is explicit through `--jobs`.

## Search Flow

`search` supports one or more titles, authors, author IDs, categories, formats,
and all-field lookup values. Title and author searches use the site's AJAX
endpoint. Category, author ID, and format searches use the site's paginated
listing pages and then apply optional client-side query and exact-match filters.
Multiple values in the same dimension are ORed; different dimensions are
combined when the site exposes enough metadata, such as author + format or
category + format.

Examples:

```bash
vnthuquan search --title "Mưa Đỏ" --title "Thiên Long Bát Bộ" --format epub
vnthuquan search --author "Kim Dung" --author "Chu Lai" --format epub,pdf --limit 10
vnthuquan search --category 23 --category 26 --format epub --page 1
vnthuquan --json search "Chu Lai" --all --format epub
vnthuquan search --category 23 --category 26 --format epub --jobs auto
vnthuquan search --author "Kim Dung" --format epub --print title,url
```

Python callers can pass either a scalar or list for multi-value selectors:

```python
from vnthuquan import VnThuQuanClient

client = VnThuQuanClient()
results = client.search(
    authors=["Kim Dung", "Chu Lai"],
    formats=["epub", "pdf"],
    limit=10,
)
```

## Listing Flow

Native listing methods wrap the site's paginated routes:

```bash
vnthuquan list latest --page 1 --limit 10
vnthuquan list authors --initial A --page 1
vnthuquan list title-initial A --format epub
vnthuquan list most-viewed --page 1
vnthuquan list five-star --page 1
vnthuquan list category 23 --format epub
vnthuquan list author 284 --format epub
vnthuquan list format epub
```

Derived top lists use global ranked pages and then filter locally:

```bash
vnthuquan list top --category 6 --source most-viewed --scan-pages 20 --limit 10
vnthuquan list top --author-id 284 --source most-viewed --scan-pages 20 --limit 10
```

These derived lists are complete only for the ranked pages scanned.

## Validation Flow

Validation checks transfer size when available, SHA256, and format-specific
structure: EPUB package structure, PDF header/EOF markers, UTF-8 text
readability, or audio ZIP/MP3 headers. Canonical completeness remains `unknown`
unless independently verified.

Strict validation is opt-in through `vnthuquan validate --strict` or
`vnthuquan download --strict-verify`. It turns selected structural warnings into
errors, including missing PDF EOF markers, HTML-looking text exports, missing
EPUB TOC/nav entries, demo/sample markers, and audio manifests that do not match
bundled MP3 files.

External validators are opt-in through `--external`, `--epubcheck`, and `--ace`.
Missing external executables are reported as validation failures when requested.

Image-format entries are searchable and listable, but they do not yet have an
executable download path because the live site does not expose one stable
ebook-level image asset route.

## Archive And Cache

Executed downloads are recorded in `~/.local/share/vnthuquan/downloads.jsonl`
by default. The archive records TID, URL, title, author, format, output path,
SHA256, size, validation status, mirror, timestamp, and skipped status.

The HTTP cache is persistent when `cache_ttl_seconds` is greater than zero. By
default it writes to `~/.cache/vnthuquan/http-cache.json`; parallel workers
disable persistent cache writes to avoid cache-file races.

## MVP Boundaries

Native per-category/per-author top routes and Calibre integration are deferred.
Top-by-category and top-by-author remain derived scans over global ranked
pages.

## Safety

Downloads are dry-run by default. Users are responsible for rights and
permissions for any material they download.
