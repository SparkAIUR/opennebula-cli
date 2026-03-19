from typer.testing import CliRunner

from opennebula_cli.cli.app import app

runner = CliRunner()


def test_onevm_snapshot() -> None:
    result = runner.invoke(app, ["vm", "poweroff", "--help"])
    assert result.exit_code == 0
    assert "--poll-interval" in result.stdout
