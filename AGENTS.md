# AGENTS.md

## Project identity

- Repo: `https://github.com/SparkAIUR/opennebula-cli`
- PyPI package: `opennebula-cli`
- Import package: `opennebula_cli`
- Target OpenNebula line: `7.0.x`
- Current bootstrap package version: `0.1.0`

## Mission

Build a modern Python CLI and SDK that reaches practical parity with the official OpenNebula CLI while remaining easy to package, test, extend, and embed.

## Primary architecture

The repo is organized into these layers:

1. `cli/`
   Canonical `one <resource> <verb>` Typer application and Wave 1 compatibility shims.
2. `config/` and `auth/`
   Resolution of profiles, environment variables, auth files, and CLI overrides.
3. `transports/`
   PyONE-first XML-RPC transport plus raw XML-RPC fallback.
4. `services/`
   Reusable typed operations consumed by both CLI and SDK.
5. `sdk/`
   Public `OneClient`, exceptions, and normalized models.
6. `renderers/`
   Human and machine output handling.
7. `waiters/`
   Polling-based wait support for long-running operations.
8. `registry/` and `catalogs/`
   Versioned command metadata and parity tracking.
9. `plugins/`
   Plugin protocol and future extension points.
10. `dev/`
    Local maintainer tooling such as the private context store backend.

## Current milestone

The first milestone is `Foundation + Wave 1`:

- packaging and CI
- runtime config/auth
- transport and exception normalization
- SDK base
- renderers and waiters
- `vm`, `host`, `image`, and `template` families

The current extension milestone adds:

- standardized help examples for every implemented subcommand
- Wave 2 read-only families: `vnet`, `datastore`, `cluster`
- private live-readonly capture and import tooling

## Canonical rules

- Prefer compatibility over novelty.
- Keep CLI behavior thin; put reusable logic in services.
- Keep transport-specific details out of the public SDK.
- Do not require `refs/*` for public onboarding.
- Treat machine-readable output as deterministic contract surface.
- Release tags must match `project.version` exactly.
- `0.1.0` is a bootstrap release; later public versions will mirror OpenNebula compatibility.

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
- `refs/tasks/live-capture/`

## Worker responsibilities

When parallelizing work, keep write ownership disjoint:

- Docs worker:
  - `docs/**`
  - `README.md`
  - `AGENTS.md`
  - `LICENSE`
- Core runtime worker:
  - `src/opennebula_cli/{auth,config,transports,sdk,services,renderers,waiters}/**`
- CLI/parity worker:
  - `src/opennebula_cli/{cli,compat,registry,catalogs}/**`
- Quality worker:
  - `tests/**`
  - `.github/workflows/**`
  - `tools/**`

Workers must not revert unrelated changes and must adapt to concurrent edits.

## Local maintainer workflow

```bash
uv sync --group dev
uv run one --help
uv run pytest
uv run python tools/check_catalog_schema.py
uv run python tools/check_release_version.py --tag v0.1.0
uv build
```

Read-only live observation workflow:

```bash
tools/capture_live_readonly.sh --write-artifact > /tmp/opennebula-capture.jsonl
uv run python tools/import_live_capture.py import --input /tmp/opennebula-capture.jsonl
```

Private context store workflow:

```bash
uv run python tools/context_store.py init
uv run python tools/context_store.py add decision architecture "Initial transport choice" "Use PyONE first" "Raw XML-RPC remains as a fallback."
uv run python tools/context_store.py export-md
```

## Near-term roadmap

1. Publish the bootstrap `0.1.0` package release.
2. Run VM-based OpenNebula `7.0.x` live validation.
3. Bump the package to `7.0.0` and switch to compatibility-mirrored releases.
4. Expand parity into identity, policy, and plugin flows.
