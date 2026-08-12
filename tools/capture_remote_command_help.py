#!/usr/bin/env python3
"""Capture `<command> --help` output from a remote OpenNebula frontend.

Reads command names from `refs/notes/list-of-commands.md` and writes
captured output to `refs/notes/list-of-command-output.md`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shlex
import subprocess
from pathlib import Path

DEFAULT_COMMANDS_FILE = Path("refs/notes/list-of-commands.md")
DEFAULT_OUTPUT_FILE = Path("refs/notes/list-of-command-output.md")


def parse_commands(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")

    # Prefer fenced block content when present.
    fenced = re.findall(r"```(?:[\w-]+)?\n(.*?)```", text, flags=re.S)
    lines: list[str] = []
    if fenced:
        for block in fenced:
            lines.extend(block.splitlines())
    else:
        lines = text.splitlines()

    commands: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Keep a conservative token parser: first whitespace-delimited token.
        command = line.split()[0]
        if command:
            commands.append(command)
    return commands


def _trim_before_synopsis(output: str) -> str:
    """Drop banner/noise lines before the first `## SYNOPSIS` section."""

    lines = output.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "## SYNOPSIS":
            return "\n".join(lines[index:]).strip()
    return output.strip()


def run_remote_help(host: str, command: str, ssh_bin: str = "ssh") -> tuple[int, str]:
    quoted = shlex.quote(command)
    remote_script = (
        "set -o pipefail; "
        f"if command -v {quoted} >/dev/null 2>&1; then "
        f"  {quoted} --help 2>&1; "
        "  echo '__JCODE_EXIT__'$?; "
        "else "
        f"  echo 'command not found: {command}'; "
        "  echo '__JCODE_EXIT__127'; "
        "fi"
    )

    proc = subprocess.run(
        [ssh_bin, host, "bash", "-lc", remote_script],
        capture_output=True,
        text=True,
    )

    combined = proc.stdout
    if proc.stderr:
        combined = f"{combined}\n[ssh-stderr]\n{proc.stderr}" if combined else proc.stderr

    match = re.search(r"\n?__JCODE_EXIT__(\d+)\s*$", combined)
    if match:
        exit_code = int(match.group(1))
        output = re.sub(r"\n?__JCODE_EXIT__\d+\s*$", "", combined, flags=re.S).rstrip()
        return exit_code, _trim_before_synopsis(output)

    # SSH-level failure (no marker produced).
    return proc.returncode, _trim_before_synopsis(combined.rstrip())


def render_markdown(host: str, commands_file: Path, rows: list[tuple[str, int, str]]) -> str:
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Command Help Output Capture",
        "",
        f"- Host: `{host}`",
        f"- Commands source: `{commands_file}`",
        f"- Captured at (UTC): `{now}`",
        "",
    ]

    for command, exit_code, output in rows:
        lines.append(f"## {command}")
        lines.append("")
        lines.append(f"Exit code: `{exit_code}`")
        lines.append("")
        lines.append("```bash")
        lines.append(f"$ {command} --help")
        lines.append(output if output else "(no output)")
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="SSH host target, e.g. root@REMOTE-HOST")
    parser.add_argument(
        "--commands-file",
        type=Path,
        default=DEFAULT_COMMANDS_FILE,
        help=f"Path to commands markdown (default: {DEFAULT_COMMANDS_FILE})",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Path to output markdown (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument("--ssh-bin", default="ssh", help="SSH binary to use (default: ssh)")

    args = parser.parse_args()

    commands = parse_commands(args.commands_file)
    if not commands:
        raise SystemExit(f"No commands found in {args.commands_file}")

    rows: list[tuple[str, int, str]] = []
    for command in commands:
        code, output = run_remote_help(args.host, command, ssh_bin=args.ssh_bin)
        rows.append((command, code, output))
        print(f"captured: {command} (exit={code})")

    content = render_markdown(args.host, args.commands_file, rows)
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(content, encoding="utf-8")
    print(f"wrote: {args.output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
