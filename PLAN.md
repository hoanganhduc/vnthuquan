# vnthuquan Implementation Plan

## Package

- Distribution name: `vnthuquan-hoanganhduc`
- Import package: `vnthuquan`
- CLI command: `vnthuquan`
- Initial version: `0.1.0`
- Python: `>=3.10`
- License: `GPL-3.0-or-later`

## MVP Scope

Supported in the first version:

- search
- show
- `show --links`
- EPUB download
- EPUB validation
- categories list/show
- formats list
- mirrors
- config
- doctor
- documentation and install scripts

Deferred:

- bulk category downloads
- top lists
- PDF/audio/text downloads
- text export
- persistent cache
- parallel downloads
- resource auto-tuning
- shell completion
- about command

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
- `search(query, field="title", format=None, limit=None, page=1)`
- `show(selector, assets=False, links=False)`
- `discover_assets(book)`
- `get_asset_links(book, formats=None)`
- `get_download_link(book, format="epub")`
- `download(selector, format="epub", out_dir=None, dry_run=True)`
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
- `vnthuquan categories`
- `vnthuquan formats`
- `vnthuquan mirrors`
- `vnthuquan config`
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

`show` and `download` accept exactly one selector: `--title`, `--url`, or `--id`.

`download` is dry-run by default. `--execute` is required before final files are
written. MVP actual downloads support EPUB only.

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

## Download Safety

Download folder resolution:

1. `--out`
2. config `download_dir`
3. `VNTHUQUAN_DOWNLOAD_DIR`
4. `~/Downloads/vnthuquan`

Folders are created only with `--execute`. Downloads write `.partial` first and
atomically rename after validation. Existing same-SHA256 files are skipped.
Existing different files fail unless `--overwrite` is supplied.

## Mirrors

Known mirrors:

- `http://vietnamthuquan.eu`
- `http://vnthuquan.net`

Failover re-discovers assets on the new mirror first. Host substitution is last
resort and must be reported. User-pinned `--mirror` is not silently changed.

## Categories And Formats

MVP category/format commands are read-only:

- `vnthuquan categories list`
- `vnthuquan categories show 23`
- `vnthuquan formats list`

Format IDs:

- text: `0`
- image: `1`
- pdf: `2`
- audio: `3`
- epub: `4`

Category + format filtering and bulk category downloads are deferred.

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

Single downloads may write a manifest with `--manifest PATH`. The manifest
contains selector, resolved book, mirror, asset URL, output path, SHA256,
validation result, timestamp, warnings, and errors.

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
- Rate limiting before future bulk/parallel work.
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
12. Verify tests and docs locally.
13. Configure GitHub Pages via `gh` after repository setup.
