#!/usr/bin/env bash
set -euo pipefail

workspace="${1:?workspace required}"
mode="${2:-probe}"
opennebula_series="${OPENNEBULA_SERIES:-7.0}"
ubuntu_series="${UBUNTU_SERIES:-24.04}"
frontend_host="${FRONTEND_HOSTNAME:-localhost}"
opennebula_endpoint="${OPENNEBULA_ENDPOINT:-http://127.0.0.1:2633/RPC2}"

mkdir -p "${workspace}"
log_file="${workspace}/bootstrap.log"
probe_json="${workspace}/probe.json"
status_env="${workspace}/status.env"
summary_txt="${workspace}/summary.txt"
service_status_txt="${workspace}/service-status.txt"
package_versions_txt="${workspace}/package-versions.txt"
onehost_list_txt="${workspace}/onehost-list.txt"
oneuser_show_txt="${workspace}/oneuser-show.txt"
frontend_facts_json="${workspace}/frontend-facts.json"
onecluster_list_txt="${workspace}/onecluster-list.txt"
onedatastore_list_txt="${workspace}/onedatastore-list.txt"
onevnet_list_txt="${workspace}/onevnet-list.txt"
oneimage_list_txt="${workspace}/oneimage-list.txt"
onetemplate_list_txt="${workspace}/onetemplate-list.txt"
onevm_list_txt="${workspace}/onevm-list.txt"
remote_commands_txt="${workspace}/remote-commands.txt"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${log_file}"
}

run_logged() {
  log "Running: $*"
  "$@" >>"${log_file}" 2>&1
}

run_as_oneadmin() {
  local command="${1:?command required}"
  log "Running as oneadmin: ${command}"
  sudo -u oneadmin -H bash -lc "${command}" >>"${log_file}" 2>&1
}

write_status() {
  cat > "${status_env}" <<EOF
MODE=${mode}
HOSTNAME=$(hostname)
FREE_BYTES=${free_bytes}
FREE_GIB=${free_gib}
HAS_KVM=${has_kvm}
VIRT_TYPE=${virt_type}
APT_PRESENT=${apt_present}
SUITABLE_MINIONE=${suitable_minione}
SUITABLE_FRONTEND=${suitable_frontend}
EOF
}

bytes_to_gib() {
  awk -v bytes="$1" 'BEGIN { printf "%.2f", bytes / 1024 / 1024 / 1024 }'
}

free_bytes="$(df --output=avail -B1 / | tail -n 1 | tr -d ' ')"
free_gib="$(bytes_to_gib "${free_bytes}")"
virt_type="$(systemd-detect-virt || true)"
has_kvm=0
if [[ -e /dev/kvm ]]; then
  has_kvm=1
fi
apt_present=0
if command -v apt-get >/dev/null 2>&1; then
  apt_present=1
fi
suitable_minione=0
if [[ "${has_kvm}" -eq 1 ]] && awk 'BEGIN{exit !('"${free_bytes}"' >= 80*1024*1024*1024)}'; then
  suitable_minione=1
fi
suitable_frontend=0
if [[ "${apt_present}" -eq 1 ]] && awk 'BEGIN{exit !('"${free_bytes}"' >= 10*1024*1024*1024)}'; then
  suitable_frontend=1
fi

cat > "${probe_json}" <<EOF
{
  "hostname": "$(hostname)",
  "mode": "${mode}",
  "kernel": "$(uname -r)",
  "virt_type": "${virt_type}",
  "has_kvm": ${has_kvm},
  "apt_present": ${apt_present},
  "free_bytes": ${free_bytes},
  "free_gib": ${free_gib},
  "suitable_minione": ${suitable_minione},
  "suitable_frontend": ${suitable_frontend}
}
EOF

write_status

{
  printf 'mode=%s\n' "${mode}"
  printf 'hostname=%s\n' "$(hostname)"
  printf 'virt=%s\n' "${virt_type}"
  printf 'kvm=%s\n' "${has_kvm}"
  printf 'free_gib=%s\n' "${free_gib}"
  printf 'minione_ready=%s\n' "${suitable_minione}"
  printf 'frontend_ready=%s\n' "${suitable_frontend}"
} > "${summary_txt}"

log "Collected host probe into ${workspace}"

cat > "${remote_commands_txt}" <<EOF
Probe:
  bash e2e_bootstrap_opennebula.sh <workspace> probe

Bootstrap:
  OPENNEBULA_SERIES=${opennebula_series} FRONTEND_HOSTNAME=${frontend_host} bash e2e_bootstrap_opennebula.sh <workspace> manual-frontend

Validation:
  - Tunnel local port to 127.0.0.1:2633 on the VM.
  - Read /var/lib/one/.one/one_auth transiently over SSH.
  - Run the current checkout with ONE_XMLRPC and ONE_AUTH set locally.
EOF

if [[ "${mode}" == "probe" ]]; then
  log "Probe-only mode complete."
  exit 0
fi

require_ubuntu_release() {
  if [[ ! -f /etc/os-release ]]; then
    log "Missing /etc/os-release."
    exit 24
  fi
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    log "Unsupported OS '${ID:-unknown}'. Expected Ubuntu."
    exit 25
  fi
  if [[ "${VERSION_ID:-}" != "${ubuntu_series}" ]]; then
    log "Unsupported Ubuntu version '${VERSION_ID:-unknown}'. Expected ${ubuntu_series}."
    exit 26
  fi
}

wait_for_one_cli() {
  local attempts="${1:-30}"
  local sleep_seconds="${2:-5}"
  local index=0
  while (( index < attempts )); do
    if sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' oneuser show >/dev/null 2>&1"; then
      return 0
    fi
    sleep "${sleep_seconds}"
    index=$(( index + 1 ))
  done
  return 1
}

wait_for_host_state() {
  local expected="${1:?expected host state required}"
  local attempts="${2:-24}"
  local sleep_seconds="${3:-5}"
  local index=0
  while (( index < attempts )); do
    local state
    state="$(sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onehost list 2>/dev/null | awk '\$2 == \"${frontend_host}\" { print \$NF; exit }'")"
    if [[ "${state}" == "${expected}" ]]; then
      return 0
    fi
    if [[ -n "${state}" ]]; then
      log "Waiting for ${frontend_host} host state '${expected}', current state '${state}'."
    else
      log "Waiting for ${frontend_host} host registration."
    fi
    sleep "${sleep_seconds}"
    index=$(( index + 1 ))
  done
  return 1
}

ensure_opennebula_repo() {
  run_logged apt-get update
  run_logged apt-get -y install apt-transport-https ca-certificates curl gnupg jq lxc bridge-utils python3 python3-venv wget
  run_logged mkdir -p /etc/apt/keyrings
  run_logged bash -lc "wget -q -O- https://downloads.opennebula.io/repo/repo2.key | gpg --dearmor --yes --output /etc/apt/keyrings/opennebula.gpg"
  cat > /etc/apt/sources.list.d/opennebula.list <<EOF
deb [signed-by=/etc/apt/keyrings/opennebula.gpg] https://downloads.opennebula.io/repo/${opennebula_series}/Ubuntu/${ubuntu_series} stable opennebula
EOF
  run_logged apt-get update
}

ensure_oneadmin_password() {
  local auth_dir="/var/lib/one/.one"
  local auth_file="${auth_dir}/one_auth"
  local password_source="${ONE_E2E_ONEADMIN_PASSWORD:-}"
  local service_active=0
  if systemctl is-active --quiet opennebula; then
    service_active=1
  fi

  run_logged install -d -m 700 -o oneadmin -g oneadmin "${auth_dir}"

  if [[ "${service_active}" -eq 1 && -s "${auth_file}" ]]; then
    log "OpenNebula is already active; preserving existing one_auth file."
    return 0
  fi

  if [[ -z "${password_source}" ]]; then
    password_source="$(openssl rand -hex 16)"
  fi
  printf 'oneadmin:%s\n' "${password_source}" > "${auth_file}"
  run_logged chown oneadmin:oneadmin "${auth_file}"
  run_logged chmod 600 "${auth_file}"
}

install_frontend_packages() {
  ensure_opennebula_repo
  run_logged apt-get -y install opennebula opennebula-tools opennebula-fireedge opennebula-gate opennebula-flow opennebula-node-lxc
  ensure_oneadmin_password
  run_logged systemctl enable --now opennebula opennebula-fireedge opennebula-gate opennebula-flow
  if ! wait_for_one_cli 30 5; then
    log "OpenNebula CLI did not become ready in time."
    return 30
  fi
  return 0
}

configure_local_ssh() {
  run_logged install -d -m 700 -o oneadmin -g oneadmin /var/lib/one/.ssh
  local host_aliases="localhost 127.0.0.1 $(hostname)"
  if hostname -f >/dev/null 2>&1; then
    host_aliases="${host_aliases} $(hostname -f)"
  fi
  run_as_oneadmin "touch /var/lib/one/.ssh/known_hosts"
  run_as_oneadmin "ssh-keyscan -H ${host_aliases} >> /var/lib/one/.ssh/known_hosts 2>/dev/null || true"
  run_as_oneadmin 'grep -qxF "$(cat /var/lib/one/.ssh/id_rsa.pub)" /var/lib/one/.ssh/authorized_keys || cat /var/lib/one/.ssh/id_rsa.pub >> /var/lib/one/.ssh/authorized_keys'
  run_as_oneadmin "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new localhost true"
}

ensure_local_bridge() {
  if ip link show onebr0 >/dev/null 2>&1; then
    log "Bridge onebr0 already exists."
    return 0
  fi
  run_logged ip link add onebr0 type bridge
  run_logged ip link set onebr0 up
}

ensure_localhost_host() {
  if sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onehost list 2>/dev/null | awk '\$2 == \"${frontend_host}\" { found=1 } END { exit found ? 0 : 1 }'"; then
    log "${frontend_host} is already registered as an LXC host."
  else
    run_as_oneadmin "ONE_XMLRPC='${opennebula_endpoint}' onehost create ${frontend_host} -i lxc -v lxc"
  fi

  if ! wait_for_host_state on 24 5; then
    log "${frontend_host} host did not reach 'on' state."
    return 31
  fi
  return 0
}

capture_frontend_artifacts() {
  systemctl --no-pager --full status opennebula opennebula-fireedge opennebula-gate opennebula-flow > "${service_status_txt}" 2>&1 || true
  dpkg-query -W 'opennebula*' 'python3-pyone' > "${package_versions_txt}" 2>&1 || true
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' oneuser show" > "${oneuser_show_txt}" 2>&1 || true
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onehost list" > "${onehost_list_txt}" 2>&1 || true
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onecluster list" > "${onecluster_list_txt}" 2>&1 || true
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onedatastore list" > "${onedatastore_list_txt}" 2>&1 || true
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onevnet list" > "${onevnet_list_txt}" 2>&1 || true
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' oneimage list" > "${oneimage_list_txt}" 2>&1 || true
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onetemplate list" > "${onetemplate_list_txt}" 2>&1 || true
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onevm list" > "${onevm_list_txt}" 2>&1 || true
  cat > "${frontend_facts_json}" <<EOF
{
  "opennebula_endpoint": "${opennebula_endpoint}",
  "opennebula_series": "${opennebula_series}",
  "frontend_host": "${frontend_host}",
  "frontend_ready": 1,
  "host_registered": $(sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' onehost list 2>/dev/null | awk '\$2 == \"${frontend_host}\" { found=1 } END { print found ? 1 : 0 }'"),
  "bridge_onebr0": $(ip link show onebr0 >/dev/null 2>&1 && printf '1' || printf '0'),
  "xmlrpc_port_open": $(ss -ltn '( sport = :2633 )' | tail -n +2 | grep -q 2633 && printf '1' || printf '0')
}
EOF
}

if [[ "${mode}" == "manual-frontend" ]]; then
  if [[ "${suitable_frontend}" -ne 1 ]]; then
    log "Insufficient free space for a frontend installation."
    exit 20
  fi
  require_ubuntu_release
  install_frontend_packages
  configure_local_ssh
  ensure_local_bridge
  ensure_localhost_host
  capture_frontend_artifacts
  log "Manual frontend bootstrap completed successfully."
  exit 0
fi

if [[ "${mode}" == "minione" ]]; then
  if [[ "${suitable_minione}" -ne 1 ]]; then
    log "Host does not satisfy miniONE prerequisites."
    exit 22
  fi
  log "miniONE bootstrap mode requested but not yet implemented in this script."
  exit 23
fi

log "Unknown mode: ${mode}"
exit 64
