"""Check captured OpenNebula 7.0.2 commands against the Typer CLI tree."""

from __future__ import annotations

import re
from pathlib import Path

import click

from opennebula_cli.cli.app import app

RESOURCE_FAMILIES = {
    "onevm": "vm",
    "onehost": "host",
    "oneimage": "image",
    "onetemplate": "template",
    "onevnet": "vnet",
    "onedatastore": "datastore",
    "onecluster": "cluster",
    "oneflow-template": "flow-template",
}
CUSTOM_COMMANDS = {
    "vm": {"disk-list", "wait", "poweroff-hard", "reboot-hard"},
    "image": {"owner"},
}
ARGUMENT_PLACEHOLDERS = {
    "ar_id",
    "clusterid",
    "clusterid_list",
    "datastoreid",
    "datastoreid_list",
    "disk_snapshot_id",
    "diskid",
    "file",
    "filterflag",
    "groupid",
    "hostid",
    "hostid_list",
    "imageid",
    "imageid_list",
    "mac",
    "nicid",
    "pciid",
    "range",
    "sched_id",
    "sgid",
    "size",
    "snapshot_id",
    "templateid",
    "templateid_list",
    "text",
    "type",
    "userid",
    "vnetid",
    "vnetid_list",
    "vmid",
    "vmid_list",
}


def captured_commands(path: Path) -> dict[str, set[str]]:
    """Parse `## COMMANDS` blocks from the captured official help notes."""

    text = path.read_text(encoding="utf-8")
    result: dict[str, set[str]] = {}
    for script, family in RESOURCE_FAMILIES.items():
        section_match = re.search(rf"### {script}\n(?P<body>.*?)(?=\n### |\Z)", text, re.S)
        if section_match is None:
            raise RuntimeError(f"Missing section for {script}")
        body = section_match.group("body")
        commands_match = re.search(
            r"## COMMANDS\n(?P<body>.*?)(?=\n## OPTIONS|\Z)",
            body,
            re.S,
        )
        if commands_match is None:
            raise RuntimeError(f"Missing command block for {script}")
        commands = {
            match.group(1)
            for match in re.finditer(
                r"^\s+\*\s+([a-z0-9][a-z0-9-]*)\b",
                commands_match.group("body"),
                re.M,
            )
            if match.group(1) not in ARGUMENT_PLACEHOLDERS
        }
        result[family] = commands
    return result


def implemented_commands() -> dict[str, set[str]]:
    """Inspect top-level resource subcommands from the Typer/Click app."""

    click_app = typer_to_click()
    result: dict[str, set[str]] = {}
    for family in RESOURCE_FAMILIES.values():
        command = click_app.commands.get(family)
        if not isinstance(command, click.Group):
            raise RuntimeError(f"Missing CLI group for {family}")
        result[family] = set(command.commands)
    return result


def typer_to_click() -> click.Group:
    command = typer_main_command()
    if not isinstance(command, click.Group):
        raise RuntimeError("Root Typer app did not produce a Click group")
    return command


def typer_main_command() -> click.Command:
    from typer.main import get_command

    return get_command(app)


def coverage_report(notes_path: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    expected = captured_commands(notes_path)
    actual = implemented_commands()
    missing: dict[str, set[str]] = {}
    extra: dict[str, set[str]] = {}
    for family, commands in expected.items():
        extras_allowed = CUSTOM_COMMANDS.get(family, set())
        missing[family] = commands - actual.get(family, set())
        extra[family] = actual.get(family, set()) - commands - extras_allowed
    return missing, extra


def main() -> None:
    notes_path = Path("refs/notes/full-commands-7.0.2.md")
    missing, extra = coverage_report(notes_path)
    has_gap = False
    for family in sorted(missing):
        if missing[family]:
            has_gap = True
            print(f"{family}: missing {sorted(missing[family])}")
        if extra[family]:
            print(f"{family}: extra non-official {sorted(extra[family])}")
    if has_gap:
        raise SystemExit(1)
    print("Command coverage matches captured OpenNebula 7.0.2 commands.")


if __name__ == "__main__":
    main()
