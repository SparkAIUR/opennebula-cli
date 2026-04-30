"""Markdown guide printed by ``one agents``."""

AGENTS_GUIDE = """# opennebula-cli Agent Guide

## Command Surface

Use the canonical CLI form:

```bash
one [GLOBAL OPTIONS] <resource> <verb> [RESOURCE ARGS] [RESOURCE OPTIONS]
```

Global options belong before the resource:

```bash
one --output json vm list
one --profile prod vm show 42 --full
```

Compatibility wrappers use global options before the verb:

```bash
onevm --output json list
oneimage --profile prod show 18
```

If an incident note says `opennebula vm ...`, read it as `one vm ...`.

## CSI Recovery Workflow

Prefer JSON for support bundles and automation:

```bash
one --output json vm show 42 --full
one --output json image show 18 --full
one --output json image owner 18
one --output json vm disk-list 42
```

Use disk IDs from `vm disk-list` when detaching stale attachments:

```bash
one --output json vm disk-detach 42 --disk-id 1
one --output json vm wait 42 --state ACTIVE --lcm-state RUNNING --timeout 10m --no-progress
```

Recover stuck VM operations only after host-level checks confirm the correct outcome:

```bash
one --output json vm recover 42 --retry
one --output json vm recover 42 --success
one --output json vm recover 42 --failure
```

## Boundaries

This CLI talks to OpenNebula XML-RPC. It does not run host commands such as
`virsh domblklist`; use the VM ID, VM name, disk ID, and target device details
from JSON output when coordinating host-level checks.

`one raw call` is an explicit escape hatch. Use it only when typed commands do
not cover the operation, keep arguments in JSON arrays, and include
`--i-understand-this-is-unsafe`.
"""
