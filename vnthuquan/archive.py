"""Persistent download archive."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import Config, default_archive_path
from .errors import FilesystemError
from .models import DownloadArchiveRecord, DownloadResult
from .validators import sha256_file


def resolve_archive_path(path: str | Path | None, config: Config) -> Path:
    value = path or config.archive_path
    return Path(value).expanduser() if value else default_archive_path()


def record_from_result(result: DownloadResult) -> DownloadArchiveRecord:
    validation = result.validation
    plan = result.plan
    size_bytes = validation.size_bytes if validation else None
    sha256 = validation.sha256 if validation else None
    if result.path and (size_bytes is None or sha256 is None):
        path = Path(result.path)
        if path.exists():
            size_bytes = path.stat().st_size
            sha256 = sha256 or sha256_file(path)
    return DownloadArchiveRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        ok=result.ok,
        tid=plan.book.tid,
        title=plan.book.title,
        author=plan.book.author,
        format=plan.format,
        url=plan.book.url,
        mirror=plan.mirror,
        output_path=result.path,
        sha256=sha256,
        size_bytes=size_bytes,
        validation_ok=validation.ok if validation else None,
        skipped=result.skipped,
    )


class DownloadArchive:
    """JSONL archive of executed download results."""

    def __init__(self, path: str | Path | None = None, config: Config | None = None) -> None:
        self.path = (
            Path(path).expanduser() if path else resolve_archive_path(None, config or Config())
        )

    def append(self, record: DownloadArchiveRecord) -> Path:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except OSError as exc:
            raise FilesystemError(f"Could not write archive {self.path}: {exc}") from exc
        return self.path

    def read(self, limit: int | None = None) -> list[DownloadArchiveRecord]:
        if not self.path.exists():
            return []
        records: list[DownloadArchiveRecord] = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                raw = json.loads(line)
                records.append(DownloadArchiveRecord(**raw))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise FilesystemError(f"Could not read archive {self.path}: {exc}") from exc
        return records[-limit:] if limit else records


def write_archive_snapshot(records: Iterable[DownloadArchiveRecord], path: str | Path) -> Path:
    archive_path = Path(path).expanduser()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(archive_path.parent),
        delete=False,
    ) as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        temp_name = handle.name
    os.replace(temp_name, archive_path)
    return archive_path
