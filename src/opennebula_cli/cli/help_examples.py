"""Shared helpers for stable CLI help examples."""

from __future__ import annotations

import re

GLOBAL_EXAMPLE_OPTION_PATTERNS = (
    re.compile(r"--output\s+\S+"),
    re.compile(r"--no-pager\b"),
)


def _extract_global_options(example: str) -> tuple[str, str]:
    """Move known global CLI options out of inline example suffixes."""

    remainder = example.strip()
    extracted: list[str] = []
    for pattern in GLOBAL_EXAMPLE_OPTION_PATTERNS:
        while match := pattern.search(remainder):
            extracted.append(match.group(0))
            remainder = " ".join(
                (remainder[: match.start()] + " " + remainder[match.end() :]).split()
            )
    return " ".join(extracted), remainder


def command_epilog(
    family: str,
    command: str,
    *examples: str,
    caution: str | None = None,
) -> str:
    """Build a stable help epilog with canonical and compat examples.

    Example:
        >>> command_epilog("vm", "list", "--output json")
        'Examples:\\n  one --output json vm list\\n  onevm --output json list'
    """

    lines: list[str] = []
    if caution:
        lines.append(caution)
        lines.append("")
    lines.append("Examples:")
    for suffix in examples:
        global_options, normalized_suffix = _extract_global_options(suffix)
        canonical_parts = ["one"]
        compat_parts = [f"one{family}"]
        if global_options:
            canonical_parts.append(global_options)
            compat_parts.append(global_options)
        canonical_parts.extend((family, command))
        compat_parts.append(command)
        if normalized_suffix:
            canonical_parts.append(normalized_suffix)
            compat_parts.append(normalized_suffix)
        lines.append(f"  {' '.join(canonical_parts)}")
        lines.append(f"  {' '.join(compat_parts)}")
    return "\n".join(lines)
