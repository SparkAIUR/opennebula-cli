"""Validate that a release tag matches the package version exactly."""

from __future__ import annotations

import argparse
import os
import sys
import tomllib
from pathlib import Path


def project_version(pyproject_path: Path) -> str:
    """Return the PEP 621 project version from pyproject.toml."""

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError("Missing [project] table in pyproject.toml.")
    version = project.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("Missing project.version in pyproject.toml.")
    return version


def normalize_tag(value: str) -> str:
    """Normalize a tag ref or tag name to the short tag form."""

    for prefix in ("refs/tags/", "refs/", "tags/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def expected_tag(version: str) -> str:
    """Return the required tag for the supplied project version."""

    return f"v{version}"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        default=os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_REF", ""),
        help="Release tag name or Git ref. Defaults to GITHUB_REF_NAME/GITHUB_REF.",
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml.",
    )
    return parser.parse_args()


def main() -> int:
    """Validate the release tag against project.version."""

    args = parse_args()
    if not args.tag:
        print("No release tag provided via --tag or GitHub environment.", file=sys.stderr)
        return 2

    tag = normalize_tag(args.tag)
    version = project_version(args.pyproject)
    required = expected_tag(version)

    if tag != required:
        print(
            f"Release tag mismatch: expected {required}, received {tag}.",
            file=sys.stderr,
        )
        return 1

    print(f"Validated release tag {tag} for project version {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
