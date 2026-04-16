#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  staging_bootstrap_cluster.sh gather
  staging_bootstrap_cluster.sh prepare
  staging_bootstrap_cluster.sh install-common

Environment:
  STAGING_FRONTEND           Frontend IP or SSH target
  STAGING_HYPERVISORS        Comma-separated hypervisor SSH targets
  STAGING_FRONTEND_NAME      Default: lab-fe-01
  STAGING_HYPERVISOR_NAMES   Comma-separated names matching STAGING_HYPERVISORS
  STAGING_DATA_DEVICE        Default: /dev/xvde1
  STAGING_DATA_MOUNT         Default: /var/lib/one
  STAGING_CEPH_DEVICE        Default: /dev/xvdf1
  STAGING_EVIDENCE_DIR       Default: refs/tasks/staging-bootstrap/<timestamp>

Notes:
  - This script intentionally stops at host preparation and evidence capture.
  - OpenNebula, Ceph, and Omni service bootstrap remain explicit follow-on steps.
EOF
}

require_env() {
  local name="${1:?name required}"
  if [[ -z "${!name:-}" ]]; then
    printf '%s must be set\n' "${name}" >&2
    exit 64
  fi
}

run_ssh() {
  local target="${1:?target required}"
  shift
  ssh -o StrictHostKeyChecking=accept-new "root@${target}" "$@"
}

split_csv() {
  printf '%s\n' "${1:-}" | tr ',' '\n' | sed '/^$/d'
}

command="${1:-}"
if [[ -z "${command}" ]]; then
  usage
  exit 64
fi

case "${command}" in
  gather|prepare|install-common)
    ;;
  *)
    usage
    exit 64
    ;;
esac

require_env STAGING_FRONTEND
require_env STAGING_HYPERVISORS

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence_dir="${STAGING_EVIDENCE_DIR:-refs/tasks/staging-bootstrap/${timestamp}}"
frontend_name="${STAGING_FRONTEND_NAME:-lab-fe-01}"
data_device="${STAGING_DATA_DEVICE:-/dev/xvde1}"
data_mount="${STAGING_DATA_MOUNT:-/var/lib/one}"
ceph_device="${STAGING_CEPH_DEVICE:-/dev/xvdf1}"

hypervisors=()
while IFS= read -r line; do
  hypervisors+=("${line}")
done <<EOF
$(split_csv "${STAGING_HYPERVISORS}")
EOF

hypervisor_names=()
while IFS= read -r line; do
  hypervisor_names+=("${line}")
done <<EOF
$(split_csv "${STAGING_HYPERVISOR_NAMES:-lab-hv-01,lab-hv-02,lab-hv-03,lab-hv-04}")
EOF

if (( ${#hypervisors[@]} != ${#hypervisor_names[@]} )); then
  printf 'STAGING_HYPERVISORS and STAGING_HYPERVISOR_NAMES must have the same number of entries\n' >&2
  exit 65
fi

mkdir -p "${evidence_dir}"

declare -a all_nodes=("${STAGING_FRONTEND}")
declare -a all_names=("${frontend_name}")
for idx in "${!hypervisors[@]}"; do
  all_nodes+=("${hypervisors[idx]}")
  all_names+=("${hypervisor_names[idx]}")
done

gather_node() {
  local target="${1:?target required}"
  local label="${2:?label required}"
  run_ssh "${target}" "\
    printf 'node=%s\n' '${label}'; \
    hostnamectl status --static; \
    uname -a; \
    . /etc/os-release && printf 'os=%s %s\n' \"\$ID\" \"\$VERSION_ID\"; \
    echo '--- lsblk ---'; lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT; \
    echo '--- ip ---'; ip -brief a; \
    echo '--- route ---'; ip r; \
    echo '--- kvm ---'; test -e /dev/kvm && echo yes || echo no; \
    echo '--- free ---'; free -h; \
    echo '--- df ---'; df -h / /boot /boot/efi 2>/dev/null || true" \
    > "${evidence_dir}/${label}.txt"
}

prepare_node() {
  local target="${1:?target required}"
  local label="${2:?label required}"
  run_ssh "${target}" "\
    hostnamectl set-hostname '${label}'; \
    mkdir -p '${data_mount}'; \
    blkid '${data_device}' >/dev/null 2>&1 || mkfs.ext4 -F '${data_device}'; \
    uuid=\$(blkid -s UUID -o value '${data_device}'); \
    grep -q \"${data_mount}\" /etc/fstab || printf 'UUID=%s %s ext4 defaults,nofail 0 2\n' \"\$uuid\" '${data_mount}' >> /etc/fstab; \
    mount '${data_mount}'; \
    test -b '${ceph_device}'" \
    > "${evidence_dir}/${label}-prepare.txt"
}

install_common() {
  local target="${1:?target required}"
  local label="${2:?label required}"
  run_ssh "${target}" "\
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update; \
    apt-get install -y ca-certificates curl gnupg lsb-release jq bridge-utils qemu-system-x86 qemu-utils libvirt-daemon-system libvirt-clients virtinst openvswitch-switch chrony python3 python3-venv" \
    > "${evidence_dir}/${label}-packages.txt"
}

for idx in "${!all_nodes[@]}"; do
  case "${command}" in
    gather)
      gather_node "${all_nodes[idx]}" "${all_names[idx]}"
      ;;
    prepare)
      prepare_node "${all_nodes[idx]}" "${all_names[idx]}"
      ;;
    install-common)
      install_common "${all_nodes[idx]}" "${all_names[idx]}"
      ;;
  esac
done

printf '%s\n' "${evidence_dir}"
