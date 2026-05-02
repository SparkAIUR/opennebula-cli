from opennebula_cli import __version__


def test_version_available() -> None:
    assert __version__ == "7.0.2"
