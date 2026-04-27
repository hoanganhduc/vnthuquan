"""Sphinx configuration for vnthuquan."""

from __future__ import annotations

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath("../.."))

project = "vnthuquan"
author = "Duc A. Hoang"
current_year = datetime.now().year
current_date = datetime.now().strftime("%Y-%m-%d")
copyright = f"2026-{current_year}, {author}"
release = "0.1.0"
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_autodoc_typehints",
]
autosectionlabel_prefix_document = True

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
]

templates_path = ["_templates"]
exclude_patterns: list[str] = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = []
rst_epilog = f".. |last_updated| replace:: {current_date}"

autodoc_typehints = "description"
autodoc_member_order = "bysource"
