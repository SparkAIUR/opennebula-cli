from __future__ import annotations

from typing import Any

from opennebula_cli.sdk.models.cluster import Cluster
from opennebula_cli.sdk.models.datastore import Datastore
from opennebula_cli.sdk.models.vnet import Vnet
from opennebula_cli.services.cluster import ClusterService
from opennebula_cli.services.datastore import DatastoreService
from opennebula_cli.services.vnet import VnetService


class StubTransport:
    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def call(self, method: str, *args: object) -> Any:
        self.calls.append((method, args))
        return self._responses[method]


def test_vnet_service_list_and_show() -> None:
    transport = StubTransport(
        {
            "one.vnpool.info": {
                "VNET": [
                    {
                        "ID": "10",
                        "NAME": "public",
                        "VN_MAD": "bridge",
                        "CLUSTER_ID": "1",
                        "TEMPLATE": {"BRIDGE": "br0"},
                        "AR_POOL": {"AR": {"IP": "10.0.0.5"}},
                    }
                ]
            },
            "one.vn.info": {
                "ID": "10",
                "NAME": "public",
                "VN_MAD": "bridge",
                "CLUSTER_ID": "1",
                "TEMPLATE": {"BRIDGE": "br0"},
            },
        }
    )
    service = VnetService(transport)

    items = service.list()
    detail = service.show(10)

    assert items == [
        Vnet(
            id=10,
            name="public",
            type="bridge",
            bridge="br0",
            cluster_id=1,
            template={"BRIDGE": "br0"},
            reservations=[{"IP": "10.0.0.5"}],
        )
    ]
    assert detail.id == 10
    assert transport.calls == [
        ("one.vnpool.info", (-2, -1, -1)),
        ("one.vn.info", (10, False)),
    ]


def test_datastore_service_list_and_show() -> None:
    transport = StubTransport(
        {
            "one.datastorepool.info": {
                "DATASTORE": {
                    "ID": "3",
                    "NAME": "default",
                    "STATE": "2",
                    "TYPE_STR": "IMAGE_DS",
                    "CLUSTER_ID": "0",
                    "TEMPLATE": {"DS_MAD": "fs", "TM_MAD": "qcow2"},
                }
            },
            "one.datastore.info": {
                "ID": "3",
                "NAME": "default",
                "STATE_STR": "READY",
                "TYPE_STR": "IMAGE_DS",
                "CLUSTER_ID": "0",
                "TEMPLATE": {"DS_MAD": "fs", "TM_MAD": "qcow2"},
            },
        }
    )
    service = DatastoreService(transport)

    items = service.list()
    detail = service.show(3)

    assert items[0] == Datastore(
        id=3,
        name="default",
        state="UNKNOWN_2",
        state_id=2,
        type="IMAGE_DS",
        cluster_id=0,
        ds_mad="fs",
        tm_mad="qcow2",
        template={"DS_MAD": "fs", "TM_MAD": "qcow2"},
    )
    assert detail.state == "READY"


def test_cluster_service_list_and_show() -> None:
    transport = StubTransport(
        {
            "one.clusterpool.info": {
                "CLUSTER": [{"ID": "0", "NAME": "default", "HOSTS": {"ID": ["1", "2"]}}]
            },
            "one.cluster.info": {
                "ID": "0",
                "NAME": "default",
                "HOSTS": {"ID": ["1", "2"]},
                "DATASTORES": {"ID": "3"},
                "VNETS": {"ID": ["4"]},
                "TEMPLATE": {"LABEL": "core"},
            },
        }
    )
    service = ClusterService(transport)

    items = service.list()
    detail = service.show(0)

    assert items == [
        Cluster(id=0, name="default", hosts=[1, 2], datastores=[], vnets=[], template={})
    ]
    assert detail == Cluster(
        id=0,
        name="default",
        hosts=[1, 2],
        datastores=[3],
        vnets=[4],
        template={"LABEL": "core"},
    )
