from typer.testing import CliRunner

from opennebula_cli.cli.app import app

runner = CliRunner()


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
        assert result.exit_code == 0, f"{family} {command} should render help"
        assert "Examples:" in result.stdout
        assert f"one {family} {command}" in result.stdout
        assert f"one{family} {command}" in result.stdout
    poweroff_help = runner.invoke(app, ["vm", "poweroff", "--help"])
    assert "--poll-interval" in poweroff_help.stdout
    assert "This command changes live resources." in poweroff_help.stdout
