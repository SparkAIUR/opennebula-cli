from __future__ import annotations

import csv
import io
import json
from xml.etree import ElementTree

import pytest
import yaml
from rich.console import Console

from opennebula_cli.renderers import render_output
from opennebula_cli.renderers.base import RenderContext
from opennebula_cli.renderers.selection import transform_output
from opennebula_cli.sdk.exceptions import PolicyError
from opennebula_cli.transports.policy import PolicyTransport


@pytest.mark.parametrize(
    "resource", ["vm", "host", "image", "template", "vnet", "datastore", "cluster"]
)
@pytest.mark.parametrize("output", ["json", "jsonl", "yaml", "xml", "csv", "raw"])
def test_machine_output_is_parser_clean_for_every_typed_read_family(
    resource: str, output: str
) -> None:
    stream = io.StringIO()
    data = [{"id": 7, "name": f"e2e-{resource}", "state": "READY", "state_id": 2}]
    render_output(
        data,
        ctx=RenderContext(
            console=Console(file=stream, force_terminal=False, color_system=None),
            output=output,
            interactive=False,
            no_pager=True,
            resource=resource,
        ),
    )
    payload = stream.getvalue()
    assert "\x1b[" not in payload
    if output == "json":
        assert json.loads(payload) == data
    elif output == "jsonl":
        assert [json.loads(line) for line in payload.splitlines()] == data
    elif output == "yaml":
        assert yaml.safe_load(payload) == data
    elif output == "xml":
        assert ElementTree.fromstring(payload).tag == resource
    elif output == "csv":
        assert list(csv.DictReader(io.StringIO(payload)))[0]["name"] == f"e2e-{resource}"
    else:
        assert json.loads(payload) == data


def test_official_xml_schema_repeats_upstream_vector_names_without_item_nodes() -> None:
    stream = io.StringIO()
    render_output(
        {"TEMPLATE": {"DISK": [{"DISK_ID": "0"}, {"DISK_ID": "1"}]}},
        ctx=RenderContext(
            console=Console(file=stream, force_terminal=False, color_system=None),
            output="xml",
            interactive=False,
            no_pager=True,
            resource="VM",
            official_schema=True,
        ),
    )

    assert "<item>" not in stream.getvalue()
    assert len(ElementTree.fromstring(stream.getvalue()).findall("./TEMPLATE/DISK")) == 2


def test_selection_filter_sort_select_and_value_share_one_path_grammar() -> None:
    data = [
        {"id": 2, "template": {"CONTEXT": {"TOKEN": "beta"}}},
        {"id": 1, "template": {"CONTEXT": {"TOKEN": "alpha"}}},
    ]
    assert transform_output(
        data,
        value_path=None,
        select_fields="id,template.CONTEXT.TOKEN",
        filter_expression="template.context.token=alpha",
        sort_field="id",
    ) == [{"id": 1, "template.CONTEXT.TOKEN": "alpha"}]
    assert (
        transform_output(
            data[0],
            value_path="template.context.token",
            select_fields=None,
            filter_expression=None,
            sort_field=None,
        )
        == "beta"
    )


class RecordingTransport:
    name = "recording"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def supports(self, method: str) -> bool:
        return True

    def call(self, method: str, *args: object) -> object:
        self.calls.append(method)
        return "7.4.0"


def test_context_policy_denies_mutation_before_transport_contact() -> None:
    backend = RecordingTransport()
    transport = PolicyTransport(backend, context="dr")

    assert transport.call("one.system.version") == "7.4.0"
    with pytest.raises(PolicyError):
        transport.call("one.vm.delete", 7)

    assert backend.calls == ["one.system.version"]
