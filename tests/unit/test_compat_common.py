from __future__ import annotations

from opennebula_cli.compat.common import _split_compat_argv


def test_split_compat_argv_moves_leading_global_options() -> None:
    global_args, remainder = _split_compat_argv(["--output", "json", "list"])

    assert global_args == ["--output", "json"]
    assert remainder == ["list"]


def test_split_compat_argv_keeps_command_help_in_remainder() -> None:
    global_args, remainder = _split_compat_argv(["list", "--help"])

    assert global_args == []
    assert remainder == ["list", "--help"]


def test_split_compat_argv_supports_equals_form() -> None:
    global_args, remainder = _split_compat_argv(["--endpoint=http://127.0.0.1:2633/RPC2", "list"])

    assert global_args == ["--endpoint=http://127.0.0.1:2633/RPC2"]
    assert remainder == ["list"]
