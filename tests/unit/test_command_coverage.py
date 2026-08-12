from __future__ import annotations

from tools.check_command_coverage import coverage_report


def test_shipped_official_commands_are_registered() -> None:
    for profile in ("7.0", "7.4"):
        missing, extra = coverage_report(profile)

        assert missing == {family: set() for family in missing}
        assert extra == {family: set() for family in extra}
