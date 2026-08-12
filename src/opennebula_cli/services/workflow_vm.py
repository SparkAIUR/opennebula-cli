"""Workflow VM initialization service."""

from __future__ import annotations

import copy
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Protocol

import yaml

from opennebula_cli.sdk.exceptions import ApiError
from opennebula_cli.sdk.models.common import Ack
from opennebula_cli.sdk.models.vm import Vm
from opennebula_cli.waiters.generic import wait_for
from opennebula_cli.waiters.vm import is_running

SIZE_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(Ki|Mi|Gi|Ti)\s*$", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class _TemplateReference:
    template_id: int | None = None
    template_name: str | None = None


class _TemplateApi(Protocol):
    def list(self) -> Sequence[Any]:
        """List templates."""

    def instantiate(
        self,
        template_id: int,
        *,
        name: str | None = None,
        template_body: str | None = None,
    ) -> Ack:
        """Instantiate a template."""


class _VmApi(Protocol):
    def show(self, vm_id: int) -> Vm:
        """Show one VM."""


class WorkflowVmInitService:
    """Initialize VMs from workflow YAML definitions."""

    def __init__(self, *, template_service: _TemplateApi, vm_service: _VmApi) -> None:
        self._template_service = template_service
        self._vm_service = vm_service
        self._template_index: dict[str, list[int]] | None = None

    def init_single(
        self,
        *,
        workflow_file: Path | None,
        name: str | None,
        selector_name: str | None,
        selector_index: int | None,
        set_values: list[str] | None = None,
        template_id: int | None = None,
        template_name: str | None = None,
        wait_ready: bool = False,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
        show_progress: bool = True,
    ) -> dict[str, Any]:
        """Initialize one VM either from a file entry or inline inputs."""

        if workflow_file is not None:
            spec = self._load_spec(workflow_file)
        else:
            spec = self._build_single_spec(
                name=name,
                template_id=template_id,
                template_name=template_name,
            )
        if workflow_file is None:
            selector_name = None
            selector_index = 0
            template_id = None
            template_name = None

        spec = self._apply_set_overrides(spec, set_values or [])
        selected = self._select_single_entries(
            spec,
            selector_name=selector_name,
            selector_index=selector_index,
        )
        summary = self._instantiate_entries(
            spec,
            entries=selected,
            cli_template_ref=self._build_cli_template_ref(template_id, template_name),
            wait_ready=wait_ready,
            timeout=timeout,
            poll_interval=poll_interval,
            show_progress=show_progress,
        )
        summary["mode"] = "single"
        return summary

    def apply_bulk(
        self,
        workflow_file: Path,
        *,
        set_values: list[str] | None = None,
        template_id: int | None = None,
        template_name: str | None = None,
        wait_ready: bool = False,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
        show_progress: bool = True,
    ) -> dict[str, Any]:
        """Initialize all VMs listed in a workflow file."""

        spec = self._load_spec(workflow_file)
        spec = self._apply_set_overrides(spec, set_values or [])
        entries = self._select_bulk_entries(spec)
        summary = self._instantiate_entries(
            spec,
            entries=entries,
            cli_template_ref=self._build_cli_template_ref(template_id, template_name),
            wait_ready=wait_ready,
            timeout=timeout,
            poll_interval=poll_interval,
            show_progress=show_progress,
        )
        summary["mode"] = "bulk"
        return summary

    def _build_single_spec(
        self,
        *,
        name: str | None,
        template_id: int | None,
        template_name: str | None,
    ) -> dict[str, Any]:
        vm_name = (name or "").strip()
        if not vm_name:
            raise ApiError("`--name` is required when workflow file is not provided")
        template_ref = self._build_cli_template_ref(template_id, template_name)
        if template_ref is None:
            raise ApiError(
                "`--template-id` or `--template-name` is required "
                "when workflow file is not provided"
            )
        template_payload: dict[str, Any] = {}
        if template_ref.template_id is not None:
            template_payload["id"] = template_ref.template_id
        if template_ref.template_name is not None:
            template_payload["name"] = template_ref.template_name
        return {
            "template": template_payload,
            "global": {},
            "vms": [{"name": vm_name}],
        }

    def _load_spec(self, workflow_file: Path) -> dict[str, Any]:
        target = workflow_file.expanduser().resolve()
        try:
            raw = yaml.safe_load(target.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ApiError(f"Unable to read workflow VM file {target}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ApiError(f"Invalid workflow VM YAML in {target}: {exc}") from exc

        if not isinstance(raw, Mapping):
            raise ApiError(f"Workflow VM file must contain a mapping: {target}")

        template_raw = raw.get("template", {})
        global_raw = raw.get("global", {})
        vms_raw = raw.get("vms", [])

        if template_raw is None:
            template_raw = {}
        if global_raw is None:
            global_raw = {}
        if not isinstance(template_raw, Mapping):
            raise ApiError("`template` must be a mapping")
        if not isinstance(global_raw, Mapping):
            raise ApiError("`global` must be a mapping")
        if not isinstance(vms_raw, list):
            raise ApiError("`vms` must be a list")

        normalized_vms: list[dict[str, Any]] = []
        for index, vm in enumerate(vms_raw):
            if not isinstance(vm, Mapping):
                raise ApiError(f"`vms[{index}]` must be a mapping")
            normalized_vms.append(dict(vm))

        return {
            "template": dict(template_raw),
            "global": dict(global_raw),
            "vms": normalized_vms,
        }

    def _apply_set_overrides(self, spec: dict[str, Any], entries: list[str]) -> dict[str, Any]:
        updated = copy.deepcopy(spec)
        for entry in entries:
            path, value = self._parse_set_entry(entry)
            self._apply_dot_path(updated, path, value)
        return updated

    @staticmethod
    def _parse_set_entry(entry: str) -> tuple[list[str], Any]:
        if "=" not in entry:
            raise ApiError(f"Invalid `--set` value '{entry}', expected path=value")
        path_raw, value_raw = entry.split("=", 1)
        path = [segment.strip() for segment in path_raw.split(".") if segment.strip()]
        if not path:
            raise ApiError(f"Invalid `--set` value '{entry}', path cannot be empty")
        try:
            value = yaml.safe_load(value_raw)
        except yaml.YAMLError as exc:
            raise ApiError(f"Invalid value for `--set` path '{path_raw}': {exc}") from exc
        return path, value

    def _apply_dot_path(self, root: Any, path: list[str], value: Any) -> None:
        current = root
        for idx, segment in enumerate(path[:-1]):
            next_segment = path[idx + 1]
            if isinstance(current, dict):
                if segment not in current or current[segment] is None:
                    current[segment] = [] if next_segment.isdigit() else {}
                current = current[segment]
                continue
            if isinstance(current, list):
                if not segment.isdigit():
                    raise ApiError(
                        f"`--set` path segment '{segment}' must be an index for list values"
                    )
                index = int(segment)
                if index < 0 or index >= len(current):
                    raise ApiError(f"`--set` index out of range: {segment}")
                if current[index] is None:
                    current[index] = [] if next_segment.isdigit() else {}
                current = current[index]
                continue
            raise ApiError("`--set` path traverses a non-container value")

        last = path[-1]
        if isinstance(current, dict):
            current[last] = value
            return
        if isinstance(current, list):
            if not last.isdigit():
                raise ApiError(f"`--set` final segment '{last}' must be a list index")
            index = int(last)
            if index < 0 or index >= len(current):
                raise ApiError(f"`--set` index out of range: {last}")
            current[index] = value
            return
        raise ApiError("`--set` path targets a non-container value")

    def _select_single_entries(
        self,
        spec: dict[str, Any],
        *,
        selector_name: str | None,
        selector_index: int | None,
    ) -> list[tuple[int, dict[str, Any]]]:
        vms = self._require_vm_entries(spec)
        if selector_name and selector_index is not None:
            raise ApiError("Use only one selector: `--vm-name` or `--index`")

        if selector_index is not None:
            if selector_index < 0 or selector_index >= len(vms):
                raise ApiError(f"`--index` out of range: {selector_index}")
            return [(selector_index, dict(vms[selector_index]))]

        if selector_name:
            matches = [
                (index, dict(vm))
                for index, vm in enumerate(vms)
                if str(vm.get("name", "")).strip() == selector_name
            ]
            if not matches:
                raise ApiError(f"No VM entry named '{selector_name}'")
            if len(matches) > 1:
                raise ApiError(f"Multiple VM entries named '{selector_name}', use `--index`")
            return matches

        if len(vms) == 1:
            return [(0, dict(vms[0]))]
        raise ApiError(
            "Single initialization requires a selector when multiple `vms` entries exist "
            "(use `--vm-name` or `--index`)."
        )

    def _select_bulk_entries(self, spec: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
        vms = self._require_vm_entries(spec)
        return [(index, dict(vm)) for index, vm in enumerate(vms)]

    @staticmethod
    def _require_vm_entries(spec: dict[str, Any]) -> list[dict[str, Any]]:
        vms_raw = spec.get("vms", [])
        if not isinstance(vms_raw, list):
            raise ApiError("`vms` must be a list")
        vms = [vm for vm in vms_raw if isinstance(vm, Mapping)]
        if len(vms) != len(vms_raw):
            raise ApiError("All `vms` entries must be mappings")
        if not vms:
            raise ApiError("`vms` must contain at least one entry")
        return [dict(vm) for vm in vms]

    def _instantiate_entries(
        self,
        spec: dict[str, Any],
        *,
        entries: list[tuple[int, dict[str, Any]]],
        cli_template_ref: _TemplateReference | None,
        wait_ready: bool,
        timeout: float,
        poll_interval: float,
        show_progress: bool,
    ) -> dict[str, Any]:
        if wait_ready:
            self._validate_wait_args(timeout=timeout, poll_interval=poll_interval)

        global_defaults = self._mapping(spec.get("global", {}), field="global")
        default_template_ref = self._normalize_template_ref(
            spec.get("template"),
            field="template",
            allow_empty=True,
        )

        results: list[dict[str, Any]] = []
        succeeded = 0
        failed = 0
        for index, entry in entries:
            vm_id: int | None = None
            template_id: int | None = None
            template_name: str | None = None
            effective_entry_name = str(entry.get("name", "")).strip() or None
            effective_vm_name: str | None = None
            try:
                effective = self._deep_merge(global_defaults, entry)
                template_ref = self._resolve_template_ref(
                    cli_ref=cli_template_ref,
                    entry_ref=self._normalize_template_ref(
                        effective.get("template"),
                        field=f"vms[{index}].template",
                        allow_empty=True,
                    ),
                    default_ref=default_template_ref,
                )
                template_id, template_name = self._resolve_template_id(template_ref)
                effective_vm_name = self._resolve_vm_name(effective)
                override_payload = self._build_instantiate_override(effective)
                override_text = (
                    self._serialize_template(override_payload) if override_payload else None
                )
                ack = self._template_service.instantiate(
                    template_id,
                    name=effective_vm_name,
                    template_body=override_text,
                )
                vm_id = ack.id
                result: dict[str, Any] = {
                    "index": index,
                    "entry_name": effective_entry_name,
                    "vm_name": effective_vm_name,
                    "template_id": template_id,
                    "template_name": template_name,
                    "status": "success",
                    "id": vm_id,
                    "action": ack.action,
                }
                if wait_ready:
                    vm_id_for_wait = vm_id
                    if vm_id_for_wait is None:
                        raise ApiError("Instantiation did not return a VM id")

                    wait_result = wait_for(
                        resource="vm",
                        resource_id=vm_id_for_wait,
                        fetch=partial(self._vm_service.show, vm_id_for_wait),
                        predicate=is_running,
                        state_label=lambda vm: f"{vm.state}/{vm.lcm_state or '-'}",
                        timeout=timeout,
                        poll_interval=poll_interval,
                        show_progress=show_progress,
                    )
                    result["wait_state"] = wait_result.state
                succeeded += 1
                results.append(result)
            except Exception as exc:
                failed += 1
                results.append(
                    {
                        "index": index,
                        "entry_name": effective_entry_name,
                        "vm_name": effective_vm_name,
                        "template_id": template_id,
                        "template_name": template_name,
                        "status": "failed",
                        "id": vm_id,
                        "error": str(exc),
                    }
                )

        return {
            "total": len(entries),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        }

    @staticmethod
    def _validate_wait_args(*, timeout: float, poll_interval: float) -> None:
        if timeout <= 0:
            raise ApiError("`--timeout` must be a positive number")
        if poll_interval <= 0:
            raise ApiError("`--poll-interval` must be a positive number")

    @staticmethod
    def _mapping(raw: Any, *, field: str) -> dict[str, Any]:
        if raw is None:
            return {}
        if not isinstance(raw, Mapping):
            raise ApiError(f"`{field}` must be a mapping")
        return dict(raw)

    @staticmethod
    def _build_cli_template_ref(
        template_id: int | None,
        template_name: str | None,
    ) -> _TemplateReference | None:
        if template_id is not None and template_name:
            raise ApiError("Use only one template selector: `--template-id` or `--template-name`")
        if template_id is None and not template_name:
            return None
        normalized_name = template_name.strip() if template_name is not None else None
        if normalized_name == "":
            normalized_name = None
        return _TemplateReference(template_id=template_id, template_name=normalized_name)

    @staticmethod
    def _normalize_template_ref(
        raw: Any,
        *,
        field: str,
        allow_empty: bool,
    ) -> _TemplateReference | None:
        if raw is None:
            return None if allow_empty else _TemplateReference()
        if not isinstance(raw, Mapping):
            raise ApiError(f"`{field}` must be a mapping")
        template_id_raw = raw.get("id")
        template_name_raw = raw.get("name")
        template_id: int | None
        if template_id_raw is None:
            template_id = None
        else:
            try:
                template_id = int(template_id_raw)
            except (TypeError, ValueError) as exc:
                raise ApiError(f"`{field}.id` must be an integer") from exc
        template_name = str(template_name_raw).strip() if template_name_raw is not None else None
        if template_name == "":
            template_name = None
        if template_id is None and template_name is None:
            if allow_empty:
                return None
            raise ApiError(f"`{field}` must include `id` or `name`")
        return _TemplateReference(template_id=template_id, template_name=template_name)

    @staticmethod
    def _resolve_template_ref(
        *,
        cli_ref: _TemplateReference | None,
        entry_ref: _TemplateReference | None,
        default_ref: _TemplateReference | None,
    ) -> _TemplateReference:
        if cli_ref is not None:
            return cli_ref
        if entry_ref is not None:
            return entry_ref
        if default_ref is not None:
            return default_ref
        raise ApiError(
            "Template reference is required via top-level `template`, per-VM `template`, "
            "or CLI `--template-id/--template-name`."
        )

    def _resolve_template_id(self, reference: _TemplateReference) -> tuple[int, str | None]:
        if reference.template_id is not None:
            return reference.template_id, reference.template_name
        if reference.template_name is None:
            raise ApiError("Template reference must include `id` or `name`")
        return self._template_id_by_name(reference.template_name), reference.template_name

    def _template_id_by_name(self, template_name: str) -> int:
        if self._template_index is None:
            index: dict[str, list[int]] = {}
            for template in self._template_service.list():
                template_name_value = str(getattr(template, "name", "")).strip()
                if not template_name_value:
                    continue
                template_id_raw = getattr(template, "id", None)
                if template_id_raw is None:
                    continue
                template_id = int(template_id_raw)
                index.setdefault(template_name_value, []).append(template_id)
            self._template_index = index

        template_ids = self._template_index.get(template_name, [])
        if not template_ids:
            raise ApiError(f"Template named '{template_name}' was not found")
        if len(template_ids) > 1:
            duplicates = ", ".join(str(value) for value in sorted(template_ids))
            raise ApiError(f"Template name '{template_name}' is ambiguous across IDs: {duplicates}")
        return template_ids[0]

    @staticmethod
    def _resolve_vm_name(effective: Mapping[str, Any]) -> str:
        vm_name_override = str(effective.get("vm_name", "")).strip()
        if vm_name_override:
            return vm_name_override
        entry_name = str(effective.get("name", "")).strip()
        if not entry_name:
            raise ApiError("Each VM entry must define `name` or `vm_name`")
        prefix = str(effective.get("name_prefix", "") or "")
        final_name = f"{prefix}{entry_name}"
        if not final_name.strip():
            raise ApiError("Resolved VM name cannot be empty")
        return final_name

    def _build_instantiate_override(self, effective: Mapping[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        resources_raw = effective.get("resources")
        if resources_raw is not None:
            resources = self._mapping(resources_raw, field="resources")
            if "cpu" in resources and resources["cpu"] is not None:
                payload["CPU"] = resources["cpu"]
            if "vcpu" in resources and resources["vcpu"] is not None:
                payload["VCPU"] = resources["vcpu"]
            if "ram" in resources and resources["ram"] is not None:
                payload["MEMORY"] = self._size_to_mb(resources["ram"], field="resources.ram")

        disk_entries: list[dict[str, Any]] = []
        if isinstance(resources_raw, Mapping) and resources_raw.get("disk") is not None:
            disk_entries.append(
                {
                    "DISK_ID": 0,
                    "SIZE": self._size_to_mb(resources_raw["disk"], field="resources.disk"),
                }
            )

        disks_raw = effective.get("disks")
        if disks_raw is not None:
            if not isinstance(disks_raw, list):
                raise ApiError("`disks` must be a list")
            for index, disk_raw in enumerate(disks_raw):
                disk = self._mapping(disk_raw, field=f"disks[{index}]")
                disk_entry: dict[str, Any] = {}
                for key, value in disk.items():
                    if str(key) == "size":
                        disk_entry["SIZE"] = self._size_to_mb(value, field=f"disks[{index}].size")
                        continue
                    disk_entry[str(key).upper()] = value
                disk_entries.append(disk_entry)
        if disk_entries:
            payload["DISK"] = disk_entries

        network_raw = effective.get("network")
        if network_raw is not None:
            if not isinstance(network_raw, list):
                raise ApiError("`network` must be a list")
            nic_entries: list[dict[str, Any]] = []
            for index, nic_raw in enumerate(network_raw):
                nic = self._mapping(nic_raw, field=f"network[{index}]")
                nic_entry: dict[str, Any] = {}
                for key, value in nic.items():
                    key_name = str(key)
                    if key_name == "network_name":
                        nic_entry["NETWORK"] = value
                        continue
                    nic_entry[key_name.upper()] = value
                nic_entries.append(nic_entry)
            if nic_entries:
                payload["NIC"] = nic_entries

        context_raw = effective.get("context")
        if context_raw is not None:
            context = self._mapping(context_raw, field="context")
            payload["CONTEXT"] = {str(key).upper(): value for key, value in context.items()}

        raw_template_raw = effective.get("raw_template")
        if raw_template_raw is not None:
            raw_template = self._mapping(raw_template_raw, field="raw_template")
            payload = self._deep_merge(payload, raw_template)

        return payload

    @staticmethod
    def _size_to_mb(raw: Any, *, field: str) -> int:
        if isinstance(raw, bool):
            raise ApiError(f"`{field}` cannot be a boolean")
        if isinstance(raw, (int, float)):
            if raw <= 0:
                raise ApiError(f"`{field}` must be greater than zero")
            return int(math.ceil(float(raw)))

        if not isinstance(raw, str):
            raise ApiError(f"`{field}` must be a number or size string")
        value = raw.strip()
        if not value:
            raise ApiError(f"`{field}` cannot be empty")
        if re.fullmatch(r"\d+(?:\.\d+)?", value):
            parsed = float(value)
            if parsed <= 0:
                raise ApiError(f"`{field}` must be greater than zero")
            return int(math.ceil(parsed))

        match = SIZE_PATTERN.match(value)
        if not match:
            raise ApiError(
                f"`{field}` must be raw MB or use Ki/Mi/Gi/Ti suffixes (for example `4Gi`)"
            )

        magnitude = float(match.group(1))
        unit = match.group(2).lower()
        multiplier = {
            "ki": 1.0 / 1024.0,
            "mi": 1.0,
            "gi": 1024.0,
            "ti": 1024.0 * 1024.0,
        }[unit]
        mb_value = magnitude * multiplier
        if mb_value <= 0:
            raise ApiError(f"`{field}` must be greater than zero")
        return int(math.ceil(mb_value))

    def _serialize_template(self, payload: Mapping[str, Any]) -> str:
        lines: list[str] = []
        for key, value in payload.items():
            lines.extend(self._serialize_assignment(str(key), value))
        return "\n".join(lines)

    def _serialize_assignment(self, key: str, value: Any) -> list[str]:
        if isinstance(value, Mapping):
            return [f"{key} = [ {self._serialize_inline_mapping(value)} ]"]
        if isinstance(value, list):
            if all(isinstance(item, Mapping) for item in value):
                return [f"{key} = [ {self._serialize_inline_mapping(item)} ]" for item in value]
            list_value = ", ".join(self._serialize_scalar(item) for item in value)
            return [f"{key} = [ {list_value} ]"]
        return [f"{key} = {self._serialize_scalar(value)}"]

    def _serialize_inline_mapping(self, mapping: Mapping[str, Any]) -> str:
        parts: list[str] = []
        for key, value in mapping.items():
            if isinstance(value, Mapping):
                rendered_value = json.dumps(dict(value), sort_keys=True)
                parts.append(f"{key} = {self._serialize_scalar(rendered_value)}")
            elif isinstance(value, list):
                rendered_value = json.dumps(value, sort_keys=True)
                parts.append(f"{key} = {self._serialize_scalar(rendered_value)}")
            else:
                parts.append(f"{key} = {self._serialize_scalar(value)}")
        return ", ".join(parts)

    @staticmethod
    def _serialize_scalar(value: Any) -> str:
        if value is None:
            rendered = ""
        elif isinstance(value, bool):
            rendered = "YES" if value else "NO"
        else:
            rendered = str(value)
        escaped = rendered.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'

    @classmethod
    def _deep_merge(cls, base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = copy.deepcopy(dict(base))
        for key, value in override.items():
            if key in result and isinstance(result[key], Mapping) and isinstance(value, Mapping):
                result[key] = cls._deep_merge(
                    dict(result[key]),
                    dict(value),
                )
                continue
            result[key] = copy.deepcopy(value)
        return result
