# AGENTS.md

## Project identity

- Repo: `https://github.com/SparkAIUR/opennebula-cli`
- PyPI package: `opennebula-cli`
- Import package: `opennebula_cli`
- Current public release: `7.0.0`
- Compatibility target for this release: OpenNebula `7.0.x`

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

## Validation state for `7.0.0`

This release was validated against a disposable OpenNebula CE `7.0.x` environment on Ubuntu `24.04` with a localhost `lxc` host.

Live-validated:

- read-only `list` and `show` for `vm`, `host`, `image`, `template`, `vnet`, `datastore`, and `cluster`
- disposable mutation flows for:
  - `template instantiate`
  - `vm poweroff --wait`

Still implemented but not a release blocker for live mutation validation:

- `host flush`
- `image delete`
- `template delete`

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
uv run python tools/check_release_version.py --tag v7.0.0
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
bash tools/e2e_run_live.sh
```

## Near-term roadmap

1. Maintain `7.0.x` compatibility quality and improve remaining live mutation coverage.
2. Expand Wave 2 beyond read-only commands.
3. Add Wave 3 and Wave 4 command families.
4. Introduce the OneFlow plugin boundary and first-party plugin support.
