from opennebula_cli.sdk.models.common import normalize_value


class _RecursiveNode:
    def __init__(self) -> None:
        self.parent_object_ = self
        self.ns_prefix_ = None
        self.VALUE = "kept"
        self.COUNT = 3


def test_normalize_value_drops_generated_metadata_cycle() -> None:
    normalized = normalize_value(_RecursiveNode())

    assert normalized == {
        "VALUE": "kept",
        "COUNT": 3,
    }
