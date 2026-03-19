# opennebula-cli

`opennebula-cli` is a modern Python CLI and SDK for OpenNebula `7.0.x`.

It preserves familiar workflows such as `onevm`, `onehost`, `oneimage`, and `onetemplate`, while also exposing a canonical `one <resource> <verb>` command tree and a typed Python SDK built for remote use from laptops, CI, and other automation systems.

## Quickstart

Below is the fastest way to get started using this tool.

```bash
uv tool install opennebula-cli

export ONE_XMLRPC="http://127.0.0.1:2633/RPC2"
export ONE_AUTH="oneadmin:password-for-auth"

onevm list
```

## Status

This repository is in active bootstrap. The current milestone focuses on:

- `uv`-managed packaging and contributor workflow
- typed config, auth, transport, and SDK foundations
- Wave 1 resource families:
  - `onevm`
  - `onehost`
  - `oneimage`
  - `onetemplate`
- Wave 2 read-only families:
  - `onevnet`
  - `onedatastore`
  - `onecluster`
- public Mintlify docs under `docs/`
- local-only maintainer context tooling under `refs/`

## Goals

- Behavioral parity with the official OpenNebula CLI for OpenNebula `7.0.x`
- Strongly typed Python SDK under `opennebula_cli.sdk`
- Compatibility shims for official command families
- Deterministic machine-readable output modes
- Plugin-ready architecture for future OneFlow and ecosystem extensions

## Install

### Local development

```bash
uv sync --group dev
uv run one --help
uv run onevm --help
```

### Build

```bash
uv build
```

## Quick start

```bash
export ONE_XMLRPC=https://opennebula.example.com/RPC2
export ONE_AUTH=$HOME/.one/one_auth

uv run one vm list
uv run onevm show 42
uv run one image list --output json
uv run one vnet list --output json
```

## Help examples

Every implemented subcommand includes 1-2 concrete usage examples in `--help`.

```bash
uv run one vm list --help
uv run one template instantiate --help
```

## Live read-only capture

When live credentials cannot be shared, use the private capture tooling to emit sanitized read-only observations:

```bash
tools/capture_live_readonly.sh --write-artifact > /tmp/opennebula-capture.jsonl
uv run python tools/import_live_capture.py import --input /tmp/opennebula-capture.jsonl
```

The capture path:

- only executes allowlisted `--help`, `list`, and `show` commands
- never executes create, update, delete, or lifecycle mutations
- redacts endpoints, hostnames, IPs, MACs, and secret-like fields
- writes private artifacts under `refs/tasks/live-capture/`

## SDK

```python
from opennebula_cli.sdk import OneClient

client = OneClient.from_env()
for vm in client.vm.list():
    print(vm.id, vm.name, vm.state)
```

## Repo layout

- `src/opennebula_cli/`: application and SDK code
- `docs/`: public Mintlify documentation
- `tests/`: unit and future parity/contract coverage
- `tools/`: repo maintenance helpers
- `refs/`: private local maintainer workspace, ignored by git

## Documentation

Public docs are tracked in [`docs/`](docs/). The main entrypoints are:

- `docs/index.mdx`
- `docs/getting-started.mdx`
- `docs/architecture.mdx`
- `docs/sdk.mdx`
- `docs/testing.mdx`
- `docs/contributing.mdx`

## Development checks

```bash
uv run ruff check .
uv run mypy src
uv run pytest
uv run python tools/check_catalog_schema.py
```

## License

Apache-2.0
