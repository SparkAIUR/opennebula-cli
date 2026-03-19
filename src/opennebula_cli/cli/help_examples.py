"""Shared helpers for stable CLI help examples."""

from __future__ import annotations


def command_epilog(
    family: str,
    command: str,
    *examples: str,
    caution: str | None = None,
) -> str:
    """Build a stable help epilog with canonical and compat examples.

    Example:
        >>> command_epilog("vm", "list", "--output json")
        'Examples:\\n  one vm list --output json\\n  onevm list --output json'
    """

    lines: list[str] = []
    if caution:
        lines.append(caution)
        lines.append("")
    lines.append("Examples:")
    for suffix in examples:
        normalized_suffix = suffix.strip()
        canonical = f"one {family} {command}".strip()
        compat = f"one{family} {command}".strip()
        if normalized_suffix:
            canonical = f"{canonical} {normalized_suffix}"
            compat = f"{compat} {normalized_suffix}"
        lines.append(f"  {canonical}")
        lines.append(f"  {compat}")
    return "\n".join(lines)
