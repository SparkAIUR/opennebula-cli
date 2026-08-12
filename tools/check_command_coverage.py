"""Check captured OpenNebula command coverage against the Typer CLI tree."""

from __future__ import annotations

import re
from pathlib import Path

import click

from opennebula_cli.cli.app import app
from opennebula_cli.registry.profiles import ProfileName, commands_for_profile

RESOURCE_FAMILIES = {
    "onevm": "vm",
    "onehost": "host",
    "oneimage": "image",
    "onetemplate": "template",
    "onevnet": "vnet",
    "onedatastore": "datastore",
    "onecluster": "cluster",
    "oneflow": "flow",
    "oneflow-template": "flow-template",
    "onegate": "gate",
    "oneuser": "user",
    "onegroup": "group",
    "oneacl": "acl",
    "onemarketapp": "marketapp",
    "onedb": "db",
    "onevdc": "vdc",
    "onevrouter": "vrouter",
    "onevmgroup": "vmgroup",
    "onevntemplate": "vntemplate",
    "onezone": "zone",
    "onehook": "hook",
    "onemarket": "market",
    "onesecgroup": "secgroup",
    "onecfg": "cfg",
    "onelog": "log",
    "oneswap": "swap",
    "oneshowback": "showback",
    "oneacct": "acct",
    "onegather": "gather",
    "oneform": "form",
    "oneprovider": "provider",
    "oneprovider-template": "provider-template",
    "oneprovision": "provision",
    "oneprovision-template": "provision-template",
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
    "password",
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
    "userid_list",
    "vnetid",
    "vnetid_list",
    "vmid",
    "vmid_list",
}


def captured_commands(path: Path) -> dict[str, set[str]]:
    """Parse command blocks from captured help output markdown."""

    text = path.read_text(encoding="utf-8")
    result: dict[str, set[str]] = {}
    for script, family in RESOURCE_FAMILIES.items():
        section_match = re.search(
            rf"^## {re.escape(script)}\n(?P<body>.*?)(?=^## one[a-z0-9-]+\n|\Z)",
            text,
            re.S | re.M,
        )
        if section_match is None:
            raise RuntimeError(f"Missing section for {script}")
        body = section_match.group("body")
        commands_match = re.search(
            r"^## COMMANDS\n(?P<body>.*?)(?=^## ARGUMENT FORMATS\n|^## VERSION\n|\Z)",
            body,
            re.S | re.M,
        )
        if commands_match is None:
            result[family] = set()
            continue
        command_body = commands_match.group("body")
        if script == "onegate":
            result[family] = _parse_onegate_commands(command_body)
            continue
        commands = {
            match.group(1)
            for match in re.finditer(
                r"^\s+\*\s+([a-z0-9][a-z0-9-]*)\b",
                command_body,
                re.M,
            )
            if match.group(1) not in ARGUMENT_PLACEHOLDERS and match.group(1) != script
        }
        result[family] = commands
    return result


def _parse_onegate_commands(command_body: str) -> set[str]:
    commands: set[str] = set()
    for line in command_body.splitlines():
        match = re.match(r"^\s*\*\s+onegate\s+(.+)$", line.strip())
        if not match:
            continue
        suffix = match.group(1).strip()
        if suffix.startswith("vm show"):
            commands.add("vm-show")
        elif suffix.startswith("vm update"):
            commands.add("vm-update")
        elif suffix.startswith("service show"):
            commands.add("service-show")
        elif suffix.startswith("service scale"):
            commands.add("service-scale")
        elif suffix.startswith("vrouter show"):
            commands.add("vrouter-show")
        elif suffix.startswith("vnet show"):
            commands.add("vnet-show")
        else:
            token = suffix.split()[0]
            if token in {
                "resume",
                "stop",
                "suspend",
                "terminate",
                "reboot",
                "poweroff",
                "resched",
                "unresched",
                "hold",
                "release",
            }:
                commands.add(token)
    return commands


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


def coverage_report(
    profile: ProfileName = "7.4",
    *,
    capture_path: Path | None = None,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Compare the installed CLI union with a shipped server-line profile.

    A private capture can be supplied explicitly for maintainer delta review, but
    normal CI and package installs never depend on ``refs/``.
    """

    expected = commands_for_profile(profile)
    if capture_path is not None:
        captured = captured_commands(capture_path)
        capture_delta = {
            family: expected.get(family, set()) ^ commands for family, commands in captured.items()
        }
        if any(capture_delta.values()):
            details = "; ".join(
                f"{family}={sorted(delta)}"
                for family, delta in sorted(capture_delta.items())
                if delta
            )
            raise RuntimeError(f"Capture differs from shipped {profile} profile: {details}")
    actual = implemented_commands()
    other_profile: ProfileName = "7.0" if profile == "7.4" else "7.4"
    other_commands = commands_for_profile(other_profile)
    missing: dict[str, set[str]] = {}
    extra: dict[str, set[str]] = {}
    for family, commands in expected.items():
        extras_allowed = CUSTOM_COMMANDS.get(family, set()) | other_commands.get(family, set())
        missing[family] = commands - actual.get(family, set())
        extra[family] = actual.get(family, set()) - commands - extras_allowed
    return missing, extra


def main() -> None:
    has_gap = False
    for profile in ("7.0", "7.4"):
        missing, extra = coverage_report(profile)
        for family in sorted(missing):
            if missing[family]:
                has_gap = True
                print(f"{profile} {family}: missing {sorted(missing[family])}")
            if extra[family]:
                has_gap = True
                print(f"{profile} {family}: extra non-official {sorted(extra[family])}")
    if has_gap:
        raise SystemExit(1)
    print("Command coverage matches shipped OpenNebula 7.0 and 7.4 profiles.")


if __name__ == "__main__":
    main()
