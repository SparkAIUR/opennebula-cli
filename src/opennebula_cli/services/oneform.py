"""Typed OpenNebula 7.4 OneForm, provider, and provision services."""

from __future__ import annotations

import os
from collections.abc import Mapping
from urllib.parse import quote

from opennebula_cli.config.models import ResolvedConfig
from opennebula_cli.sdk.exceptions import PolicyError, UnsupportedCapabilityError
from opennebula_cli.sdk.models.common import Ack, ensure_list
from opennebula_cli.sdk.models.oneform import PROVISION_STATES, OneFormDocument
from opennebula_cli.transports.rest import JsonRestTransport


class _OneFormBase:
    def __init__(self, config: ResolvedConfig) -> None:
        self._config = config
        self._rest_transport: JsonRestTransport | None = None

    @property
    def _rest(self) -> JsonRestTransport:
        if self._rest_transport is not None:
            return self._rest_transport
        config = self._config
        endpoint = config.connection.service_endpoints.get("oneform")
        if not endpoint:
            raise UnsupportedCapabilityError(
                "OneForm requires an explicit endpoint in the selected context or ONEFORM_URL."
            )
        versioned = endpoint.rstrip("/")
        if not versioned.endswith("/api/v1"):
            versioned += "/api/v1"
        self._rest_transport = JsonRestTransport(
            base_url=versioned,
            username=os.getenv("ONEFORM_USER", config.auth.username),
            password=os.getenv("ONEFORM_PASSWORD", config.auth.secret),
            timeout=config.connection.timeout,
            verify_ssl=config.connection.verify_ssl,
            cert_dir=config.connection.cert_dir,
        )
        return self._rest_transport

    def _mutation(self) -> None:
        if self._config.mutation_policy == "deny":
            raise PolicyError(
                f"Context '{self._config.context_name or '<none>'}' denies mutating operations."
            )


class OneFormService(_OneFormBase):
    def list(self, *, enabled: bool = False) -> list[OneFormDocument]:
        raw = self._rest.request("GET", "drivers", query={"enabled": str(enabled).lower()})
        return [OneFormDocument.from_raw(item) for item in ensure_list(raw)]

    def show(self, name: str) -> OneFormDocument:
        return OneFormDocument.from_raw(
            self._rest.request("GET", f"drivers/{quote(name, safe='')}")
        )

    def sync(self) -> Ack:
        self._mutation()
        self._rest.request("POST", "drivers/sync", body={})
        return Ack(resource="form", id=-1, action="sync")

    def enable(self, name: str, *, enabled: bool) -> Ack:
        self._mutation()
        action = "enable" if enabled else "disable"
        self._rest.request("POST", f"drivers/{quote(name, safe='')}/{action}", body={})
        return Ack(resource="form", id=-1, action=action, message=name)


class ProviderService(_OneFormBase):
    def list(self, *, enabled: bool = False, sensitive: bool = False) -> list[OneFormDocument]:
        raw = self._rest.request(
            "GET", "providers", query={"enabled": enabled, "include_sensitive": sensitive}
        )
        return [OneFormDocument.from_raw(item) for item in ensure_list(raw)]

    def show(self, provider_id: int, *, sensitive: bool = False) -> OneFormDocument:
        raw = self._rest.request(
            "GET", f"providers/{provider_id}", query={"include_sensitive": sensitive}
        )
        return OneFormDocument.from_raw(raw)

    def create(self, driver: str, values: Mapping[str, object]) -> OneFormDocument:
        self._mutation()
        return OneFormDocument.from_raw(
            self._rest.request("POST", "providers", body={"driver": driver, **values})
        )

    def update(self, provider_id: int, values: Mapping[str, object]) -> OneFormDocument:
        self._mutation()
        return OneFormDocument.from_raw(
            self._rest.request("PATCH", f"providers/{provider_id}", body=values)
        )

    def action(self, provider_id: int, action: str, body: Mapping[str, object]) -> Ack:
        self._mutation()
        if action == "delete":
            self._rest.request("DELETE", f"providers/{provider_id}")
        else:
            self._rest.request("POST", f"providers/{provider_id}/{action}", body=body)
        return Ack(resource="provider", id=provider_id, action=action)


class ProvisionService(_OneFormBase):
    @staticmethod
    def _document(value: object) -> OneFormDocument:
        return OneFormDocument.from_raw(value, state_labels=PROVISION_STATES)

    def list(self) -> list[OneFormDocument]:
        return [
            self._document(item) for item in ensure_list(self._rest.request("GET", "provisions"))
        ]

    def show(self, provision_id: int, *, sensitive: bool = False) -> OneFormDocument:
        raw = self._rest.request(
            "GET", f"provisions/{provision_id}", query={"include_sensitive": sensitive}
        )
        return self._document(raw)

    def create(self, values: Mapping[str, object]) -> OneFormDocument:
        self._mutation()
        return self._document(self._rest.request("POST", "provisions", body=values))

    def update(self, provision_id: int, values: Mapping[str, object]) -> OneFormDocument:
        self._mutation()
        return self._document(
            self._rest.request("PATCH", f"provisions/{provision_id}", body=values)
        )

    def action(
        self, provision_id: int, action: str, body: Mapping[str, object] | None = None
    ) -> Ack:
        self._mutation()
        if action == "delete":
            self._rest.request("DELETE", f"provisions/{provision_id}", query=body)
        else:
            self._rest.request("POST", f"provisions/{provision_id}/{action}", body=body or {})
        return Ack(resource="provision", id=provision_id, action=action)

    def logs(self, provision_id: int, *, all_logs: bool = False) -> object:
        return self._rest.request(
            "GET", f"provisions/{provision_id}/logs/poll", query={"all": all_logs}
        )


class PreviewTemplateService(_OneFormBase):
    """Guard the two 7.4 wrappers whose stock server routes are absent."""

    def __init__(self, config: ResolvedConfig, family: str) -> None:
        super().__init__(config)
        self._family = family
        self._route = (
            "provider-templates" if family == "provider-template" else "provision-templates"
        )

    def _guard(self) -> None:
        enabled = os.getenv("OPENNEBULA_CLI_ENABLE_ONEFORM_PREVIEW", "").lower()
        if enabled not in {"1", "true", "yes", "on"}:
            raise UnsupportedCapabilityError(
                f"{self._family} is a guarded preview because stock OpenNebula 7.4 "
                "ships its wrapper without matching OneForm routes."
            )

    def list(self) -> list[OneFormDocument]:
        self._guard()
        return [
            OneFormDocument.from_raw(item)
            for item in ensure_list(self._rest.request("GET", self._route))
        ]

    def show(self, template_id: int) -> OneFormDocument:
        self._guard()
        return OneFormDocument.from_raw(self._rest.request("GET", f"{self._route}/{template_id}"))

    def instantiate(self, template_id: int, values: Mapping[str, object]) -> OneFormDocument:
        self._guard()
        self._mutation()
        return OneFormDocument.from_raw(
            self._rest.request("POST", f"{self._route}/{template_id}/instantiate", body=values)
        )
