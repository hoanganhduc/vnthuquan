# vnthuquan Implementation Plan

## Package

- Distribution name: `vnthuquan-hoanganhduc`
- Import package: `vnthuquan`
- CLI command: `vnthuquan`
- Initial version: `0.1.0`
- Current package version: `0.1.2.dev0`
- Python: `>=3.10`
- License: `GPL-3.0-or-later`

## MVP Scope

Supported in the first version:

- search
- search by one or more titles, authors, author IDs, categories, formats, or all fields
- show
- `show --links`
- EPUB, PDF, generated text, and audio download
- EPUB, PDF, text, and audio validation
- categories list/show
- formats list
- latest/newly added ebook listing
- author listing by initial
- title-initial ebook listing
- most-viewed ebook listing
- five-star/rated ebook listing
- category, author, and format ebook listing through a unified `list` command
- derived top lists by category or author with explicit scan limits
- mirrors
- config
- doctor
- README updates, Sphinx documentation updates, and install scripts
- persistent download archive
- reviewed download queue manifests and queue execution
- script field extraction with `--print`
- filename templates
- optional external validators
- persistent HTTP cache
- adaptive resource suggestions, parallel search, and parallel queue downloads
- shell completion setup

Deferred:

- native per-category/per-author top routes if the site adds them later
- about command
- Calibre library integration

## 0.1.1 Hardening Scope

Objective: tighten download reliability and release hygiene without adding bulk
or parallel download commands.

Assumptions:

- `--execute` remains the only switch that writes final files.
- `dry_run` stays in the Python API for compatibility, but `execute` controls
  writes.
- User-pinned `--mirror` must not silently switch mirrors.

Tasks:

- Bump package metadata to `0.1.1`.
- Route direct and audio downloads through the adapter session so cookies,
  headers, retries, request pacing, and optional cache settings are consistent.
- Implement mirror failover for download and validation failures, disabled by
  `--no-failover` or a pinned `--mirror`.
- Add opt-in strict validation for CLI and Python callers.
- Add request pacing and optional TTL cache settings before future bulk or
  parallel work.
- Add opt-in live smoke tests and CI for lint, tests, and package builds.
- Update README and Sphinx documentation.

## Architecture

Package modules:

- `vnthuquan.__init__`
- `vnthuquan.__main__`
- `vnthuquan.cli`
- `vnthuquan.client`
- `vnthuquan.adapter`
- `vnthuquan.models`
- `vnthuquan.validators`
- `vnthuquan.mirrors`
- `vnthuquan.config`
- `vnthuquan.errors`

`LegacySiteAdapter` owns cookies, ASP.NET routes, parsing, AJAX endpoints,
category/format discovery, asset discovery, and mirror quirks.

`VnThuQuanClient` exposes stable public APIs and delegates site-specific work to
the adapter.

## Stable Identity

Book records normalize around:

- `tid`
- `canonical_book_url`
- `mirror`
- `title`
- `author`
- `format`
- `category_id`
- `category_name`

Titles are user-facing labels, not internal identity.

## Core API

- `live_check(mirror=None)`
- `search(query=None, field="title", format=None, formats=None, category=None, categories=None, author_id=None, author_ids=None, titles=None, authors=None, limit=None, page=1, exact=False)`
- `search_by_title(title_or_titles, exact=False, format=None, formats=None, limit=None)`
- `search_by_author(author_or_authors, exact=False, format=None, formats=None, limit=None)`
- `search_by_author_id(author_id_or_ids, query=None, field="all", format=None, formats=None, limit=None, page=1, exact=False)`
- `search_by_category(category_or_categories, query=None, field="all", format=None, formats=None, limit=None, page=1, exact=False)`
- `search_all(query_or_queries, format=None, formats=None, limit=None, exact=False)`
- `list_by_format(format_or_formats, limit=None, page=1)`
- `list_latest(format=None, formats=None, limit=None, page=1)`
- `list_authors(initial, limit=None, page=1)`
- `list_by_title_initial(initial, format=None, formats=None, limit=None, page=1)`
- `list_most_viewed(format=None, formats=None, limit=None, page=1)`
- `list_five_star(format=None, formats=None, limit=None, page=1)`
- `list_top_by_category(category, source="most-viewed", scan_pages=10, format=None, formats=None, limit=20)`
- `list_top_by_author(author_id=None, author=None, source="most-viewed", scan_pages=10, format=None, formats=None, limit=20)`
- `show(selector, assets=False, links=False)`
- `discover_assets(book)`
- `get_asset_links(book, formats=None)`
- `get_download_link(book, format="epub")`
- `download(selector, format="epub", out_dir=None, dry_run=True)`
- `build_download_queue(format="epub", out_dir=None, query=None, category=None, author_id=None, limit=None, page=1, pages=1)`
- `download_from_manifest(path, execute=False, jobs=1)`
- `list_archive(limit=None)`
- `validate_external(path, validators)`
- `detect_resources()`
- `validate(path, format="auto")`
- `list_categories()`
- `get_category(category_id_or_slug)`
- `list_formats()`

## CLI

MVP commands:

- `vnthuquan search`
- `vnthuquan show`
- `vnthuquan download`
- `vnthuquan validate`
- `vnthuquan list`
- `vnthuquan categories`
- `vnthuquan formats`
- `vnthuquan mirrors`
- `vnthuquan config`
- `vnthuquan archive`
- `vnthuquan completion`
- `vnthuquan doctor`

Global flags:

- `--json`
- `--verbose`
- `--quiet`
- `--debug`
- `--no-color`
- `--config PATH`
- `--timeout SECONDS`
- `--retries N`
- `--print FIELD[,FIELD]`

`show` and `download` accept exactly one selector: `--title`, `--url`, or `--id`.

`download` is dry-run by default. `--execute` is required before final files are
written. Executable download formats are:

- `epub`: direct EPUB asset
- `pdf`: direct PDF source exposed by the site reader, with a warning when the reader marks download disabled
- `text`: generated UTF-8 text export assembled from the site's chapter reader
- `audio`: ZIP bundle containing all discovered MP3 assets plus `manifest.json`

Bulk downloads are a two-step queue workflow:

1. `vnthuquan download --all ... --manifest queue.json --dry-run`
2. `vnthuquan download --from-manifest queue.json --execute [--jobs auto]`

`download --all` creates queue manifests only. It does not directly download
multiple books.

## Link Sharing

Use `show --links` to share URLs. Link output distinguishes:

- book page
- reader URL
- direct asset URL
- mirror used
- content type
- content length
- whether the site UI restricts direct download

Links are discovered live; direct asset paths are not guessed.

## Validation

EPUB validation checks:

- byte count when expected size is available
- SHA256
- ZIP integrity
- EPUB mimetype
- `META-INF/container.xml`
- OPF path
- manifest files
- spine files
- TOC/nav when available
- readable content docs
- demo-marker heuristic

Validation reports separate facts:

- `transfer_complete`
- `file_type_valid`
- `container_valid`
- `content_readable`
- `demo_suspected`
- `content_completeness`
- `warnings`
- `errors`

`content_completeness` defaults to `unknown`.

Additional format validation checks:

- PDF: byte count, SHA256, `%PDF-` header, EOF marker warning, readable payload size
- text: SHA256, UTF-8 decoding, readable text length, demo/sample-marker scan
- audio: ZIP integrity, MP3 entry count, MP3 header checks, SHA256

Text export validation proves only that the generated file is readable. It does
not prove that the source site has every canonical chapter.

## Download Safety

Download folder resolution:

1. `--out`
2. config `download_dir`
3. `VNTHUQUAN_DOWNLOAD_DIR`
4. `~/Downloads/vnthuquan`

Folders are created only with `--execute`. Downloads write `.partial` first and
atomically rename after validation. Existing same-SHA256 files are skipped.
Existing different files fail unless `--overwrite` is supplied.

`--strict-verify` applies stricter validation after a download. The Python API
passes this as `strict_verify=True`.

## Mirrors

Known mirrors:

- `http://vietnamthuquan.eu`
- `http://vnthuquan.net`

Download failover re-discovers assets on the new mirror first. Host
substitution is avoided. User-pinned `--mirror` is not silently changed.

## Categories And Formats

Category, author, title-initial, ranking, and format commands are read-only:

- `vnthuquan list latest --page 1 --limit 20`
- `vnthuquan list authors --initial A --page 1`
- `vnthuquan list title-initial A --format epub`
- `vnthuquan list most-viewed --page 1`
- `vnthuquan list five-star --page 1`
- `vnthuquan list category 23 --format epub`
- `vnthuquan list author 284 --format epub`
- `vnthuquan list format epub --page 1`
- `vnthuquan list top --category 6 --source most-viewed --scan-pages 20`
- `vnthuquan list top --author-id 284 --source most-viewed --scan-pages 20`
- `vnthuquan categories list`
- `vnthuquan categories show 23`
- `vnthuquan formats list`
- `vnthuquan search --category 23 --format epub --page 1`
- `vnthuquan search --format pdf,epub --page 1`
- `vnthuquan search --author "Kim Dung" --author "Chu Lai" --format epub --format pdf`

Format IDs:

- text: `0`
- image: `1`
- pdf: `2`
- audio: `3`
- epub: `4`

Category + format filtering is supported for search/listing. Bulk category
downloads are deferred.

Native site list routes confirmed:

- `/truyen/default.aspx?tranghientai=N` for latest/newly added books
- `/truyen/tacgia.aspx?tacgia=A&tranghientai=N` for authors by initial
- `/truyen/mautu.aspx?tua=A&tranghientai=N` for titles by initial
- `/truyen/xemnhieu.aspx?tranghientai=N` for global most-viewed books
- `/truyen/Namsao_moi.aspx?tranghientai=N` for global five-star/rated books
- `/truyen/theloai.aspx?theloaiid=ID&tranghientai=N` for category books
- `/truyen/tacpham.aspx?tacgiaid=ID&tranghientai=N` for author books
- `/truyen/dangsach.aspx?dangsach=ID&tranghientai=N` for format books

Top-by-category and top-by-author are derived by scanning global ranked lists
and filtering locally because the live site ignores category/author parameters
on the global ranking routes. CLI output and docs must make this scan limit
explicit.

## Failure Handling

Typed errors:

- `VnThuQuanError`
- `LiveCheckError`
- `MirrorUnavailableError`
- `SearchError`
- `AmbiguousResultError`
- `NotFoundError`
- `ParseError`
- `AssetDiscoveryError`
- `DownloadError`
- `ValidationError`
- `FilesystemError`
- `ConfigError`
- `UnsupportedFormatError`

Exit codes:

- `0` success
- `1` general error
- `2` CLI usage error
- `3` not found
- `4` ambiguous result
- `5` network/mirror error
- `6` download error
- `7` validation error
- `8` filesystem error
- `9` config error

## JSON Contract

JSON schemas to keep stable:

- `SearchResult`
- `BookMetadata`
- `LinkInfo`
- `DownloadPlan`
- `DownloadResult`
- `ValidationResult`
- `ErrorResult`

`--json` emits script-safe output and suppresses decorative progress.

## Manifest

Dry-run downloads and `download --all` may write a queue manifest with
`--manifest PATH`. Executed single downloads may write a result manifest with
the same flag. Result manifests contain selector, resolved book, mirror, asset
URL, output path, SHA256, validation result, timestamp, warnings, and errors.

## Archive

Executed downloads are recorded in a JSONL archive unless `--no-archive` is
used. Archive records include timestamp, TID, URL, title, author, format,
mirror, output path, SHA256, size, validation status, and skipped status.

Default archive path:

- `~/.local/share/vnthuquan/downloads.jsonl`

Commands:

- `vnthuquan archive path`
- `vnthuquan archive list --limit 20`

## Parallelism And Resources

Parallel search and queue execution are explicit:

- `vnthuquan search ... --jobs auto`
- `vnthuquan download --from-manifest queue.json --execute --jobs auto`

`--jobs auto` uses local CPU/memory detection but caps concurrency
conservatively for the legacy live site. Parallel workers disable persistent
HTTP cache writes to avoid cache-file races.

Use `vnthuquan doctor --resources` to inspect CPU, memory, suggested search
jobs, suggested download jobs, and suggested request interval.

## External Validators

Internal validation remains the default. External validators are opt-in:

- `vnthuquan validate book.epub --external`
- `vnthuquan validate book.epub --epubcheck`
- `vnthuquan validate book.epub --ace`
- `vnthuquan download --title ... --format epub --execute --epubcheck`

Missing external executables are reported as validation failures when
explicitly requested.

## Shell Completion

Shell completion is optional through `argcomplete`:

- install with `pip install "vnthuquan-hoanganhduc[completion]"`
- inspect setup with `vnthuquan completion bash|zsh|fish`

## Documentation

Generate:

- `README.md`
- `PLAN.md`
- `docs/PROJECT_DOCUMENTATION.md`
- `docs/requirements.txt`
- `docs/source/conf.py`
- `docs/source/index.rst`
- `docs/source/usage.rst`
- `docs/source/configuration.rst`
- `docs/source/cli_reference.rst`
- `docs/source/validation.rst`
- `docs/source/mirrors.rst`
- `docs/source/categories.rst`
- `docs/source/api_reference.rst`
- `docs/source/project_documentation.md`

Document only MVP as supported. Deferred features belong in a future-work
section.

When list features change, update both:

- README quick examples
- Sphinx usage, CLI reference, categories/listing docs, and project
  documentation

## GitHub Pages

Add `.github/workflows/docs.yml` to build Sphinx docs and publish HTML to a
`web` branch, matching the `getscipapers` pattern.

Repository/Page settings should be configured through `gh` CLI, not manual UI,
where the GitHub API supports it.

## Install Automation

Add:

- `pyproject.toml`
- `setup.py`
- `requirements.txt`
- `Makefile`
- `scripts/install.sh`
- `scripts/dev_install.sh`
- `scripts/clean.sh`

The default virtual environment path is `~/.vnthuquan`.

## Safety And Politeness

- Dry-run by default.
- Conservative retries/timeouts.
- Conservative request pacing before future bulk/parallel work.
- Optional TTL cache for non-streaming adapter requests.
- Users are responsible for rights and permissions.
- The tool discovers live exposed links and does not guess private paths.

## Implementation Order

1. Create plan and package metadata.
2. Add install scripts and Makefile.
3. Add docs skeleton and docs workflow.
4. Implement `LegacySiteAdapter`.
5. Implement `search`, `show`, and `show --links`.
6. Implement EPUB discovery.
7. Implement dry-run `download`.
8. Implement EPUB download and validation.
9. Implement `validate PATH`.
10. Add mirrors/config/doctor.
11. Add read-only categories/formats.
12. Add read-only listing APIs and `vnthuquan list` CLI.
13. Add PDF, generated text, and audio ZIP download paths.
14. Add PDF, text, and audio validation.
15. Update README and Sphinx docs for listing and download examples.
16. Verify tests and docs locally.
17. Configure GitHub Pages via `gh` after repository setup.
