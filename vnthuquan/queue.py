"""Download queue manifest helpers."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ConfigError, FilesystemError
from .models import DownloadQueue, DownloadQueueItem


def make_queue(
    items: list[DownloadQueueItem],
    source: dict[str, Any] | None = None,
) -> DownloadQueue:
    return DownloadQueue(
        items=items,
        source=source or {},
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def write_queue(queue: DownloadQueue, path: str | Path) -> Path:
    queue_path = Path(path).expanduser()
    try:
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(queue_path.parent),
            delete=False,
        ) as handle:
            json.dump(queue.to_dict(), handle, ensure_ascii=False, indent=2)
            temp_name = handle.name
        os.replace(temp_name, queue_path)
    except OSError as exc:
        raise FilesystemError(f"Could not write queue manifest {queue_path}: {exc}") from exc
    return queue_path


def read_queue(path: str | Path) -> DownloadQueue:
    queue_path = Path(path).expanduser()
    try:
        raw = json.loads(queue_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FilesystemError(f"Could not read queue manifest {queue_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid queue manifest {queue_path}: {exc}") from exc

    items_raw = raw.get("items")
    if not isinstance(items_raw, list):
        raise ConfigError("Queue manifest must contain an items list")
    items = []
    for idx, item in enumerate(items_raw):
        if not isinstance(item, dict):
            raise ConfigError(f"Queue item {idx} must be an object")
        selector = item.get("selector")
        if not isinstance(selector, dict) or not selector:
            raise ConfigError(f"Queue item {idx} must contain a selector")
        items.append(
            DownloadQueueItem(
                selector={str(key): str(value) for key, value in selector.items() if value},
                format=str(item.get("format") or "epub"),
                out_dir=item.get("out_dir"),
                index=item.get("index"),
                exact=bool(item.get("exact", False)),
                filename_template=item.get("filename_template"),
            )
        )

    return DownloadQueue(
        version=int(raw.get("version", 1)),
        created_at=str(raw.get("created_at") or ""),
        source=raw.get("source") if isinstance(raw.get("source"), dict) else {},
        items=items,
    )
