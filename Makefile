.PHONY: help venv install dev-install docs-install build test lint format docs docs-clean clean dist

VENV_PATH ?= ~/.vnthuquan

help:
	@echo "Available targets:"
	@echo "  venv          Create virtual environment at $(VENV_PATH)"
	@echo "  install       Install package into the active environment"
	@echo "  dev-install   Create venv and install dev/docs/test dependencies"
	@echo "  docs-install  Install documentation dependencies"
	@echo "  build         Build the Python package"
	@echo "  test          Run tests"
	@echo "  lint          Run ruff checks"
	@echo "  format        Format with ruff"
	@echo "  docs          Build Sphinx HTML docs"
	@echo "  clean         Remove build artifacts"
	@echo "  dist          Clean and build distribution artifacts"

venv:
	python -m venv $(VENV_PATH)

install:
	pip install -e .

dev-install:
	bash scripts/dev_install.sh

docs-install:
	pip install -r docs/requirements.txt

build:
	python -m build

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

docs:
	sphinx-build -b html docs/source docs/_build/html

docs-clean:
	rm -rf docs/_build

clean:
	bash scripts/clean.sh

dist: clean build
	@echo "Package built successfully"
