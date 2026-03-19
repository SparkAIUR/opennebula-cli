from typer.testing import CliRunner

from opennebula_cli.cli.app import app

runner = CliRunner()


def test_template_help() -> None:
    result = runner.invoke(app, ["template", "--help"])
    assert result.exit_code == 0
    assert "Manage VM templates" in result.stdout


def test_wave2_group_help() -> None:
    for family, expected in (
        ("vnet", "Manage virtual networks"),
        ("datastore", "Manage datastores"),
        ("cluster", "Manage clusters"),
    ):
        result = runner.invoke(app, [family, "--help"])
        assert result.exit_code == 0
        assert expected in result.stdout
