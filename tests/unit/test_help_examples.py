from opennebula_cli.cli.help_examples import command_epilog


def test_command_epilog_includes_examples() -> None:
    epilog = command_epilog("vm", "list", "--output json")
    assert epilog == "Examples:\n  one vm list --output json\n  onevm list --output json"


def test_command_epilog_includes_caution() -> None:
    epilog = command_epilog("image", "delete", "18", caution="This command changes live resources.")
    assert epilog.startswith("This command changes live resources.\n\nExamples:")
    assert "one image delete 18" in epilog
    assert "oneimage delete 18" in epilog
