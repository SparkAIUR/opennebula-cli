from typer.testing import CliRunner

from opennebula_cli.cli.app import app

runner = CliRunner()


def test_template_help() -> None:
    result = runner.invoke(app, ["template", "--help"])
    assert result.exit_code == 0
    assert "Manage VM templates" in result.stdout
