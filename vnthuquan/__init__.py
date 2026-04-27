"""Python wrapper and CLI for Vietnam Thu Quan ebook discovery."""

from __future__ import annotations

from .client import VnThuQuanClient

__version__ = "0.1.0"
__author__ = "Duc A. Hoang (hoanganhduc)"
__email__ = "anhduc.hoang1990@gmail.com"
__description__ = "Python wrapper and CLI for Vietnam Thu Quan ebook discovery and EPUB downloads"


def get_version() -> str:
    """Return the package version."""

    return __version__


def get_package_info() -> dict[str, str]:
    """Return package metadata for CLI and diagnostics."""

    return {
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": __description__,
    }


def main() -> int:
    """Console script entry point."""

    from .cli import main as cli_main

    return cli_main()


__all__ = [
    "VnThuQuanClient",
    "__author__",
    "__description__",
    "__email__",
    "__version__",
    "get_package_info",
    "get_version",
    "main",
]
