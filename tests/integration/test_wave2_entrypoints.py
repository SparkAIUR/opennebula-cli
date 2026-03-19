import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_compat(module: str, binary: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    argv = [binary, "--help"]
    script = (
        "import sys\n"
        f"from {module} import main\n"
        f"sys.argv = {argv!r}\n"
        "main()\n"
    )
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
