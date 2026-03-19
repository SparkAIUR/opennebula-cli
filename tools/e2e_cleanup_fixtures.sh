#!/usr/bin/env bash
set -euo pipefail

workspace="${1:?workspace required}"
opennebula_endpoint="${OPENNEBULA_ENDPOINT:-http://127.0.0.1:2633/RPC2}"
vm_prefix="${ONE_E2E_VM_PREFIX:-e2e-vm-}"
reset_base_fixtures="${ONE_E2E_RESET_BASE_FIXTURES:-0}"
template_name="${ONE_E2E_TEMPLATE_NAME:-e2e-alpine-lxc}"
image_name="${ONE_E2E_IMAGE_NAME:-e2e-alpine-lxc}"
vnet_name="${ONE_E2E_VNET_NAME:-e2e-vnet}"

mkdir -p "${workspace}"
log_file="${workspace}/cleanup.log"
summary_txt="${workspace}/cleanup-summary.txt"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${log_file}"
}

run_as_oneadmin() {
  local command="${1:?command required}"
  log "Running as oneadmin: ${command}"
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' ${command}" >>"${log_file}" 2>&1
}

list_vm_ids() {
  sudo -u oneadmin -H bash -lc \
    "ONE_XMLRPC='${opennebula_endpoint}' onevm list 2>/dev/null | awk 'NR > 1 && \$4 ~ /^${vm_prefix}/ { print \$1 }'"
}

wait_until_vm_gone() {
  local vm_id="${1:?vm id required}"
  local attempts=90
  local index=0
  while (( index < attempts )); do
    local state
    state="$(
      sudo -u oneadmin -H bash -lc \
        "ONE_XMLRPC='${opennebula_endpoint}' onevm show '${vm_id}' 2>/dev/null | awk -F': ' '/^STATE[[:space:]]*:/ { sub(/^ +/, \"\", \$2); print \$2; exit }'"
    )"
    if [[ -z "${state}" ]]; then
      return 0
    fi
    if [[ "${state}" == "DONE" || "${state}" == "FAILED" ]]; then
      return 0
    fi
    sleep 2
    index=$(( index + 1 ))
  done
  return 1
}

delete_if_exists() {
  local family="${1:?family required}"
  local name="${2:?name required}"
  if sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' one${family} show '${name}' >/dev/null 2>&1"; then
    run_as_oneadmin "one${family} delete '${name}'"
  fi
}

terminated=0
while IFS= read -r vm_id; do
  [[ -z "${vm_id}" ]] && continue
  run_as_oneadmin "onevm terminate --hard '${vm_id}'"
  wait_until_vm_gone "${vm_id}"
  terminated=$(( terminated + 1 ))
done < <(list_vm_ids)

if [[ "${reset_base_fixtures}" == "1" ]]; then
  delete_if_exists template "${template_name}"
  delete_if_exists image "${image_name}"
  delete_if_exists vnet "${vnet_name}"
fi

{
  printf 'terminated_vms=%s\n' "${terminated}"
  printf 'reset_base_fixtures=%s\n' "${reset_base_fixtures}"
} > "${summary_txt}"

log "Fixture cleanup completed successfully."
