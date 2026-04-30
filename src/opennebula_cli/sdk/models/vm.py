"""VM models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from opennebula_cli.sdk.models.common import normalize_value, object_get

VM_STATES = (
    "INIT",
    "PENDING",
    "HOLD",
    "ACTIVE",
    "STOPPED",
    "SUSPENDED",
    "DONE",
    "FAILED",
    "POWEROFF",
    "UNDEPLOYED",
    "CLONING",
    "CLONING_FAILURE",
)

LCM_STATES = (
    "LCM_INIT",
    "PROLOG",
    "BOOT",
    "RUNNING",
    "MIGRATE",
    "SAVE_STOP",
    "SAVE_SUSPEND",
    "SAVE_MIGRATE",
    "PROLOG_MIGRATE",
    "PROLOG_RESUME",
    "EPILOG_STOP",
    "EPILOG",
    "SHUTDOWN",
    "CANCEL",
    "FAILURE",
    "CLEANUP_RESUBMIT",
    "UNKNOWN",
    "HOTPLUG",
    "SHUTDOWN_POWEROFF",
    "BOOT_UNKNOWN",
    "BOOT_POWEROFF",
    "BOOT_SUSPENDED",
    "BOOT_STOPPED",
    "CLEANUP_DELETE",
    "HOTPLUG_SNAPSHOT",
    "HOTPLUG_NIC",
    "HOTPLUG_SAVEAS",
    "HOTPLUG_SAVEAS_POWEROFF",
    "HOTPLUG_SAVEAS_SUSPENDED",
    "SHUTDOWN_UNDEPLOY",
    "EPILOG_UNDEPLOY",
    "PROLOG_UNDEPLOY",
    "BOOT_UNDEPLOY",
    "HOTPLUG_PROLOG_POWEROFF",
    "HOTPLUG_EPILOG_POWEROFF",
    "BOOT_MIGRATE",
    "BOOT_FAILURE",
    "BOOT_MIGRATE_FAILURE",
    "PROLOG_MIGRATE_FAILURE",
    "PROLOG_FAILURE",
    "EPILOG_FAILURE",
    "EPILOG_STOP_FAILURE",
    "EPILOG_UNDEPLOY_FAILURE",
    "PROLOG_MIGRATE_POWEROFF",
    "PROLOG_MIGRATE_POWEROFF_FAILURE",
    "PROLOG_MIGRATE_SUSPEND",
    "PROLOG_MIGRATE_SUSPEND_FAILURE",
    "BOOT_UNDEPLOY_FAILURE",
    "BOOT_STOPPED_FAILURE",
    "PROLOG_RESUME_FAILURE",
    "PROLOG_UNDEPLOY_FAILURE",
    "DISK_SNAPSHOT_POWEROFF",
    "DISK_SNAPSHOT_REVERT_POWEROFF",
    "DISK_SNAPSHOT_DELETE_POWEROFF",
    "DISK_SNAPSHOT_SUSPENDED",
    "DISK_SNAPSHOT_REVERT_SUSPENDED",
    "DISK_SNAPSHOT_DELETE_SUSPENDED",
    "DISK_SNAPSHOT",
    "DISK_SNAPSHOT_REVERT",
    "DISK_SNAPSHOT_DELETE",
    "PROLOG_MIGRATE_UNKNOWN",
    "PROLOG_MIGRATE_UNKNOWN_FAILURE",
    "DISK_RESIZE",
    "DISK_RESIZE_POWEROFF",
    "DISK_RESIZE_UNDEPLOYED",
    "HOTPLUG_NIC_POWEROFF",
    "HOTPLUG_RESIZE",
    "HOTPLUG_SAVEAS_UNDEPLOYED",
    "HOTPLUG_SAVEAS_STOPPED",
    "BACKUP",
    "BACKUP_POWEROFF",
    "RESTORE",
)


def _enum_label(raw: object, labels: tuple[str, ...]) -> str:
    value = object_get(raw, "value", raw)
    if isinstance(value, int):
        return labels[value] if 0 <= value < len(labels) else str(value)
    if isinstance(value, str) and value.isdigit():
        index = int(value)
        return labels[index] if 0 <= index < len(labels) else value
    return str(value)


class Vm(BaseModel):
    """Normalized OpenNebula VM model."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    state: str
    lcm_state: str | None = None
    host: str | None = None
    ips: list[str] = Field(default_factory=list)
    template: dict[str, Any] = Field(default_factory=dict)
    user_template: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: object) -> Vm:
        template = normalize_value(object_get(raw, "TEMPLATE", {}))
        user_template = normalize_value(object_get(raw, "USER_TEMPLATE", {}))
        history = object_get(raw, "HISTORY_RECORDS")
        ips: list[str] = []
        if isinstance(template, dict):
            nic = template.get("NIC")
            if isinstance(nic, list):
                ips = [
                    str(item.get("IP"))
                    for item in nic
                    if isinstance(item, dict) and item.get("IP")
                ]
            elif isinstance(nic, dict) and nic.get("IP"):
                ips = [str(nic["IP"])]
        state = object_get(raw, "STATE_STR")
        if state is None:
            state = _enum_label(object_get(raw, "STATE", ""), VM_STATES)
        lcm_state_raw = object_get(raw, "LCM_STATE_STR")
        if lcm_state_raw is None:
            lcm_state_raw = _enum_label(object_get(raw, "LCM_STATE", ""), LCM_STATES)
        lcm_state = str(lcm_state_raw) or None
        history_host = object_get(history, "HOSTNAME", None) if history else None
        host = str(history_host) if history_host else None
        normalized_template = template if isinstance(template, dict) else {"value": template}
        normalized_user_template = (
            user_template if isinstance(user_template, dict) else {"value": user_template}
        )
        return cls(
            id=int(object_get(raw, "ID", 0)),
            name=str(object_get(raw, "NAME", "")),
            state=str(state),
            lcm_state=lcm_state,
            host=host,
            ips=ips,
            template=normalized_template,
            user_template=normalized_user_template,
        )


class VmDisk(BaseModel):
    """VM disk summary for recovery workflows."""

    model_config = ConfigDict(frozen=True)

    disk_id: int | None = None
    image_id: int | None = None
    image: str | None = None
    target: str | None = None
    dev_prefix: str | None = None
    datastore_id: int | None = None
    source: str | None = None
    serial: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
