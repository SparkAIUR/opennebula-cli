"""Public OneClient entrypoint."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from opennebula_cli.config.loader import resolve_runtime_config
from opennebula_cli.config.models import ResolvedConfig
from opennebula_cli.registry.profiles import profile_for_version
from opennebula_cli.sdk.exceptions import ConnectionError, UnsupportedCapabilityError
from opennebula_cli.sdk.models.system import CapabilityProfile, ServerInfo
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
    OneFormService,
    OneGateService,
    PlaceholderFamilyService,
    PreviewTemplateService,
    ProviderService,
    ProvisionService,
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
from opennebula_cli.transports.policy import PolicyTransport
from opennebula_cli.transports.pyone_adapter import PyoneTransport
from opennebula_cli.transports.routing import RoutingTransport
from opennebula_cli.transports.xmlrpc_raw import RawXmlRpcTransport


def build_transport(config: ResolvedConfig, *, backend: str = "auto") -> OpenNebulaTransport:
    """Construct the selected transport backend."""

    raw = RawXmlRpcTransport(
        endpoint=config.connection.endpoint,
        session=config.auth.raw_session,
        timeout=config.connection.timeout,
        verify_ssl=config.connection.verify_ssl,
        cert_dir=config.connection.cert_dir,
    )
    selected: OpenNebulaTransport
    if backend == "raw":
        selected = raw
    else:
        pyone = PyoneTransport(
            endpoint=config.connection.endpoint,
            session=config.auth.raw_session,
            timeout=config.connection.timeout,
            verify_ssl=config.connection.verify_ssl,
            cert_dir=config.connection.cert_dir,
        )
        if backend == "pyone":
            selected = pyone
        elif backend == "auto":
            selected = RoutingTransport(pyone, raw)
        else:
            raise ConnectionError(f"Unknown transport backend: {backend}")
    if config.mutation_policy == "deny":
        return PolicyTransport(selected, context=config.context_name)
    return selected


@dataclass(slots=True)
class OneClient:
    """Public typed OpenNebula SDK client."""

    config: ResolvedConfig
    transport: OpenNebulaTransport
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
    form: OneFormService
    provider: ProviderService
    provider_template: PreviewTemplateService
    provision: ProvisionService
    provision_template: PreviewTemplateService
    _server_info: ServerInfo | None = None

    @classmethod
    def from_config(cls, config: ResolvedConfig, *, backend: str = "auto") -> OneClient:
        """Build a client from a fully resolved configuration object."""

        transport = build_transport(config, backend=backend)
        return cls(
            config=config,
            transport=transport,
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
            form=OneFormService(config),
            provider=ProviderService(config),
            provider_template=PreviewTemplateService(config, "provider-template"),
            provision=ProvisionService(config),
            provision_template=PreviewTemplateService(config, "provision-template"),
        )

    @staticmethod
    def _safe_endpoint(endpoint: str) -> str:
        parsed = urlsplit(endpoint)
        host = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))

    def server_info(self, *, refresh: bool = False) -> ServerInfo:
        """Authenticate, detect the server line, and return sanitized identity."""

        if self._server_info is not None and not refresh:
            return self._server_info
        version_raw = self.transport.call("one.system.version")
        version = str(version_raw).strip()
        profile = profile_for_version(version)
        transport = getattr(self.transport, "last_backend", None) or self.transport.name
        self._server_info = ServerInfo(
            version=version,
            profile=profile.name,
            endpoint=self._safe_endpoint(self.config.connection.endpoint),
            username=self.config.auth.username,
            transport=transport,
        )
        return self._server_info

    def capabilities(self, *, refresh: bool = False) -> CapabilityProfile:
        """Return the authenticated effective compatibility profile."""

        info = self.server_info(refresh=refresh)
        return profile_for_version(info.version)

    def require_capability(self, capability: str) -> CapabilityProfile:
        """Fail before an operation call when the server profile lacks a feature."""

        profile = self.capabilities()
        if not profile.supports(capability):
            raise UnsupportedCapabilityError(
                f"{capability} is not available for OpenNebula {profile.server_version}.",
                method=capability if capability.startswith("one.") else None,
            )
        return profile

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
