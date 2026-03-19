import re

from typer.testing import CliRunner

from opennebula_cli.cli.app import app

runner = CliRunner()
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


IMPLEMENTED_SUBCOMMANDS = [
    ("vm", "list"),
    ("vm", "show"),
    ("vm", "poweroff"),
    ("host", "list"),
    ("host", "show"),
    ("host", "flush"),
    ("image", "list"),
    ("image", "show"),
    ("image", "delete"),
    ("template", "list"),
    ("template", "show"),
    ("template", "delete"),
    ("template", "instantiate"),
    ("vnet", "list"),
    ("vnet", "show"),
    ("datastore", "list"),
    ("datastore", "show"),
    ("cluster", "list"),
    ("cluster", "show"),
]


def test_help_snapshots_cover_examples() -> None:
    for family, command in IMPLEMENTED_SUBCOMMANDS:
        result = runner.invoke(app, [family, command, "--help"])
        output = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
        assert result.exit_code == 0, f"{family} {command} should render help"
        assert "Examples:" in output
        assert f"one {family} {command}" in output
        assert f"one{family} {command}" in output
    poweroff_help = runner.invoke(app, ["vm", "poweroff", "--help"])
    poweroff_output = ANSI_ESCAPE_PATTERN.sub("", poweroff_help.stdout)
    assert "poll-interval" in poweroff_output
    assert "This command changes live resources." in poweroff_output
