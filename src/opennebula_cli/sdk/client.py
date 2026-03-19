"""Public OneClient entrypoint."""

from __future__ import annotations

from dataclasses import dataclass

from opennebula_cli.config.loader import resolve_runtime_config
from opennebula_cli.config.models import ResolvedConfig
from opennebula_cli.services import (
    ClusterService,
    DatastoreService,
    HostService,
    ImageService,
    TemplateService,
    VmService,
    VnetService,
)
from opennebula_cli.transports.base import OpenNebulaTransport
from opennebula_cli.transports.pyone_adapter import PyoneTransport
from opennebula_cli.transports.xmlrpc_raw import RawXmlRpcTransport


def build_transport(config: ResolvedConfig, *, backend: str = "pyone") -> OpenNebulaTransport:
    """Construct the selected transport backend."""

    if backend == "raw":
        return RawXmlRpcTransport(
            endpoint=config.connection.endpoint,
            session=config.auth.raw_session,
            timeout=config.connection.timeout,
            verify_ssl=config.connection.verify_ssl,
            cert_dir=config.connection.cert_dir,
        )
    return PyoneTransport(
        endpoint=config.connection.endpoint,
        session=config.auth.raw_session,
        timeout=config.connection.timeout,
        verify_ssl=config.connection.verify_ssl,
        cert_dir=config.connection.cert_dir,
    )


@dataclass(slots=True)
class OneClient:
    """Public typed OpenNebula SDK client.

    Example:
        >>> client = OneClient.from_env()
        >>> client.vm.list()
        [...]
    """

    config: ResolvedConfig
    cluster: ClusterService
    datastore: DatastoreService
    vnet: VnetService
    vm: VmService
    host: HostService
    image: ImageService
    template: TemplateService

    @classmethod
    def from_config(cls, config: ResolvedConfig, *, backend: str = "pyone") -> OneClient:
        """Build a client from a fully resolved configuration object."""

        transport = build_transport(config, backend=backend)
        return cls(
            config=config,
            cluster=ClusterService(transport),
            datastore=DatastoreService(transport),
            vnet=VnetService(transport),
            vm=VmService(transport),
            host=HostService(transport),
            image=ImageService(transport),
            template=TemplateService(transport),
        )

    @classmethod
    def from_env(cls) -> OneClient:
        return cls.from_config(
            resolve_runtime_config(
                profile_name=None,
                endpoint=None,
                auth=None,
                user=None,
                password=None,
                output="table",
                no_pager=False,
                timeout=None,
                no_verify=False,
                cert_dir=None,
                verbose=0,
                debug=False,
            )
        )

    @classmethod
    def from_profile(cls, name: str) -> OneClient:
        return cls.from_config(
            resolve_runtime_config(
                profile_name=name,
                endpoint=None,
                auth=None,
                user=None,
                password=None,
                output="table",
                no_pager=False,
                timeout=None,
                no_verify=False,
                cert_dir=None,
                verbose=0,
                debug=False,
            )
        )
