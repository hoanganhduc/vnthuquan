"""Local resource detection and conservative parallelism recommendations."""

from __future__ import annotations

import os

from .models import ResourceProfile


def _memory_total_bytes() -> int | None:
    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if isinstance(pages, int) and isinstance(page_size, int):
                return pages * page_size
        except (OSError, ValueError):
            return None
    return None


def detect_resources() -> ResourceProfile:
    cpu_count = os.cpu_count() or 1
    memory_total = _memory_total_bytes()
    memory_limited_jobs = 2
    if memory_total is not None:
        gib = memory_total / (1024**3)
        if gib >= 16:
            memory_limited_jobs = 4
        elif gib >= 8:
            memory_limited_jobs = 3
    suggested_download_jobs = max(1, min(4, cpu_count // 2 or 1, memory_limited_jobs))
    suggested_search_jobs = max(1, min(6, cpu_count, memory_limited_jobs + 2))
    request_interval = 0.2 if suggested_download_jobs <= 2 else 0.4
    return ResourceProfile(
        cpu_count=cpu_count,
        memory_total_bytes=memory_total,
        suggested_download_jobs=suggested_download_jobs,
        suggested_search_jobs=suggested_search_jobs,
        suggested_request_interval_seconds=request_interval,
    )


def resolve_jobs(value: str | int | None, default: int = 1) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return max(value, 1)
    if str(value).casefold().strip() == "auto":
        return detect_resources().suggested_download_jobs
    return max(int(value), 1)
