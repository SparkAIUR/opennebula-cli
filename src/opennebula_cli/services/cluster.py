"""Cluster service."""

from __future__ import annotations

import builtins
from typing import Any

from opennebula_cli.sdk.models.cluster import Cluster
from opennebula_cli.sdk.models.common import Ack, ensure_list, normalize_mapping, object_get
from opennebula_cli.services.official import run_official_command
from opennebula_cli.transports.base import OpenNebulaTransport


class ClusterService:
    """Typed OpenNebula cluster operations.

    Example:
        >>> service = ClusterService(transport)
        >>> service.list()
        [Cluster(id=0, name='default', ...)]
    """

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self) -> list[Cluster]:
        raw = self._transport.call("one.clusterpool.info")
        items = ensure_list(object_get(raw, "CLUSTER"))
        return [Cluster.from_raw(item) for item in items]

    def show(self, cluster_id: int) -> Cluster:
        raw = self._transport.call("one.cluster.info", cluster_id)
        return Cluster.from_raw(raw)

    def show_full(self, cluster_id: int) -> dict[str, Any]:
        return normalize_mapping(self._transport.call("one.cluster.info", cluster_id))

    def optimize(self, cluster_id: int) -> Ack:
        self._transport.call("one.cluster.optimize", cluster_id)
        return Ack(resource="cluster", id=cluster_id, action="optimize")

    def plan_execute(self, cluster_id: int) -> Ack:
        self._transport.call("one.cluster.planexecute", cluster_id)
        return Ack(resource="cluster", id=cluster_id, action="planexecute")

    def plan_delete(self, cluster_id: int) -> Ack:
        self._transport.call("one.cluster.plandelete", cluster_id)
        return Ack(resource="cluster", id=cluster_id, action="plandelete")

    def run_official(self, verb: str, argv: builtins.list[str]) -> object:
        """Run a captured official cluster command not yet modeled by a typed method."""

        return run_official_command(self._transport, "cluster", verb, argv)
