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
