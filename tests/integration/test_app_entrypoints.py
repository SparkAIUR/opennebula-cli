from pathlib import Path

from typer.testing import CliRunner

from opennebula_cli.cli.app import app
from opennebula_cli.cli.resources.raw import _load_args

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


def test_raw_group_help() -> None:
    result = runner.invoke(app, ["raw", "--help"])
    assert result.exit_code == 0
    assert "Run guarded raw XML-RPC calls" in result.stdout

    call_result = runner.invoke(app, ["raw", "call", "--help"])
    assert call_result.exit_code == 0
    assert "i-understand-this-is-unsafe" in call_result.stdout


def test_agents_command_prints_markdown_guide() -> None:
    result = runner.invoke(app, ["agents"])
    assert result.exit_code == 0
    assert "# opennebula-cli Agent Guide" in result.stdout
    assert "opennebula vm" in result.stdout


def test_version_command_prints_app_version_and_git_hash() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "opennebula-cli version:" in result.stdout
    assert "opennebula-cli git hash:" in result.stdout


def test_recover_requires_exactly_one_action_flag() -> None:
    missing = runner.invoke(app, ["vm", "recover", "42"])
    assert missing.exit_code != 0
    assert "Select exactly one" in missing.output

    multiple = runner.invoke(app, ["vm", "recover", "42", "--success", "--retry"])
    assert multiple.exit_code != 0
    assert "Select exactly one" in multiple.output


def test_raw_call_requires_unsafe_flag_before_config_resolution() -> None:
    result = runner.invoke(app, ["raw", "call", "one.vm.info", "--json-args-text", "[42]"])
    assert result.exit_code != 0
    assert "i-understand-this-is-unsafe" in result.output


def test_vm_wait_rejects_invalid_duration_before_config_resolution() -> None:
    result = runner.invoke(app, ["vm", "wait", "42", "--state", "ACTIVE", "--timeout", "nope"])
    assert result.exit_code != 0
    assert "Duration must be seconds" in result.output


def test_raw_args_loader_accepts_file_and_inline_json(tmp_path: Path) -> None:
    args_file = tmp_path / "args.json"
    args_file.write_text('[42, {"extended": true}]', encoding="utf-8")

    assert _load_args(args_file, None) == [42, {"extended": True}]
    assert _load_args(None, '[43, {"full": true}]') == [43, {"full": True}]
