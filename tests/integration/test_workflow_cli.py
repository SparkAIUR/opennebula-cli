from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from opennebula_cli.cli.app import app

runner = CliRunner()


def test_workflow_template_init_writes_files(tmp_path: Path) -> None:
    target = tmp_path / "wf"

    result = runner.invoke(app, ["workflow", "template", "init", str(target)])

    assert result.exit_code == 0
    assert (target / "workflow.yaml").exists()
    assert (target / "vm-template.one.j2").exists()
    assert (target / "cloud-init.yaml.j2").exists()
    assert (target / "vars.example.yaml").exists()


def test_workflow_template_render_prints_template(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    template = tmp_path / "vm-template.one.j2"
    cloud_init = tmp_path / "cloud-init.yaml.j2"
    vars_file = tmp_path / "vars.yaml"

    workflow.write_text(
        """version: 1
kind: workflow-template
template:
  source: vm-template.one.j2
cloud_init:
  source: cloud-init.yaml.j2
required:
  - template_name
  - image_name
""",
        encoding="utf-8",
    )
    template.write_text(
        """NAME = "{{ template_name }}"
DISK = [ IMAGE = "{{ image_name }}" ]
CONTEXT = [ USER_DATA = "{{ cloud_init_user_data_escaped }}" ]
""",
        encoding="utf-8",
    )
    cloud_init.write_text("#cloud-config\nruncmd:\n  - echo hello\n", encoding="utf-8")
    vars_file.write_text("image_name: ubuntu-cloud\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "workflow",
            "template",
            "render",
            str(workflow),
            "--vars-file",
            str(vars_file),
            "--var",
            "template_name=workflow-test",
        ],
    )

    assert result.exit_code == 0
    assert 'NAME = "workflow-test"' in result.stdout
    assert 'DISK = [ IMAGE = "ubuntu-cloud" ]' in result.stdout
    assert 'USER_DATA = "#cloud-config\\nruncmd:\\n  - echo hello\\n"' in result.stdout
