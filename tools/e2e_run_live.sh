#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
assh_repo="${ASSH_REPO:-/Volumes/S0/github/_personal/assh}"
target_alias="${ONE_E2E_TARGET_ALIAS:-opennebula-e2e}"
target_endpoint="${ONE_E2E_TARGET_ENDPOINT:-}"
remote_root="${ONE_E2E_REMOTE_ROOT:-/dev/shm/opennebula-cli-e2e}"
mode="${ONE_E2E_MODE:-probe}"
frontend_host="${ONE_E2E_FRONTEND_HOST:-localhost}"
validate_local="${ONE_E2E_VALIDATE_LOCAL:-0}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact_root="${repo_root}/refs/tasks/e2e/${timestamp}"

mkdir -p "${artifact_root}"

assh() {
  (
    cd "${assh_repo}"
    uv run assh "$@"
  )
}

free_port() {
  python - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

cleanup() {
  if [[ -n "${ssh_tunnel_pid:-}" ]]; then
    kill "${ssh_tunnel_pid}" >/dev/null 2>&1 || true
    wait "${ssh_tunnel_pid}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${temp_auth_file:-}" && -f "${temp_auth_file}" ]]; then
    rm -f "${temp_auth_file}"
  fi
}

trap cleanup EXIT

if [[ -z "${target_endpoint}" ]]; then
  printf 'ONE_E2E_TARGET_ENDPOINT must be set or an assh target with alias %s must already exist.\n' "${target_alias}" >&2
fi

assh init >/dev/null
if [[ -n "${target_endpoint}" ]]; then
  assh target add "${target_alias}" "${target_endpoint}" --scope repo >/dev/null
fi
assh run "mkdir -p '${remote_root}/workspace'" --target "${target_alias}" >/dev/null
assh push "${repo_root}/tools/e2e_bootstrap_opennebula.sh" "${remote_root}/e2e_bootstrap_opennebula.sh" --target "${target_alias}" --mode 755 >/dev/null
assh push "${repo_root}/tools/e2e_seed_fixtures.sh" "${remote_root}/e2e_seed_fixtures.sh" --target "${target_alias}" --mode 755 >/dev/null
assh push "${repo_root}/tools/e2e_cleanup_fixtures.sh" "${remote_root}/e2e_cleanup_fixtures.sh" --target "${target_alias}" --mode 755 >/dev/null

set +e
assh run "OPENNEBULA_SERIES='7.0' FRONTEND_HOSTNAME='${frontend_host}' bash '${remote_root}/e2e_bootstrap_opennebula.sh' '${remote_root}/workspace' '${mode}'" --target "${target_alias}" | tee "${artifact_root}/assh-run.txt"
run_exit="${PIPESTATUS[0]}"
set -e

assh fetch "${remote_root}/workspace/probe.json" "${artifact_root}/probe.json" --target "${target_alias}" >/dev/null
assh fetch "${remote_root}/workspace/status.env" "${artifact_root}/status.env" --target "${target_alias}" >/dev/null
assh fetch "${remote_root}/workspace/summary.txt" "${artifact_root}/summary.txt" --target "${target_alias}" >/dev/null
assh fetch "${remote_root}/workspace/bootstrap.log" "${artifact_root}/bootstrap.log" --target "${target_alias}" >/dev/null
for optional_file in \
  remote-commands.txt \
  service-status.txt \
  package-versions.txt \
  onehost-list.txt \
  oneuser-show.txt \
  frontend-facts.json \
  onecluster-list.txt \
  onedatastore-list.txt \
  onevnet-list.txt \
  oneimage-list.txt \
  onetemplate-list.txt \
  onevm-list.txt
do
  set +e
  assh fetch "${remote_root}/workspace/${optional_file}" "${artifact_root}/${optional_file}" --target "${target_alias}" >/dev/null
  set -e
done
set +e
assh fetch "/var/log/one/oned.log" "${artifact_root}/oned.log" --target "${target_alias}" >/dev/null
set -e

if [[ "${run_exit}" -eq 0 && "${mode}" != "probe" && "${validate_local}" == "1" ]]; then
  set +e
  assh run "bash '${remote_root}/e2e_cleanup_fixtures.sh' '${remote_root}/workspace'" --target "${target_alias}" | tee "${artifact_root}/assh-cleanup-before.txt"
  cleanup_before_exit="${PIPESTATUS[0]}"
  set -e
  if [[ "${cleanup_before_exit}" -ne 0 ]]; then
    exit "${cleanup_before_exit}"
  fi

  set +e
  assh run "bash '${remote_root}/e2e_seed_fixtures.sh' '${remote_root}/workspace'" --target "${target_alias}" | tee "${artifact_root}/assh-seed.txt"
  seed_exit="${PIPESTATUS[0]}"
  set -e
  set +e
  assh fetch "${remote_root}/workspace/seed.log" "${artifact_root}/seed.log" --target "${target_alias}" >/dev/null
  assh fetch "${remote_root}/workspace/seed-summary.txt" "${artifact_root}/seed-summary.txt" --target "${target_alias}" >/dev/null
  assh fetch "${remote_root}/workspace/fixtures.env" "${artifact_root}/fixtures.env" --target "${target_alias}" >/dev/null
  assh fetch "${remote_root}/workspace/fixtures.json" "${artifact_root}/fixtures.json" --target "${target_alias}" >/dev/null
  set -e
  if [[ "${seed_exit}" -ne 0 ]]; then
    exit "${seed_exit}"
  fi

  temp_auth_file="$(mktemp)"
  if [[ -z "${target_endpoint}" ]]; then
    printf 'ONE_E2E_TARGET_ENDPOINT must be set for local validation.\n' >&2
    exit 65
  fi
  ssh -o StrictHostKeyChecking=accept-new "${target_endpoint}" "cat /var/lib/one/.one/one_auth" > "${temp_auth_file}"
  chmod 0600 "${temp_auth_file}"

  local_port="$(free_port)"
  ssh -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new -N -L "${local_port}:127.0.0.1:2633" "${target_endpoint}" &
  ssh_tunnel_pid="$!"
  sleep 3

  (
    cd "${repo_root}"
    export ONE_XMLRPC="http://127.0.0.1:${local_port}/RPC2"
    export ONE_AUTH="${temp_auth_file}"
    uv run pytest tests/e2e/test_live_opennebula.py tests/e2e/test_live_mutation_opennebula.py -q
  ) | tee "${artifact_root}/pytest-live.txt"
  pytest_exit="${PIPESTATUS[0]}"

  (
    cd "${repo_root}"
    export ONE_XMLRPC="http://127.0.0.1:${local_port}/RPC2"
    export ONE_AUTH="${temp_auth_file}"
    bash tools/capture_live_readonly.sh --write-artifact > "${artifact_root}/live-capture.jsonl" 2> "${artifact_root}/live-capture.stderr"
    uv run python tools/import_live_capture.py import --input "${artifact_root}/live-capture.jsonl" > "${artifact_root}/live-capture-summary.txt"
  )
  capture_exit=$?

  if [[ "${pytest_exit}" -ne 0 || "${capture_exit}" -ne 0 ]]; then
    printf 'live_validation_failed\n' > "${artifact_root}/live-validation.status"
  else
    printf 'live_validation_passed\n' > "${artifact_root}/live-validation.status"
  fi

  set +e
  assh run "bash '${remote_root}/e2e_cleanup_fixtures.sh' '${remote_root}/workspace'" --target "${target_alias}" | tee "${artifact_root}/assh-cleanup-after.txt"
  cleanup_after_exit="${PIPESTATUS[0]}"
  set -e
  set +e
  assh fetch "${remote_root}/workspace/cleanup.log" "${artifact_root}/cleanup.log" --target "${target_alias}" >/dev/null
  assh fetch "${remote_root}/workspace/cleanup-summary.txt" "${artifact_root}/cleanup-summary.txt" --target "${target_alias}" >/dev/null
  set -e

  if [[ "${pytest_exit}" -ne 0 ]]; then
    exit "${pytest_exit}"
  fi
  if [[ "${capture_exit}" -ne 0 ]]; then
    exit "${capture_exit}"
  fi
  if [[ "${cleanup_after_exit}" -ne 0 ]]; then
    exit "${cleanup_after_exit}"
  fi
fi

printf '%s\n' "${artifact_root}"
exit "${run_exit}"
