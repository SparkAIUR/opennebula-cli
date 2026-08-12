# AGENTS.md

## Project identity

- Repo: `https://github.com/SparkAIUR/opennebula-cli`
- PyPI package: `opennebula-cli`
- Import package: `opennebula_cli`
- Current public release: `7.4.0`
- Compatibility targets: OpenNebula `7.4.x` and retained `7.0.x`

## Mission

Ship a CLI-first, automation-friendly OpenNebula toolkit that keeps official workflows recognizable while making scripting, packaging, testing, and Python integration substantially easier.

The CLI is the primary user surface. The SDK exists so the CLI and external Python automation share the same typed service layer instead of shelling out to subprocesses.

## Primary architecture

The repo is organized into these layers:

1. `cli/`
   Typer command tree, error handling, state construction, and help/example formatting.
2. `compat/`
   Official-style wrappers such as `onevm` and `onevnet`.
3. `auth/` and `config/`
   Auth resolution, profile loading, env precedence, and runtime configuration.
4. `transports/`
   PyONE-first XML-RPC transport with raw XML-RPC fallback.
5. `services/`
   Reusable typed OpenNebula operations shared by CLI and SDK.
6. `sdk/`
   Public `OneClient`, exceptions, and normalized models.
7. `renderers/`
   Human and machine output handling.
8. `waiters/`
   Polling support for lifecycle operations.
9. `registry/` and `catalogs/`
   Versioned command metadata and parity inventory.
10. `plugins/`
    Future extension boundary.
11. `dev/`
    Private maintainer tooling such as the context store and live capture support.

## CLI contract

Canonical syntax:

```bash
one [GLOBAL OPTIONS] <resource> <verb> [RESOURCE ARGS] [RESOURCE OPTIONS]
```

Compatibility syntax:

```bash
one<resource> [GLOBAL OPTIONS] <verb> [RESOURCE ARGS] [RESOURCE OPTIONS]
```

Important rule:

- global options belong before the resource verb on `one`
- global options belong before the verb on compatibility wrappers

Examples:

```bash
one --output json vm list
one --profile prod template show 24
onevm --output json list
onecluster --profile prod show 0
```

## Current implemented scope

Wave 1:

- `vm`: `list`, `show`, `poweroff`
- `host`: `list`, `show`, `flush`
- `image`: `list`, `show`, `delete`
- `template`: `list`, `show`, `delete`, `instantiate`

Wave 2 read-only:

- `vnet`: `list`, `show`
- `datastore`: `list`, `show`
- `cluster`: `list`, `show`

Workflow automation:

- `workflow template`: `init`, `render`, `import`, `apply`
- `workflow vm`: `init`, `apply`

## Validation state for `7.4.0`

This release was validated read-only against DR OpenNebula `7.4.0` through both PyONE and raw XML-RPC. It also passed a local dual-backend `7.0.2` protocol fixture, generated bindings from the OpenNebula `7.4.0` source schema, and a local OneForm REST contract fixture.

DR read-only validated:

- read-only `list` and `show` for `vm`, `host`, `image`, `template`, `vnet`, `datastore`, and `cluster`
- ACL and OneFlow list operations
- authenticated server version negotiation and version-profile selection

Historical disposable 7.0 mutation evidence remains available for `template instantiate` and `vm poweroff --wait`. No production mutation was performed for 7.4. OneForm was not configured in DR, so its 7.4 routes were validated locally only.

Still requiring disposable 7.4 mutation validation before environment enablement:

- `host flush`
- `image delete`
- `template delete`
- VM exec/retry/cancel and VM-group operations
- cluster optimization plans and group VLAN operations

## Canonical repo rules

- Prefer compatibility over novelty.
- Keep CLI handlers thin; reusable logic belongs in services.
- Keep transport-specific details out of public SDK types.
- Do not require `refs/*` for public onboarding.
- Treat machine-readable output as contract surface.
- Keep live capture tooling read-only and aggressively redacted.
- Keep disposable fixture namespaced under `e2e-*`.
- Do not mutate or clean up non-`e2e-*` resources in the remote E2E workflow.
- Release tags must match `project.version` exactly.
- Public package versions mirror OpenNebula compatibility targets.

## Docs map

Public docs:

- `docs/index.mdx`
- `docs/getting-started.mdx`
- `docs/architecture.mdx`
- `docs/command-model.mdx`
- `docs/workflows-vm-templates.mdx`
- `docs/configuration.mdx`
- `docs/sdk.mdx`
- `docs/testing.mdx`
- `docs/parity-roadmap.mdx`
- `docs/contributing.mdx`

Private local docs:

- `refs/RULES.md`
- `refs/KB.md`
- `refs/docs/ctx/context.db`
- `refs/tasks/e2e/`
- `refs/tasks/live-capture/`

## Worker responsibilities

When parallelizing work, keep ownership disjoint:

- Docs worker:
  - `docs/**`
  - `README.md`
  - `AGENTS.md`
- Core runtime worker:
  - `src/opennebula_cli/{auth,config,transports,sdk,services,renderers,waiters}/**`
- CLI/parity worker:
  - `src/opennebula_cli/{cli,compat,registry,catalogs}/**`
- Quality and tooling worker:
  - `tests/**`
  - `.github/workflows/**`
  - `tools/**`

Workers must adapt to concurrent edits and must not revert unrelated changes.

## Local maintainer workflow

```bash
uv sync --group dev
uv run one --help
uv run pytest
uv run python tools/check_catalog_schema.py
uv run python tools/check_command_coverage.py
uv run python tools/check_release_version.py --tag v7.4.0
uv build
```

Read-only live observation:

```bash
tools/capture_live_readonly.sh --write-artifact > /tmp/opennebula-capture.jsonl
uv run python tools/import_live_capture.py import --input /tmp/opennebula-capture.jsonl
```

Remote live validation:

```bash
ONE_E2E_TARGET_ALIAS=opennebula-e2e \
ONE_E2E_TARGET_ENDPOINT=root@vm.example.com \
ONE_E2E_REMOTE_ROOT=/mnt/opennebula-cli-e2e \
ONE_E2E_MODE=manual-frontend \
ONE_E2E_VALIDATE_LOCAL=1 \
OPENNEBULA_SERIES=7.4 \
bash tools/e2e_run_live.sh
```

## Near-term roadmap

1. Add disposable 7.4 mutation evidence for new typed operations.
2. Validate OneForm against a configured disposable 7.4 service.
3. Deepen typed models for broad official compatibility commands.
4. Maintain the retained 7.0 profile while following future upstream profiles.
