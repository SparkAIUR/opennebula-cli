#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
assh_repo="${ASSH_REPO:-/Volumes/S0/github/_personal/assh}"
target_alias="${ONE_E2E_TARGET_ALIAS:-opennebula-e2e}"
target_endpoint="${ONE_E2E_TARGET_ENDPOINT:-root@192.237.244.107}"
remote_root="${ONE_E2E_REMOTE_ROOT:-/dev/shm/opennebula-cli-e2e}"
mode="${ONE_E2E_MODE:-probe}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact_root="${repo_root}/refs/tasks/e2e/${timestamp}"

mkdir -p "${artifact_root}"

assh() {
  (
    cd "${assh_repo}"
    uv run assh "$@"
  )
}

assh init >/dev/null
assh target add "${target_alias}" "${target_endpoint}" --scope repo >/dev/null
assh run "mkdir -p '${remote_root}/workspace'" --target "${target_alias}" >/dev/null
assh push "${repo_root}/tools/e2e_bootstrap_opennebula.sh" "${remote_root}/e2e_bootstrap_opennebula.sh" --target "${target_alias}" --mode 755 >/dev/null

set +e
assh run "bash '${remote_root}/e2e_bootstrap_opennebula.sh' '${remote_root}/workspace' '${mode}'" --target "${target_alias}" | tee "${artifact_root}/assh-run.txt"
run_exit="${PIPESTATUS[0]}"
set -e

assh fetch "${remote_root}/workspace/probe.json" "${artifact_root}/probe.json" --target "${target_alias}" >/dev/null
assh fetch "${remote_root}/workspace/status.env" "${artifact_root}/status.env" --target "${target_alias}" >/dev/null
assh fetch "${remote_root}/workspace/summary.txt" "${artifact_root}/summary.txt" --target "${target_alias}" >/dev/null
assh fetch "${remote_root}/workspace/bootstrap.log" "${artifact_root}/bootstrap.log" --target "${target_alias}" >/dev/null

printf '%s\n' "${artifact_root}"
exit "${run_exit}"
