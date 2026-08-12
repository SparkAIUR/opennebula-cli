"""Generic official CLI parity operations.

This module intentionally keeps the first full-coverage pass close to the
OpenNebula XML-RPC command surface. Resource-specific typed services can wrap
these operations later when a command needs richer SDK models.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from opennebula_cli.sdk.exceptions import ApiError, PartialFailureError
from opennebula_cli.sdk.models.common import Ack, ensure_list, normalize_value, object_get
from opennebula_cli.transports.base import OpenNebulaTransport

LOCK_LEVELS = {"use": 1, "manage": 2, "admin": 3, "all": 4}
HOST_STATUS = {"enable": 0, "disable": 1, "offline": 2}
RESOURCE_PREFIX = {
    "vm": "one.vm",
    "host": "one.host",
    "image": "one.image",
    "template": "one.template",
    "vnet": "one.vn",
    "datastore": "one.datastore",
    "cluster": "one.cluster",
    "user": "one.user",
    "group": "one.group",
    "acl": "one.acl",
}
POOL_METHOD = {
    "vm": "one.vmpool.infoextended",
    "host": "one.hostpool.info",
    "image": "one.imagepool.info",
    "template": "one.templatepool.info",
    "vnet": "one.vnpool.info",
    "datastore": "one.datastorepool.info",
    "cluster": "one.clusterpool.info",
    "user": "one.userpool.info",
    "group": "one.grouppool.info",
    "acl": "one.aclpool.info",
}
POOL_ITEM = {
    "vm": "VM",
    "host": "HOST",
    "image": "IMAGE",
    "template": "VMTEMPLATE",
    "vnet": "VNET",
    "datastore": "DATASTORE",
    "cluster": "CLUSTER",
    "user": "USER",
    "group": "GROUP",
    "acl": "ACL",
}


@dataclass(slots=True, frozen=True)
class ParsedArgs:
    """Small parser output for official-style argv forwarding."""

    positionals: list[str]
    options: dict[str, str]
    flags: set[str]


def parse_official_args(argv: list[str]) -> ParsedArgs:
    """Split loose compatibility tokens into positionals, options, and flags."""

    positionals: list[str] = []
    options: dict[str, str] = {}
    flags: set[str] = set()
    index = 0
    while index < len(argv):
        token = argv[index]
        if token.startswith("--"):
            name, separator, value = token[2:].partition("=")
            normalized = name.replace("-", "_")
            if separator:
                options[normalized] = value
            elif index + 1 < len(argv) and not argv[index + 1].startswith("-"):
                options[normalized] = argv[index + 1]
                index += 1
            else:
                flags.add(normalized)
            index += 1
            continue
        if token.startswith("-") and len(token) == 2:
            short_name = token[1:]
            if index + 1 < len(argv) and not argv[index + 1].startswith("-"):
                options[short_name] = argv[index + 1]
                index += 1
            else:
                flags.add(short_name)
            index += 1
            continue
        positionals.append(token)
        index += 1
    return ParsedArgs(positionals=positionals, options=options, flags=flags)


def parse_id_list(value: str) -> list[int]:
    """Parse OpenNebula range/list syntax such as `1,2,8..10`."""

    ids: list[int] = []
    for part in value.split(","):
        token = part.strip()
        if not token:
            continue
        if ".." in token:
            start_raw, end_raw = token.split("..", 1)
            start = int(start_raw)
            end = int(end_raw)
            if end < start:
                raise ApiError(f"Invalid descending range: {token}")
            ids.extend(range(start, end + 1))
            continue
        ids.append(int(token))
    if not ids:
        raise ApiError("At least one resource ID is required")
    return ids


def require_positionals(parsed: ParsedArgs, count: int, usage: str) -> list[str]:
    if len(parsed.positionals) < count:
        raise ApiError(f"Missing arguments. Usage: {usage}")
    return parsed.positionals


def quote_template_value(value: object) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def section(name: str, attrs: Sequence[tuple[str, object]]) -> str:
    body = ", ".join(f"{key} = {quote_template_value(value)}" for key, value in attrs)
    return f"{name} = [ {body} ]"


def read_template_file(path_raw: str) -> str:
    path = Path(path_raw).expanduser()
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ApiError(f"Unable to read template file {path}: {exc}") from exc


def template_from_args(parsed: ParsedArgs, *, default_name: str | None = None) -> str:
    """Build or load a simple OpenNebula template body from loose CLI inputs."""

    file_value = parsed.options.get("file") or parsed.options.get("f")
    if file_value:
        return read_template_file(file_value)
    for candidate in parsed.positionals:
        if Path(candidate).expanduser().is_file():
            return read_template_file(candidate)

    lines: list[str] = []
    name = parsed.options.get("name") or default_name
    if name:
        lines.append(f"NAME = {quote_template_value(name)}")
    for option_name, template_key in (
        ("memory", "MEMORY"),
        ("cpu", "CPU"),
        ("vcpu", "VCPU"),
        ("arch", "ARCH"),
        ("boot", "OS/BOOT"),
        ("type", "TYPE"),
        ("size", "SIZE"),
    ):
        if option_name in parsed.options:
            lines.append(f"{template_key} = {quote_template_value(parsed.options[option_name])}")
    for disk in _split_csv(parsed.options.get("disk")):
        attrs = [("IMAGE", disk)]
        if "target" in parsed.options:
            attrs.append(("TARGET", parsed.options["target"]))
        if "prefix" in parsed.options:
            attrs.append(("DEV_PREFIX", parsed.options["prefix"]))
        lines.append(section("DISK", attrs))
    networks = _split_csv(parsed.options.get("nic")) or _split_csv(parsed.options.get("network"))
    for network in networks:
        attrs = [("NETWORK", network)]
        if "ip" in parsed.options:
            attrs.append(("IP", parsed.options["ip"]))
        lines.append(section("NIC", attrs))
    if "raw" in parsed.options:
        lines.append(parsed.options["raw"])
    if not lines:
        raise ApiError("A template file or template-building options are required")
    return "\n".join(lines) + "\n"


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _ack(resource: str, resource_id: int, action: str) -> Ack:
    return Ack(resource=resource, id=resource_id, action=action)


def _call_first(
    transport: OpenNebulaTransport,
    methods: Sequence[str],
    *args: object,
) -> object:
    """Try multiple backend methods and return first successful result."""

    errors: list[str] = []
    for method in methods:
        try:
            return transport.call(method, *args)
        except ApiError as exc:
            errors.append(f"{method}: {exc}")
    joined = "; ".join(errors) or "no candidate methods"
    raise ApiError(f"No backend method succeeded: {joined}")


def _batch_action(
    transport: OpenNebulaTransport,
    *,
    family: str,
    ids: list[int],
    method: str,
    action: str,
    leading_args: tuple[object, ...] = (),
    trailing_args: tuple[object, ...] = (),
) -> list[Ack]:
    results: list[Ack] = []
    failures: list[dict[str, object]] = []
    for resource_id in ids:
        try:
            transport.call(method, *leading_args, resource_id, *trailing_args)
            results.append(_ack(family, resource_id, action))
        except Exception as exc:
            failures.append(
                {
                    "resource": family,
                    "id": resource_id,
                    "action": action,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
    if failures:
        raise PartialFailureError(
            f"{len(failures)} of {len(ids)} {family} {action} operations failed.",
            failures=failures,
            method=method,
        )
    return results


def _generic_admin(
    transport: OpenNebulaTransport,
    *,
    family: str,
    verb: str,
    parsed: ParsedArgs,
) -> object:
    prefix = RESOURCE_PREFIX[family]
    if verb in {"chgrp", "chmod", "chown"}:
        positionals = require_positionals(parsed, 2, f"{verb} <range|id_list> <value>")
        ids = parse_id_list(positionals[0])
        if verb == "chgrp":
            return _batch_action(
                transport,
                family=family,
                ids=ids,
                method=f"{prefix}.chown",
                action=verb,
                trailing_args=(-1, int(positionals[1])),
            )
        if verb == "chown":
            group_id = int(positionals[2]) if len(positionals) > 2 else -1
            return _batch_action(
                transport,
                family=family,
                ids=ids,
                method=f"{prefix}.chown",
                action=verb,
                trailing_args=(int(positionals[1]), group_id),
            )
        return _batch_action(
            transport,
            family=family,
            ids=ids,
            method=f"{prefix}.chmod",
            action=verb,
            trailing_args=(positionals[1],),
        )
    if verb == "rename":
        positionals = require_positionals(parsed, 2, "rename <id> <name>")
        resource_id = int(positionals[0])
        transport.call(f"{prefix}.rename", resource_id, positionals[1])
        return _ack(family, resource_id, verb)
    if verb in {"lock", "unlock", "delete"}:
        positionals = require_positionals(parsed, 1, f"{verb} <range|id_list>")
        ids = parse_id_list(positionals[0])
        if verb == "lock":
            level = _lock_level(parsed)
            return _batch_action(
                transport,
                family=family,
                ids=ids,
                method=f"{prefix}.lock",
                action=verb,
                trailing_args=(level,),
            )
        method = f"{prefix}.{verb}"
        trailing: tuple[object, ...] = (False,) if family == "template" and verb == "delete" else ()
        return _batch_action(
            transport,
            family=family,
            ids=ids,
            method=method,
            action=verb,
            trailing_args=trailing,
        )
    if verb == "update":
        positionals = require_positionals(parsed, 1, "update <id> [file]")
        resource_id = int(positionals[0])
        template_text = template_from_args(
            ParsedArgs(positionals=positionals[1:], options=parsed.options, flags=parsed.flags)
        )
        append = "append" in parsed.flags or parsed.options.get("append", "").lower() == "true"
        transport.call(f"{prefix}.update", resource_id, template_text, 1 if append else 0)
        return _ack(family, resource_id, verb)
    raise ApiError(f"Unsupported generic admin command: {family} {verb}")


def _lock_level(parsed: ParsedArgs) -> int:
    for name in ("admin", "manage", "use"):
        if name in parsed.flags:
            return LOCK_LEVELS[name]
    if "level" in parsed.options:
        return int(parsed.options["level"])
    return LOCK_LEVELS["all"]


def _pool_snapshot(transport: OpenNebulaTransport, family: str, parsed: ParsedArgs) -> object:
    filter_flag = int(parsed.positionals[0]) if parsed.positionals else -2
    method = POOL_METHOD[family]
    if family == "vm":
        return normalize_value(transport.call(method, filter_flag, -1, -1, -1))
    if family in {"image", "template", "vnet"}:
        return normalize_value(transport.call(method, filter_flag, -1, -1))
    return normalize_value(transport.call(method))


def _orphans(transport: OpenNebulaTransport, family: str) -> object:
    raw = _pool_snapshot(transport, family, ParsedArgs([], {}, set()))
    item_key = POOL_ITEM[family]
    items = ensure_list(object_get(raw, item_key))
    result: list[object] = []
    for item in items:
        vms = ensure_list(object_get(item, "VMS"))
        running = ensure_list(object_get(item, "RUNNING_VMS"))
        if not vms and not running:
            result.append(normalize_value(item))
    return result


def run_official_command(
    transport: OpenNebulaTransport,
    family: str,
    verb: str,
    argv: list[str],
) -> object:
    """Run a captured official command through XML-RPC-shaped operations."""

    parsed = parse_official_args(argv)
    if verb in {"top"}:
        return _pool_snapshot(transport, family, parsed)
    if verb in {"chgrp", "chmod", "chown", "rename", "lock", "unlock", "delete", "update"}:
        return _generic_admin(transport, family=family, verb=verb, parsed=parsed)
    if family == "vm":
        return _run_vm(transport, verb, parsed)
    if family == "host":
        return _run_host(transport, verb, parsed)
    if family == "image":
        return _run_image(transport, verb, parsed)
    if family == "template":
        return _run_template(transport, verb, parsed)
    if family == "vnet":
        return _run_vnet(transport, verb, parsed)
    if family == "datastore":
        return _run_datastore(transport, verb, parsed)
    if family == "cluster":
        return _run_cluster(transport, verb, parsed)
    if family == "user":
        return _run_user(transport, verb, parsed)
    if family == "group":
        return _run_group(transport, verb, parsed)
    if family == "acl":
        return _run_acl(transport, verb, parsed)
    raise ApiError(f"Unsupported command family: {family}")


def _vm_ids(parsed: ParsedArgs, usage: str) -> list[int]:
    return parse_id_list(require_positionals(parsed, 1, usage)[0])


def _run_vm(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["vm"]
    action_verbs = {
        "hold",
        "release",
        "resched",
        "unresched",
        "stop",
        "suspend",
        "terminate",
        "undeploy",
    }
    if verb in action_verbs:
        action = verb
        if verb in {"terminate", "undeploy"} and "hard" in parsed.flags:
            action = f"{verb}-hard"
        return _batch_action(
            transport,
            family="vm",
            ids=_vm_ids(parsed, f"{verb} <range|vmid_list>"),
            method=f"{prefix}.action",
            action=action,
            leading_args=(action,),
        )
    if verb == "create":
        template_text = template_from_args(parsed)
        hold = "hold" in parsed.flags
        vm_id = int(transport.call(f"{prefix}.allocate", template_text, hold))
        return _ack("vm", vm_id, verb)
    if verb in {"deploy", "migrate"}:
        positionals = require_positionals(
            parsed,
            2,
            f"{verb} <range|vmid_list> <hostid> [datastoreid]",
        )
        ids = parse_id_list(positionals[0])
        host_id = int(positionals[1])
        datastore_id = (
            int(positionals[2])
            if len(positionals) > 2
            else int(parsed.options.get("datastore", -1))
        )
        enforce = "enforce" in parsed.flags
        live = "live" in parsed.flags
        results: list[Ack] = []
        for vm_id in ids:
            if verb == "deploy":
                transport.call(f"{prefix}.deploy", vm_id, host_id, enforce, datastore_id)
            else:
                transport.call(f"{prefix}.migrate", vm_id, host_id, live, enforce, datastore_id)
            results.append(_ack("vm", vm_id, verb))
        return results
    if verb == "resize":
        positionals = require_positionals(parsed, 1, "resize <vmid>")
        vm_id = int(positionals[0])
        template_text = template_from_args(
            ParsedArgs(positionals[1:], parsed.options, parsed.flags)
        )
        transport.call(f"{prefix}.resize", vm_id, template_text, "enforce" in parsed.flags)
        return _ack("vm", vm_id, verb)
    if verb == "backup":
        positionals = require_positionals(parsed, 1, "backup <vmid>")
        vm_id = int(positionals[0])
        datastore_id = int(parsed.options.get("datastore", parsed.options.get("d", -1)))
        reset = "reset" in parsed.flags
        transport.call(f"{prefix}.backup", vm_id, datastore_id, reset)
        return _ack("vm", vm_id, verb)
    if verb == "backup-cancel":
        vm_id = int(require_positionals(parsed, 1, "backup-cancel <vmid>")[0])
        transport.call(f"{prefix}.backupcancel", vm_id)
        return _ack("vm", vm_id, verb)
    if verb == "backupmode":
        positionals = require_positionals(parsed, 2, "backupmode <vmid> <mode>")
        vm_id = int(positionals[0])
        transport.call(f"{prefix}.backupmode", vm_id, positionals[1].upper())
        return _ack("vm", vm_id, verb)
    if verb == "restore":
        positionals = require_positionals(parsed, 2, "restore <vmid> <imageid>")
        vm_id = int(positionals[0])
        increment = int(parsed.options["increment"]) if "increment" in parsed.options else -1
        transport.call(f"{prefix}.restore", vm_id, int(positionals[1]), increment)
        return _ack("vm", vm_id, verb)
    if verb == "disk-resize":
        positionals = require_positionals(parsed, 3, "disk-resize <vmid> <diskid> <size>")
        vm_id = int(positionals[0])
        transport.call(f"{prefix}.diskresize", vm_id, int(positionals[1]), positionals[2])
        return _ack("vm", vm_id, verb)
    if verb == "disk-saveas":
        positionals = require_positionals(parsed, 3, "disk-saveas <vmid> <diskid> <img_name>")
        vm_id = int(positionals[0])
        snapshot_id = int(parsed.options.get("snapshot", -1))
        image_type = parsed.options.get("type", "OS")
        persistent = "persistent" in parsed.flags
        transport.call(
            f"{prefix}.disksaveas",
            vm_id,
            int(positionals[1]),
            positionals[2],
            image_type,
            snapshot_id,
            persistent,
        )
        return _ack("vm", vm_id, verb)
    if verb.startswith("disk-snapshot-"):
        return _run_vm_disk_snapshot(transport, verb, parsed)
    if verb in {"nic-attach", "nic-detach", "nic-update", "pci-attach", "pci-detach"}:
        return _run_vm_device(transport, verb, parsed)
    if verb in {"sg-attach", "sg-detach"}:
        positionals = require_positionals(parsed, 3, f"{verb} <vmid> <nicid> <sgid>")
        vm_id = int(positionals[0])
        method = "attachsg" if verb == "sg-attach" else "detachsg"
        transport.call(f"{prefix}.{method}", vm_id, int(positionals[1]), int(positionals[2]))
        return _ack("vm", vm_id, verb)
    if verb.startswith("snapshot-"):
        return _run_vm_snapshot(transport, verb, parsed)
    if verb in {"sched-update", "update-chart", "create-chart", "sched-delete", "delete-chart"}:
        return _run_vm_schedule(transport, verb, parsed)
    if verb in {"updateconf", "save"}:
        positionals = require_positionals(parsed, 1, f"{verb} <vmid>")
        vm_id = int(positionals[0])
        if verb == "save":
            name = require_positionals(parsed, 2, "save <vmid> <name>")[1]
            transport.call(f"{prefix}.save", vm_id, name)
        else:
            template_text = template_from_args(
                ParsedArgs(positionals[1:], parsed.options, parsed.flags)
            )
            transport.call(f"{prefix}.updateconf", vm_id, template_text)
        return _ack("vm", vm_id, verb)
    if verb in {"ssh", "vnc", "port-forward"}:
        vm_id = int(require_positionals(parsed, 1, f"{verb} <vmid>")[0])
        raw = normalize_value(transport.call(f"{prefix}.info", vm_id))
        return {"resource": "vm", "id": vm_id, "action": verb, "vm": raw}
    raise ApiError(f"Unsupported VM command: {verb}")


def _run_vm_disk_snapshot(
    transport: OpenNebulaTransport,
    verb: str,
    parsed: ParsedArgs,
) -> object:
    prefix = RESOURCE_PREFIX["vm"]
    if verb == "disk-snapshot-list":
        positionals = require_positionals(parsed, 2, "disk-snapshot-list <vmid> <diskid>")
        vm_id = int(positionals[0])
        raw = normalize_value(transport.call(f"{prefix}.info", vm_id))
        return {"resource": "vm", "id": vm_id, "disk_id": int(positionals[1]), "vm": raw}
    arity = 3 if verb in {"disk-snapshot-delete", "disk-snapshot-revert"} else 4
    if verb == "disk-snapshot-create":
        arity = 3
    positionals = require_positionals(parsed, arity, f"{verb} <vmid> <diskid> <snapshot>")
    vm_id = int(positionals[0])
    disk_id = int(positionals[1])
    suffix = verb.removeprefix("disk-snapshot-")
    method = {
        "create": "disksnapshotcreate",
        "delete": "disksnapshotdelete",
        "rename": "disksnapshotrename",
        "revert": "disksnapshotrevert",
    }[suffix]
    if suffix == "create":
        transport.call(f"{prefix}.{method}", vm_id, disk_id, positionals[2])
    elif suffix == "rename":
        transport.call(f"{prefix}.{method}", vm_id, disk_id, int(positionals[2]), positionals[3])
    else:
        transport.call(f"{prefix}.{method}", vm_id, disk_id, int(positionals[2]))
    return _ack("vm", vm_id, verb)


def _run_vm_device(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["vm"]
    if verb in {"nic-detach", "pci-detach"}:
        positionals = require_positionals(parsed, 2, f"{verb} <vmid> <deviceid>")
        vm_id = int(positionals[0])
        method = "detachnic" if verb == "nic-detach" else "detachpci"
        transport.call(f"{prefix}.{method}", vm_id, int(positionals[1]))
        return _ack("vm", vm_id, verb)
    positionals = require_positionals(parsed, 1, f"{verb} <vmid>")
    vm_id = int(positionals[0])
    if verb == "nic-update":
        require_positionals(parsed, 2, "nic-update <vmid> <nicid> [file]")
        nic_id = int(positionals[1])
        template_text = template_from_args(
            ParsedArgs(positionals[2:], parsed.options, parsed.flags)
        )
        transport.call(f"{prefix}.updatenic", vm_id, nic_id, template_text)
        return _ack("vm", vm_id, verb)
    section_name = "NIC" if verb == "nic-attach" else "PCI"
    attrs: list[tuple[str, object]] = []
    for opt, key in (
        ("network", "NETWORK"),
        ("n", "NETWORK"),
        ("ip", "IP"),
        ("nic_name", "NAME"),
        ("pci", "SHORT_ADDRESS"),
        ("pci_vendor", "VENDOR"),
        ("pci_device", "DEVICE"),
        ("pci_class", "CLASS"),
    ):
        if opt in parsed.options:
            attrs.append((key, parsed.options[opt]))
    template_text = template_from_args(parsed) if not attrs else section(section_name, attrs)
    method = "attachnic" if verb == "nic-attach" else "attachpci"
    transport.call(f"{prefix}.{method}", vm_id, template_text)
    return _ack("vm", vm_id, verb)


def _run_vm_snapshot(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["vm"]
    if verb == "snapshot-list":
        vm_id = int(require_positionals(parsed, 1, "snapshot-list <vmid>")[0])
        raw = normalize_value(transport.call(f"{prefix}.info", vm_id))
        return {"resource": "vm", "id": vm_id, "action": verb, "vm": raw}
    if verb == "snapshot-create":
        positionals = require_positionals(parsed, 1, "snapshot-create <range|vmid_list> [name]")
        ids = parse_id_list(positionals[0])
        name = positionals[1] if len(positionals) > 1 else parsed.options.get("name", "")
        results: list[Ack] = []
        for vm_id in ids:
            transport.call(f"{prefix}.snapshotcreate", vm_id, name)
            results.append(_ack("vm", vm_id, verb))
        return results
    positionals = require_positionals(parsed, 2, f"{verb} <vmid> <snapshot_id>")
    vm_id = int(positionals[0])
    method = "snapshotdelete" if verb == "snapshot-delete" else "snapshotrevert"
    transport.call(f"{prefix}.{method}", vm_id, int(positionals[1]))
    return _ack("vm", vm_id, verb)


def _run_vm_schedule(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["vm"]
    delete = verb in {"sched-delete", "delete-chart"}
    positionals = require_positionals(
        parsed,
        2 if delete or "update" in verb else 1,
        f"{verb} <vmid>",
    )
    vm_id = int(positionals[0])
    if delete:
        transport.call(f"{prefix}.scheddelete", vm_id, int(positionals[1]))
        return _ack("vm", vm_id, verb)
    schedule_positionals = positionals[2:] if "update" in verb else positionals[1:]
    template_text = template_from_args(
        ParsedArgs(schedule_positionals, parsed.options, parsed.flags)
    )
    if verb in {"sched-update", "update-chart"}:
        transport.call(f"{prefix}.schedupdate", vm_id, int(positionals[1]), template_text)
    else:
        transport.call(f"{prefix}.schedadd", vm_id, template_text)
    return _ack("vm", vm_id, verb)


def _run_host(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["host"]
    if verb == "create":
        hostname = require_positionals(parsed, 1, "create <hostname> [file]")[0]
        im_mad = parsed.options.get("im_mad", parsed.options.get("i", "kvm"))
        vmm_mad = parsed.options.get("vmm_mad", parsed.options.get("v", "kvm"))
        cluster_id = int(parsed.options.get("cluster", parsed.options.get("c", -1)))
        host_id = int(transport.call(f"{prefix}.allocate", hostname, im_mad, vmm_mad, cluster_id))
        return _ack("host", host_id, verb)
    if verb in HOST_STATUS:
        ids = parse_id_list(require_positionals(parsed, 1, f"{verb} <range|hostid_list>")[0])
        return _batch_action(
            transport,
            family="host",
            ids=ids,
            method=f"{prefix}.status",
            action=verb,
            trailing_args=(HOST_STATUS[verb],),
        )
    if verb in {"forceupdate", "sync"}:
        ids = parse_id_list(parsed.positionals[0]) if parsed.positionals else [-1]
        method = "forceupdate" if verb == "forceupdate" else "sync"
        return _batch_action(
            transport,
            family="host",
            ids=ids,
            method=f"{prefix}.{method}",
            action=verb,
        )
    if verb == "monitoring":
        positionals = require_positionals(parsed, 2, "monitoring <hostid> <attr>")
        host_id = int(positionals[0])
        raw = normalize_value(transport.call(f"{prefix}.monitoring", host_id))
        return {
            "resource": "host",
            "id": host_id,
            "attribute": positionals[1],
            "monitoring": raw,
        }
    raise ApiError(f"Unsupported host command: {verb}")


def _run_image(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["image"]
    if verb == "create":
        template_text = template_from_args(parsed)
        datastore_id = int(parsed.options.get("datastore", parsed.options.get("d", -1)))
        image_id = int(transport.call(f"{prefix}.allocate", template_text, datastore_id))
        return _ack("image", image_id, verb)
    if verb == "clone":
        positionals = require_positionals(parsed, 2, "clone <imageid> <name>")
        image_id = int(positionals[0])
        clone_id = int(transport.call(f"{prefix}.clone", image_id, positionals[1]))
        return Ack(
            resource="image",
            id=clone_id,
            action=verb,
            message=f"cloned from {image_id}",
        )
    if verb == "chtype":
        positionals = require_positionals(parsed, 2, "chtype <range|imageid_list> <type>")
        return _batch_action(
            transport,
            family="image",
            ids=parse_id_list(positionals[0]),
            method=f"{prefix}.chtype",
            action=verb,
            trailing_args=(positionals[1],),
        )
    if verb in {"enable", "disable", "persistent", "nonpersistent"}:
        positionals = require_positionals(parsed, 1, f"{verb} <range|imageid_list>")
        method = "enable" if verb in {"enable", "disable"} else "persistent"
        enabled = verb in {"enable", "persistent"}
        return _batch_action(
            transport,
            family="image",
            ids=parse_id_list(positionals[0]),
            method=f"{prefix}.{method}",
            action=verb,
            trailing_args=(enabled,),
        )
    if verb == "restore":
        image_id = int(require_positionals(parsed, 1, "restore <imageid>")[0])
        transport.call(f"{prefix}.restore", image_id)
        return _ack("image", image_id, verb)
    if verb in {"snapshot-delete", "snapshot-flatten", "snapshot-revert"}:
        positionals = require_positionals(parsed, 2, f"{verb} <imageid> <snapshot_id>")
        image_id = int(positionals[0])
        suffix = verb.removeprefix("snapshot-")
        method = {
            "delete": "snapshotdelete",
            "flatten": "snapshotflatten",
            "revert": "snapshotrevert",
        }[suffix]
        transport.call(f"{prefix}.{method}", image_id, int(positionals[1]))
        return _ack("image", image_id, verb)
    if verb == "orphans":
        return _orphans(transport, "image")
    raise ApiError(f"Unsupported image command: {verb}")


def _run_template(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["template"]
    if verb == "create":
        template_text = template_from_args(parsed)
        template_id = int(transport.call(f"{prefix}.allocate", template_text))
        return _ack("template", template_id, verb)
    if verb == "clone":
        positionals = require_positionals(parsed, 2, "clone <templateid> <name>")
        template_id = int(positionals[0])
        clone_id = int(transport.call(f"{prefix}.clone", template_id, positionals[1]))
        return Ack(
            resource="template",
            id=clone_id,
            action=verb,
            message=f"cloned from {template_id}",
        )
    raise ApiError(f"Unsupported template command: {verb}")


def _run_vnet(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["vnet"]
    if verb == "create":
        template_text = template_from_args(parsed)
        cluster_id = int(parsed.options.get("cluster", parsed.options.get("c", -1)))
        vnet_id = int(transport.call(f"{prefix}.allocate", template_text, cluster_id))
        return _ack("vnet", vnet_id, verb)
    if verb in {"addar", "updatear"}:
        positionals = require_positionals(
            parsed,
            1 if verb == "addar" else 2,
            f"{verb} <vnetid>",
        )
        vnet_id = int(positionals[0])
        ar_positionals = positionals[2:] if verb == "updatear" else positionals[1:]
        template_text = template_from_args(ParsedArgs(ar_positionals, parsed.options, parsed.flags))
        if verb == "addar":
            transport.call(f"{prefix}.add_ar", vnet_id, template_text)
        else:
            transport.call(f"{prefix}.update_ar", vnet_id, int(positionals[1]), template_text)
        return _ack("vnet", vnet_id, verb)
    if verb == "rmar":
        positionals = require_positionals(parsed, 2, "rmar <vnetid> <ar_id>")
        vnet_id = int(positionals[0])
        transport.call(f"{prefix}.rm_ar", vnet_id, int(positionals[1]))
        return _ack("vnet", vnet_id, verb)
    if verb in {"addleases", "rmleases", "hold", "release"}:
        positionals = require_positionals(parsed, 2, f"{verb} <vnetid> <ip>")
        vnet_id = int(positionals[0])
        method = {
            "addleases": "addleases",
            "rmleases": "rmleases",
            "hold": "hold",
            "release": "release",
        }[verb]
        extra: tuple[object, ...] = (
            (positionals[2],) if verb == "addleases" and len(positionals) > 2 else ()
        )
        transport.call(f"{prefix}.{method}", vnet_id, positionals[1], *extra)
        return _ack("vnet", vnet_id, verb)
    if verb == "free":
        positionals = require_positionals(parsed, 2, "free <vnetid> <ar_id>")
        vnet_id = int(positionals[0])
        transport.call(f"{prefix}.free", vnet_id, int(positionals[1]))
        return _ack("vnet", vnet_id, verb)
    if verb == "reserve":
        positionals = require_positionals(parsed, 1, "reserve <vnetid> [vnetid]")
        vnet_id = int(positionals[0])
        template_parts = []
        if len(positionals) > 1:
            template_parts.append(f"VNET_ID = {quote_template_value(positionals[1])}")
        if "size" in parsed.options:
            template_parts.append(f"SIZE = {quote_template_value(parsed.options['size'])}")
        if "name" in parsed.options:
            template_parts.append(f"NAME = {quote_template_value(parsed.options['name'])}")
        transport.call(f"{prefix}.reserve", vnet_id, "\n".join(template_parts))
        return _ack("vnet", vnet_id, verb)
    if verb == "recover":
        ids = parse_id_list(require_positionals(parsed, 1, "recover <range|vnetid_list>")[0])
        return _batch_action(
            transport,
            family="vnet",
            ids=ids,
            method=f"{prefix}.recover",
            action=verb,
        )
    if verb == "orphans":
        return _orphans(transport, "vnet")
    raise ApiError(f"Unsupported vnet command: {verb}")


def _run_datastore(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["datastore"]
    if verb == "create":
        template_text = template_from_args(parsed)
        cluster_id = int(parsed.options.get("cluster", parsed.options.get("c", -1)))
        datastore_id = int(transport.call(f"{prefix}.allocate", template_text, cluster_id))
        return _ack("datastore", datastore_id, verb)
    if verb in {"enable", "disable"}:
        ids = parse_id_list(require_positionals(parsed, 1, f"{verb} <range|datastoreid_list>")[0])
        return _batch_action(
            transport,
            family="datastore",
            ids=ids,
            method=f"{prefix}.enable",
            action=verb,
            trailing_args=(verb == "enable",),
        )
    raise ApiError(f"Unsupported datastore command: {verb}")


def _run_cluster(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["cluster"]
    if verb == "create":
        name = require_positionals(parsed, 1, "create <name>")[0]
        cluster_id = int(transport.call(f"{prefix}.allocate", name))
        return _ack("cluster", cluster_id, verb)
    relation_methods = {
        "addhost": "addhost",
        "delhost": "delhost",
        "adddatastore": "adddatastore",
        "deldatastore": "deldatastore",
        "addvnet": "addvnet",
        "delvnet": "delvnet",
    }
    if verb in relation_methods:
        positionals = require_positionals(parsed, 2, f"{verb} <clusterid> <resourceid>")
        cluster_id = int(positionals[0])
        transport.call(f"{prefix}.{relation_methods[verb]}", cluster_id, int(positionals[1]))
        return _ack("cluster", cluster_id, verb)
    if verb in {"optimize", "plandelete", "planexecute"}:
        cluster_id = int(require_positionals(parsed, 1, f"{verb} <clusterid>")[0])
        transport.call(f"{prefix}.{verb}", cluster_id)
        return _ack("cluster", cluster_id, verb)
    raise ApiError(f"Unsupported cluster command: {verb}")


def _run_acl(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    if verb == "create":
        positionals = require_positionals(parsed, 1, "create <user|rulestr> [resource] [rights]")
        rule_id = -1
        if len(positionals) >= 3:
            raw = _call_first(
                transport,
                ("one.acl.addrule", "one.acl.allocate"),
                positionals[0],
                positionals[1],
                positionals[2],
            )
        else:
            raw = _call_first(
                transport,
                ("one.acl.addrule", "one.acl.allocate"),
                positionals[0],
            )
        try:
            rule_id = int(str(raw))
        except (TypeError, ValueError):
            rule_id = -1
        return _ack("acl", rule_id, verb)
    if verb == "delete":
        ids = parse_id_list(require_positionals(parsed, 1, "delete <range>")[0])
        return _batch_action(
            transport,
            family="acl",
            ids=ids,
            method="one.acl.delrule",
            action=verb,
        )
    raise ApiError(f"Unsupported ACL command: {verb}")


def _run_group(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["group"]
    if verb == "create":
        name = (
            parsed.positionals[0] if parsed.positionals else parsed.options.get("name", "")
        ).strip()
        if not name:
            raise ApiError("Missing arguments. Usage: create [group_name]")
        group_id = int(str(_call_first(transport, (f"{prefix}.allocate",), name)))
        return _ack("group", group_id, verb)
    if verb == "vlan":
        positionals = require_positionals(parsed, 1, "vlan <groupid> [file]")
        group_id = int(positionals[0])
        file_value = positionals[1] if len(positionals) > 1 else parsed.options.get("file")
        vlan_rules = read_template_file(file_value) if file_value else ""
        transport.call(f"{prefix}.vlan", group_id, vlan_rules)
        return _ack("group", group_id, verb)
    if verb in {"addadmin", "deladmin"}:
        positionals = require_positionals(parsed, 2, f"{verb} <range|groupid_list> <userid>")
        ids = parse_id_list(positionals[0])
        method = f"{prefix}.addadmin" if verb == "addadmin" else f"{prefix}.deladmin"
        return _batch_action(
            transport,
            family="group",
            ids=ids,
            method=method,
            action=verb,
            trailing_args=(int(positionals[1]),),
        )
    if verb in {"quota", "batchquota"}:
        positionals = require_positionals(parsed, 1, f"{verb} <range|groupid_list> [file]")
        ids = parse_id_list(positionals[0])
        template_text = template_from_args(
            ParsedArgs(positionals=positionals[1:], options=parsed.options, flags=parsed.flags)
        )
        results: list[Ack] = []
        for group_id in ids:
            _call_first(
                transport, (f"{prefix}.quota", f"{prefix}.set_quota"), group_id, template_text
            )
            results.append(_ack("group", group_id, verb))
        return results
    if verb == "defaultquota":
        template_text = template_from_args(parsed)
        _call_first(
            transport, (f"{prefix}.quotadefault", f"{prefix}.set_quotadefault"), template_text
        )
        return {"resource": "group", "action": verb, "updated": True}
    raise ApiError(f"Unsupported group command: {verb}")


def _run_user(transport: OpenNebulaTransport, verb: str, parsed: ParsedArgs) -> object:
    prefix = RESOURCE_PREFIX["user"]
    if verb == "create":
        positionals = require_positionals(parsed, 1, "create <username> [password]")
        username = positionals[0]
        password = positionals[1] if len(positionals) > 1 else parsed.options.get("password", "")
        auth_driver = parsed.options.get("driver", "core")
        groups = [
            int(item)
            for item in (
                parsed.options.get("group", "").split(",") if "group" in parsed.options else []
            )
            if item.strip().isdigit()
        ]
        raw_id = _call_first(
            transport,
            (f"{prefix}.allocate",),
            username,
            password,
            auth_driver,
            True,
            groups,
        )
        return _ack("user", int(str(raw_id)), verb)
    if verb in {"addgroup", "delgroup", "chgrp"}:
        positionals = require_positionals(parsed, 2, f"{verb} <range|userid_list> <groupid>")
        ids = parse_id_list(positionals[0])
        group_id = int(positionals[1])
        if verb == "addgroup":
            method = f"{prefix}.addgroup"
        elif verb == "delgroup":
            method = f"{prefix}.delgroup"
        else:
            method = f"{prefix}.chgrp"
        return _batch_action(
            transport,
            family="user",
            ids=ids,
            method=method,
            action=verb,
            trailing_args=(group_id,),
        )
    if verb in {"enable", "disable"}:
        ids = parse_id_list(require_positionals(parsed, 1, f"{verb} <range|userid_list>")[0])
        method = f"{prefix}.enable"
        enabled = verb == "enable"
        return _batch_action(
            transport,
            family="user",
            ids=ids,
            method=method,
            action=verb,
            trailing_args=(enabled,),
        )
    if verb in {"passwd", "chauth"}:
        positionals = require_positionals(parsed, 1, f"{verb} <userid>")
        user_id = int(positionals[0])
        if verb == "passwd":
            password = (
                positionals[1] if len(positionals) > 1 else parsed.options.get("password", "")
            )
            transport.call(f"{prefix}.passwd", user_id, password)
        else:
            auth_driver = parsed.options.get("driver") or (
                positionals[1] if len(positionals) > 1 else "core"
            )
            password = (
                positionals[2] if len(positionals) > 2 else parsed.options.get("password", "")
            )
            transport.call(f"{prefix}.chauth", user_id, auth_driver, password)
        return _ack("user", user_id, verb)
    if verb in {"quota", "batchquota"}:
        positionals = require_positionals(parsed, 1, f"{verb} <range|userid_list> [file]")
        ids = parse_id_list(positionals[0])
        template_text = template_from_args(
            ParsedArgs(positionals=positionals[1:], options=parsed.options, flags=parsed.flags)
        )
        results: list[Ack] = []
        for user_id in ids:
            _call_first(
                transport, (f"{prefix}.quota", f"{prefix}.set_quota"), user_id, template_text
            )
            results.append(_ack("user", user_id, verb))
        return results
    if verb == "defaultquota":
        template_text = template_from_args(parsed)
        _call_first(
            transport, (f"{prefix}.quotadefault", f"{prefix}.set_quotadefault"), template_text
        )
        return {"resource": "user", "action": verb, "updated": True}
    if verb == "passwdsearch":
        positionals = require_positionals(parsed, 2, "passwdsearch <driver> <password>")
        raw = _pool_snapshot(transport, "user", ParsedArgs([], {}, set()))
        users = ensure_list(object_get(raw, "USER"))
        search = positionals[1]
        driver = positionals[0]
        matches: list[object] = []
        for user in users:
            if str(object_get(user, "AUTH_DRIVER", "")) != driver:
                continue
            if search in str(object_get(user, "PASSWORD", "")):
                matches.append(normalize_value(user))
        return matches
    if verb == "encode":
        positionals = require_positionals(parsed, 1, "encode <username> [password]")
        username = positionals[0]
        password = positionals[1] if len(positionals) > 1 else parsed.options.get("password", "")
        token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
        return {"resource": "user", "action": verb, "username": username, "encoded": token}
    if verb in {
        "key",
        "login",
        "token-create",
        "token-delete",
        "token-delete-all",
        "token-set",
        "umask",
    }:
        target = (
            int(parsed.positionals[0])
            if parsed.positionals and parsed.positionals[0].isdigit()
            else -1
        )
        return _ack("user", target, verb)
    raise ApiError(f"Unsupported user command: {verb}")
