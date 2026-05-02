"""Public OneClient entrypoint."""

from __future__ import annotations

from dataclasses import dataclass

from opennebula_cli.config.loader import resolve_runtime_config
from opennebula_cli.config.models import ResolvedConfig
from opennebula_cli.services import (
    AclService,
    ClusterService,
    DatastoreService,
    DbService,
    GroupService,
    HostService,
    ImageService,
    MarketappService,
    OneFlowService,
    OneGateService,
    PlaceholderFamilyService,
    RawService,
    TemplateService,
    UserService,
    VdcService,
    VmgroupService,
    VmService,
    VnetService,
    VntemplateService,
    VrouterService,
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
    """Public typed OpenNebula SDK client."""

    config: ResolvedConfig
    cluster: ClusterService
    datastore: DatastoreService
    vnet: VnetService
    vm: VmService
    host: HostService
    image: ImageService
    template: TemplateService
    user: UserService
    group: GroupService
    acl: AclService
    flow: OneFlowService
    gate: OneGateService
    marketapp: MarketappService
    db: DbService
    vdc: VdcService
    vrouter: VrouterService
    vmgroup: VmgroupService
    vntemplate: VntemplateService
    zone: PlaceholderFamilyService
    hook: PlaceholderFamilyService
    market: PlaceholderFamilyService
    secgroup: PlaceholderFamilyService
    cfg: PlaceholderFamilyService
    log: PlaceholderFamilyService
    swap: PlaceholderFamilyService
    showback: PlaceholderFamilyService
    acct: PlaceholderFamilyService
    gather: PlaceholderFamilyService
    raw: RawService

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
            user=UserService(transport),
            group=GroupService(transport),
            acl=AclService(transport),
            flow=OneFlowService(config),
            gate=OneGateService(transport),
            marketapp=MarketappService(transport),
            db=DbService(),
            vdc=VdcService(transport),
            vrouter=VrouterService(transport),
            vmgroup=VmgroupService(transport),
            vntemplate=VntemplateService(transport),
            zone=PlaceholderFamilyService("zone", transport),
            hook=PlaceholderFamilyService("hook", transport),
            market=PlaceholderFamilyService("market", transport),
            secgroup=PlaceholderFamilyService("secgroup", transport),
            cfg=PlaceholderFamilyService("cfg", transport),
            log=PlaceholderFamilyService("log", transport),
            swap=PlaceholderFamilyService("swap", transport),
            showback=PlaceholderFamilyService("showback", transport),
            acct=PlaceholderFamilyService("acct", transport),
            gather=PlaceholderFamilyService("gather", transport),
            raw=RawService(transport),
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
