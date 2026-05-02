from __future__ import annotations

from pathlib import Path

from tools.check_command_coverage import coverage_report


def test_captured_official_commands_are_registered() -> None:
    missing, extra = coverage_report(Path("refs/notes/list-of-command-output.md"))

    assert missing == {family: set() for family in missing}
    assert extra == {family: set() for family in extra}
