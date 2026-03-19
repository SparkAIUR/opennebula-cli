from opennebula_cli.cli.help_examples import command_epilog


def test_command_epilog_includes_examples() -> None:
    epilog = command_epilog("vm", "list", "--output json")
    assert epilog == "Examples:\n  one --output json vm list\n  onevm --output json list"


def test_command_epilog_moves_global_options_ahead_of_show_command() -> None:
    epilog = command_epilog("vnet", "show", "11 --output yaml")
    assert "one --output yaml vnet show 11" in epilog
    assert "onevnet --output yaml show 11" in epilog


def test_command_epilog_includes_caution() -> None:
    epilog = command_epilog("image", "delete", "18", caution="This command changes live resources.")
    assert epilog.startswith("This command changes live resources.\n\nExamples:")
    assert "one image delete 18" in epilog
    assert "oneimage delete 18" in epilog
