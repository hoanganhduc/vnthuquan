"""Data models for public API and JSON output."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _clean_dict(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_clean_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_dict(item) for key, item in value.items()}
    return value


@dataclass(slots=True)
class MirrorStatus:
    url: str
    ok: bool
    status_code: int | None = None
    elapsed_seconds: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class Category:
    id: int
    name: str
    count: int | None = None
    pages: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class FormatCategory:
    id: int
    name: str
    slug: str
    count: int | None = None
    pages: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class Author:
    name: str
    id: int | None
    url: str | None
    mirror: str
    initial: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class SearchResult:
    tid: str
    title: str
    author: str | None
    format: str | None
    url: str
    mirror: str
    author_id: int | None = None
    category_id: int | None = None
    category_name: str | None = None
    date_or_views: str | None = None
    added_date: str | None = None
    views: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class BookMetadata:
    tid: str
    title: str
    author: str | None
    format: str | None
    url: str
    mirror: str
    tuaid: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    raw_title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class LinkInfo:
    kind: str
    format: str | None
    url: str
    mirror: str
    content_type: str | None = None
    content_length: int | None = None
    is_direct_asset: bool = False
    restricted_by_site_ui: bool | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class ValidationResult:
    path: str
    ok: bool
    transfer_complete: bool | None
    file_type_valid: bool
    container_valid: bool
    content_readable: bool
    demo_suspected: bool | None
    content_completeness: str
    sha256: str | None = None
    size_bytes: int | None = None
    expected_size_bytes: int | None = None
    metadata_title: str | None = None
    metadata_creator: str | None = None
    manifest_items: int | None = None
    spine_items: int | None = None
    toc_items: int | None = None
    nav_items: int | None = None
    spine_text_chars_approx: int | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class DownloadPlan:
    selector: dict[str, str]
    book: BookMetadata
    format: str
    mirror: str
    asset: LinkInfo
    output_path: str
    partial_path: str
    dry_run: bool
    validation_checks: list[str]
    assets: list[LinkInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class DownloadResult:
    ok: bool
    plan: DownloadPlan
    path: str | None = None
    skipped: bool = False
    validation: ValidationResult | None = None
    manifest_path: str | None = None
    archive_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class DownloadQueueItem:
    selector: dict[str, str]
    format: str = "epub"
    out_dir: str | None = None
    index: int | None = None
    exact: bool = False
    filename_template: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class DownloadQueue:
    items: list[DownloadQueueItem]
    created_at: str
    version: int = 1
    source: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class DownloadArchiveRecord:
    timestamp: str
    ok: bool
    tid: str
    title: str
    author: str | None
    format: str
    url: str
    mirror: str
    output_path: str | None
    sha256: str | None
    size_bytes: int | None
    validation_ok: bool | None
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class ExternalValidationResult:
    name: str
    command: list[str]
    ok: bool
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class ResourceProfile:
    cpu_count: int
    memory_total_bytes: int | None
    suggested_download_jobs: int
    suggested_search_jobs: int
    suggested_request_interval_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class ErrorResult:
    ok: bool
    error: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _clean_dict(asdict(self))
