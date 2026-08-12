"""Run sanitized, read-only compatibility checks against a named context."""

from __future__ import annotations

import argparse
import json

from opennebula_cli.config.loader import resolve_runtime_config
from opennebula_cli.config.models import ResolvedConfig
from opennebula_cli.sdk.client import OneClient


def _config(context: str) -> ResolvedConfig:
    return resolve_runtime_config(
        profile_name=None,
        context_name=context,
        require_context=context,
        endpoint=None,
        auth=None,
        user=None,
        password=None,
        output="json",
        no_pager=True,
        timeout=15.0,
        no_verify=False,
        cert_dir=None,
        verbose=0,
        debug=False,
    )


def _check_family(
    client: OneClient,
    family: str,
    *,
    full_fields: tuple[str, ...] = (),
) -> dict[str, object]:
    service = getattr(client, family)
    items = service.list()
    result: dict[str, object] = {"count": len(items), "list": "pass", "show": "empty"}
    if items:
        identifier = items[0].id
        service.show(identifier)
        result["show"] = "pass"
        if full_fields and hasattr(service, "show_full"):
            full = service.show_full(identifier)
            result["full_fields"] = {field: field in full for field in full_fields}
    return result


def validate(context: str) -> dict[str, object]:
    config = _config(context)
    summary: dict[str, object] = {
        "context": context,
        "mutation_policy": config.mutation_policy,
        "backends": {},
    }
    backends = summary["backends"]
    assert isinstance(backends, dict)
    for backend in ("auto", "raw"):
        client = OneClient.from_config(config, backend=backend)
        info = client.server_info()
        checks: dict[str, object] = {
            "server_version": info.version,
            "profile": info.profile,
            "transport": info.transport,
        }
        families: tuple[tuple[str, tuple[str, ...]], ...] = (
            ("vm", ("STATE", "LCM_STATE", "TEMPLATE", "USER_TEMPLATE")),
            ("host", ("STATE", "HOST_SHARE", "TEMPLATE")),
            ("image", ("STATE", "DATASTORE_ID", "TEMPLATE")),
            ("template", ("TEMPLATE",)),
            ("vnet", ("AR_POOL", "TEMPLATE")),
            ("datastore", ("TOTAL_MB", "FREE_MB", "USED_MB", "TEMPLATE")),
            ("cluster", ("HOSTS", "DATASTORES", "VNETS")),
        )
        for family, fields in families:
            checks[family] = _check_family(client, family, full_fields=fields)
        checks["acl"] = {"count": len(client.acl.list()), "list": "pass"}
        backends[backend] = checks

    rest_checks: dict[str, object] = {}
    try:
        flow_records = OneClient.from_config(config).flow.run_official("list", [])
        flow_roles = [role for record in flow_records for role in getattr(record, "roles", [])]
        rest_checks["oneflow"] = {
            "count": len(flow_records),
            "list": "pass",
            "service_state_pairs": all(
                getattr(record, "state", None) is not None
                and getattr(record, "state_id", None) is not None
                for record in flow_records
            ),
            "role_state_pairs": all(
                getattr(role, "state", None) is not None
                and getattr(role, "state_id", None) is not None
                for role in flow_roles
            ),
        }
    except Exception as exc:
        rest_checks["oneflow"] = {"list": "unavailable", "error_type": type(exc).__name__}
    if "oneform" in config.connection.service_endpoints:
        try:
            rest_checks["oneform"] = {
                "count": len(OneClient.from_config(config).form.list()),
                "list": "pass",
            }
        except Exception as exc:
            rest_checks["oneform"] = {
                "list": "unavailable",
                "error_type": type(exc).__name__,
            }
    else:
        rest_checks["oneform"] = {"list": "not_configured"}
    summary["rest"] = rest_checks
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.context), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
