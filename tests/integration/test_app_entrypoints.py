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


def test_workflow_group_help() -> None:
    result = runner.invoke(app, ["workflow", "--help"])
    assert result.exit_code == 0
    assert "Manage workflow automation commands" in result.stdout

    template_result = runner.invoke(app, ["workflow", "template", "--help"])
    assert template_result.exit_code == 0
    assert "Render and import workflow VM templates" in template_result.stdout

    vm_result = runner.invoke(app, ["workflow", "vm", "--help"])
    assert vm_result.exit_code == 0
    assert "Initialize VMs from workflow definitions" in vm_result.stdout
