#!/usr/bin/env bash
set -euo pipefail

rm -rf build dist *.egg-info docs/_build .pytest_cache
find . -type d -name __pycache__ -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
