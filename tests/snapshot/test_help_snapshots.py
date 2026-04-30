import re

from typer.testing import CliRunner

from opennebula_cli.cli.app import app

runner = CliRunner()
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


IMPLEMENTED_SUBCOMMANDS = [
    (("vm", "list"), True),
    (("vm", "show"), True),
    (("vm", "disk-list"), True),
    (("vm", "disk-attach"), True),
    (("vm", "disk-detach"), True),
    (("vm", "recover"), True),
    (("vm", "reboot"), True),
    (("vm", "reboot-hard"), True),
    (("vm", "resume"), True),
    (("vm", "wait"), True),
    (("vm", "poweroff"), True),
    (("vm", "poweroff-hard"), True),
    (("host", "list"), True),
    (("host", "show"), True),
    (("host", "flush"), True),
    (("image", "list"), True),
    (("image", "show"), True),
    (("image", "owner"), True),
    (("image", "delete"), True),
    (("template", "list"), True),
    (("template", "show"), True),
    (("template", "delete"), True),
    (("template", "instantiate"), True),
    (("vnet", "list"), True),
    (("vnet", "show"), True),
    (("datastore", "list"), True),
    (("datastore", "show"), True),
    (("cluster", "list"), True),
    (("cluster", "show"), True),
    (("workflow", "template", "init"), False),
    (("workflow", "template", "render"), False),
    (("workflow", "template", "import"), False),
    (("workflow", "template", "apply"), False),
    (("workflow", "vm", "init"), False),
    (("workflow", "vm", "apply"), False),
    (("raw", "call"), False),
]


def test_help_snapshots_cover_examples() -> None:
    for command_parts, expect_compat in IMPLEMENTED_SUBCOMMANDS:
        result = runner.invoke(app, [*command_parts, "--help"])
        output = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
        command_label = " ".join(command_parts)
        assert result.exit_code == 0, f"{command_label} should render help"
        assert "Examples:" in output
        assert f"one {command_label}" in output or "one --output" in output
        if expect_compat:
            family = command_parts[0]
            command = command_parts[1]
            assert f"one{family} {command}" in output or f"one{family} --output" in output
        else:
            assert "oneworkflow " not in output
    poweroff_help = runner.invoke(app, ["vm", "poweroff", "--help"])
    poweroff_output = ANSI_ESCAPE_PATTERN.sub("", poweroff_help.stdout)
    assert "poll-interval" in poweroff_output
    assert "This command changes live resources." in poweroff_output
