import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def run_compat(module: str, binary: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    argv = [binary, "--help"]
    script = f"import sys\nfrom {module} import main\nsys.argv = {argv!r}\nmain()\n"
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        cwd=ROOT,
        env=env,
        text=True,
    )


def test_compat_help_entrypoints() -> None:
    for module, binary, expected in (
        ("opennebula_cli.compat.onevnet", "onevnet", "Manage virtual networks"),
        ("opennebula_cli.compat.onedatastore", "onedatastore", "Manage datastores"),
        ("opennebula_cli.compat.onecluster", "onecluster", "Manage clusters"),
    ):
        result = run_compat(module, binary)
        assert result.returncode == 0
        assert expected in result.stdout


def test_compat_entrypoint_accepts_leading_global_output_option() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    script = (
        "import sys\n"
        "from opennebula_cli.compat.onevnet import main\n"
        "sys.argv = ['onevnet', '--output', 'json', 'list', '--help']\n"
        "main()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        cwd=ROOT,
        env=env,
        text=True,
    )
    assert result.returncode == 0
    output = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "onevnet --output json list" in output
