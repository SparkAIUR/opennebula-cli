set shell := ["bash", "-cu"]

default:
    @just --list

sync:
    uv sync --group dev

lint:
    uv run ruff check src tests

lint-fix:
    uv run ruff check src tests --fix

typecheck:
    uv run mypy src tests tools

test:
    uv run pytest

snapshot:
    uv run pytest tests/snapshot/test_help_snapshots.py

catalog:
    uv run python tools/check_catalog_schema.py

release-preflight tag="v7.0.2":
    uv run python tools/check_release_version.py --tag {{tag}}

check:
    just lint
    just typecheck
    just test
    just catalog

build:
    uv build
