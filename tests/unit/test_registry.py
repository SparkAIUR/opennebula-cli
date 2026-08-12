from pathlib import Path

from opennebula_cli.registry.catalog import load_catalogs


def test_load_catalogs() -> None:
    catalogs = load_catalogs(Path("src/opennebula_cli/catalogs/v7_0/base"))
    assert sorted(catalogs) == [
        "cluster",
        "datastore",
        "flow-template",
        "host",
        "image",
        "template",
        "vm",
        "vnet",
    ]
