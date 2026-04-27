# vnthuquan Project Documentation

## Architecture

`vnthuquan` separates site-specific parsing from the public client. The
`LegacySiteAdapter` owns ASP.NET route details, cookies, parser rules, and asset
discovery. `VnThuQuanClient` exposes stable methods and handles download
planning, output paths, and validation.

## Download Flow

1. Resolve one selector: title, URL, or tid.
2. Fetch book metadata.
3. Discover EPUB asset links through the site AJAX endpoint.
4. Build a dry-run `DownloadPlan`.
5. If `--execute` is supplied, stream to `.partial`.
6. Validate the EPUB.
7. Atomically rename the file after validation.

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

Validation checks transfer size, SHA256, ZIP integrity, EPUB package structure,
manifest/spine readability, TOC/nav presence, and demo-marker heuristics.
Canonical completeness remains `unknown` unless independently verified.

## MVP Boundaries

MVP supports EPUB downloads only. PDF, audio, text export, bulk downloads, cache,
top lists, and parallelism are deferred.

## Safety

Downloads are dry-run by default. Users are responsible for rights and
permissions for any material they download.
