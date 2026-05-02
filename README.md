# opennebula-cli

`opennebula-cli` is a CLI-first Python toolkit for OpenNebula `7.0.x`.

It is built for operators, platform teams, CI/CD pipelines, and Python automation that need a modern interface to OpenNebula without giving up the familiar `onevm`-style workflows.

## Why use it

- Canonical command tree for automation: `one <resource> <verb>`
- Compatibility shims for existing operator habits: `onevm`, `onehost`, `oneimage`, `onetemplate`, `onevnet`, `onedatastore`, `onecluster`
- Typed SDK for Python integrations under `opennebula_cli.sdk`
- Deterministic machine-readable output for scripts and pipelines
- Live-validated against a disposable OpenNebula CE `7.0.x` deployment before release

## Install

Install the release that matches the OpenNebula compatibility line you want:

```bash
uv tool install opennebula-cli==7.0.2
```

Run it without installing permanently:

```bash
uvx --from opennebula-cli==7.0.2 one --help
```

For local development:

```bash
uv sync --group dev
uv run one --help
uv run onevm --help
```

## Authenticate safely

Recommended for operators and CI:

```bash
mkdir -p "$HOME/.one"
chmod 700 "$HOME/.one"
printf 'oneadmin:super-secret-token\n' > "$HOME/.one/one_auth"
chmod 600 "$HOME/.one/one_auth"

export ONE_XMLRPC="https://opennebula.example.com/RPC2"
export ONE_AUTH="$HOME/.one/one_auth"
```

Avoid exporting raw `user:secret` values directly in shell history unless you are intentionally using `literal:` for a short-lived task.

Supported auth forms:

- `ONE_AUTH=/path/to/authfile`
- `ONE_AUTH=file:/path/to/authfile`
- `ONE_AUTH=literal:user:secret`
- `one --user oneadmin ...` with a secure password prompt

## Command model

Canonical commands:

```bash
one [GLOBAL OPTIONS] <resource> <verb> [RESOURCE ARGS] [RESOURCE OPTIONS]
```

Compatibility commands:

```bash
one<resource> [GLOBAL OPTIONS] <verb> [RESOURCE ARGS] [RESOURCE OPTIONS]
```

Examples:

```bash
one vm list
one --output json vm list
one --profile prod --no-pager template show 24

onevm list
onevm --output json list
onecluster --profile prod show 0
```

Global options such as `--output`, `--profile`, `--endpoint`, and `--auth` belong before the resource verb on the canonical CLI and before the verb on compatibility wrappers.

## Quick examples

Human-readable operator output:

```bash
one vm list
one template show 24
onehost show 0
```

Machine-readable automation output:

```bash
one --output json vm list
one --output yaml template show 24
onevnet --output json list
```

CI/CD example:

```bash
VM_ID="$(
  one --output json vm list \
    | jq -r '.[] | select(.name == "build-runner") | .id'
)"

one --output json vm show "$VM_ID"
```

## New in `7.0.2`: workflow + state/context operations

This release adds an end-to-end workflow system for template rendering and VM provisioning:

- `one workflow template init|render|import|apply`
- `one workflow vm init` for single VM initialization
- `one workflow vm apply` for bulk initialization from a list
- cloud-init helper functions for Jinja templates:
  - `read_file(path)`
  - `read_file_b64(path)`
  - `fetch_url(url, method=..., headers=..., params=..., body=..., timeout=...)`

This release also adds local state and context management:

- `one state lock enable|disable`
- `one state ctx set|use|get|list|show|validate`
- auth-config aware context switching with `OPENNEBULA_CLI_AUTH_CONFIG`

Template workflow example:

```bash
one workflow template init ./openclaw-workflow
one workflow template render ./openclaw-workflow/workflow.yaml \
  --vars-file ./openclaw-workflow/vars.example.yaml
one workflow template import ./openclaw-workflow/workflow.yaml \
  --vars-file ./openclaw-workflow/vars.example.yaml
```

Bulk VM initialization example:

```bash
one workflow vm apply docs/examples/05-vm-init/bulk-init.yaml \
  --wait-ready \
  --set global.name_prefix=user-vm-
```

Single VM initialization example:

```bash
one workflow vm init docs/examples/05-vm-init/bulk-init.yaml --vm-name alice
```

Read the full guide:

- `docs/workflows-vm-templates.mdx`
- `docs/examples/README.md`

## Supported command families

Wave 1:

- `vm`: `list`, `show`, `disk-list`, `disk-attach`, `disk-detach`, `recover`, `reboot`, `reboot-hard`, `resume`, `wait`, `poweroff`, `poweroff-hard`
- `host`: `list`, `show`, `flush`
- `image`: `list`, `show`, `owner`, `delete`
- `template`: `list`, `show`, `delete`, `instantiate`

Wave 2 read-only:

- `vnet`: `list`, `show`
- `datastore`: `list`, `show`
- `cluster`: `list`, `show`

Workflow automation:

- `workflow template`: `init`, `render`, `import`, `apply`
- `workflow vm`: `init`, `apply`

Recovery and agent support:

- `raw`: guarded `call`
- `agents`: print the AI-agent usage guide
- `state`: local lock and context management commands
- `version`: print app version and git hash

## Validation status for `7.0.2`

`7.0.2` targets OpenNebula `7.0.x` and maintains the compatibility baseline validated against:

- Ubuntu `24.04`
- OpenNebula CE `7.0.x`
- single-node frontend
- localhost `lxc` host

Live-validated surfaces:

- read-only `list` and `show` coverage for `vm`, `host`, `image`, `template`, `vnet`, `datastore`, and `cluster`
- disposable mutation validation for:
  - `template instantiate`
  - `vm poweroff --wait`

Implemented but not yet fully live-validated on disposable fixtures:

- `host flush`
- `image delete`
- `template delete`

Workflow and state/context additions are validated through unit/integration test coverage and runnable docs examples.

## Configuration and profiles

Configuration precedence:

1. CLI flags
2. selected profile
3. environment variables
4. defaults

Key environment variables:

- `ONE_XMLRPC`
- `ONE_AUTH`
- `ONE_XMLRPC_TIMEOUT`
- `ONE_CERT_DIR`
- `ONE_DISABLE_SSL_VERIFY`
- `ONE_PAGER`
- `ONE_LISTCONF`
- `ONE_POOL_PAGE_SIZE`

Profile config lives at the platform config directory for `opennebula-cli`, for example:

- macOS: `~/Library/Application Support/opennebula-cli/config.toml`
- Linux: `~/.config/opennebula-cli/config.toml`

Example:

```toml
default_profile = "prod"

[profiles.prod]
endpoint = "https://opennebula.example.com/RPC2"
auth = "file:/home/ops/.one/prod_auth"
output = "table"
timeout = 60
verify_ssl = true
```

## SDK

```python
from opennebula_cli.sdk import OneClient

client = OneClient.from_env()

for vm in client.vm.list():
    print(vm.id, vm.name, vm.state)
```

## Live capture for private environments

When credentials cannot be shared, use the read-only capture workflow:

```bash
tools/capture_live_readonly.sh --write-artifact > /tmp/opennebula-capture.jsonl
uv run python tools/import_live_capture.py import --input /tmp/opennebula-capture.jsonl
```

The capture path:

- only runs allowlisted `--help`, `list`, and `show` commands
- never runs create, update, delete, or lifecycle operations
- redacts endpoints, hostnames, IPs, MACs, and secret-like fields
- writes private artifacts under `refs/tasks/live-capture/`

## Remote E2E harness

The repo includes an `assh`-backed workflow for disposable OpenNebula validation VMs:

```bash
ONE_E2E_TARGET_ALIAS=opennebula-e2e \
ONE_E2E_TARGET_ENDPOINT=root@vm.example.com \
ONE_E2E_REMOTE_ROOT=/mnt/opennebula-cli-e2e \
ONE_E2E_MODE=manual-frontend \
ONE_E2E_VALIDATE_LOCAL=1 \
bash tools/e2e_run_live.sh
```

That flow:

- bootstraps a disposable OpenNebula CE frontend
- seeds `e2e-*` fixtures
- runs live read-only and mutation E2E from the current checkout
- imports sanitized read-only observations
- cleans up disposable `e2e-vm-*` VMs afterward

## Staging-lab bootstrap

For multi-node staging environments, this repo also ships simple bootstrap helpers:

```bash
export STAGING_FRONTEND=frontend.example.com
export STAGING_HYPERVISORS=hv-01.example.com,hv-02.example.com,hv-03.example.com,hv-04.example.com
export STAGING_HYPERVISOR_NAMES=lab-hv-01,lab-hv-02,lab-hv-03,lab-hv-04

bash tools/staging_bootstrap_cluster.sh gather
bash tools/staging_bootstrap_cluster.sh prepare
bash tools/staging_bootstrap_cluster.sh install-common
bash tools/staging_validate_cluster.sh capture
```

These scripts intentionally cover the repeatable host-preparation and read-only validation layers. Higher-level OpenNebula, Ceph, and Omni service bootstrap remains environment-specific and is documented in the consuming repos.

## Versioning and releases

Public package versions now mirror the OpenNebula compatibility target.

- current release: `7.0.2`
- compatibility target: OpenNebula `7.0.x`
- historical bootstrap release: `0.1.0`

Release tags must always match `project.version` exactly:

```bash
uv run python tools/check_release_version.py --tag v7.0.2
git tag -a v7.0.2 -m "Release v7.0.2"
```

## Docs

Tracked public documentation lives in [`docs/`](docs/):

- `docs/index.mdx`
- `docs/getting-started.mdx`
- `docs/command-model.mdx`
- `docs/workflows-vm-templates.mdx`
- `docs/configuration.mdx`
- `docs/sdk.mdx`
- `docs/testing.mdx`
- `docs/parity-roadmap.mdx`
- `docs/contributing.mdx`

## Development checks

```bash
uv run ruff check .
uv run mypy src tests tools
uv run pytest
uv run python tools/check_catalog_schema.py
uv build
```

## License

Apache-2.0
