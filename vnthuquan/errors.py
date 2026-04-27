"""Typed errors used by the vnthuquan client and CLI."""

from __future__ import annotations


class VnThuQuanError(Exception):
    """Base package error."""

    exit_code = 1


class LiveCheckError(VnThuQuanError):
    """Raised when a mirror liveness check fails."""

    exit_code = 5


class MirrorUnavailableError(VnThuQuanError):
    """Raised when no usable mirror is available."""

    exit_code = 5


class SearchError(VnThuQuanError):
    """Raised when a search request or parse fails."""

    exit_code = 1


class AmbiguousResultError(VnThuQuanError):
    """Raised when a selector matches multiple books."""

    exit_code = 4


class NotFoundError(VnThuQuanError):
    """Raised when a requested book, asset, or category cannot be found."""

    exit_code = 3


class ParseError(VnThuQuanError):
    """Raised when expected site markup is missing or malformed."""

    exit_code = 1


class AssetDiscoveryError(VnThuQuanError):
    """Raised when an asset URL cannot be discovered."""

    exit_code = 1


class DownloadError(VnThuQuanError):
    """Raised when a file download fails."""

    exit_code = 6


class ValidationError(VnThuQuanError):
    """Raised when file validation fails."""

    exit_code = 7


class FilesystemError(VnThuQuanError):
    """Raised for local path or write errors."""

    exit_code = 8


class ConfigError(VnThuQuanError):
    """Raised for invalid configuration."""

    exit_code = 9


class UnsupportedFormatError(VnThuQuanError):
    """Raised when a requested format is not supported."""

    exit_code = 2
