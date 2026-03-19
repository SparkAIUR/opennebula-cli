#!/usr/bin/env bash
set -euo pipefail

workspace="${1:?workspace required}"
mode="${2:-probe}"

mkdir -p "${workspace}"
log_file="${workspace}/bootstrap.log"
probe_json="${workspace}/probe.json"
status_env="${workspace}/status.env"
summary_txt="${workspace}/summary.txt"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${log_file}"
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

if [[ "${mode}" == "probe" ]]; then
  log "Probe-only mode complete."
  exit 0
fi

if [[ "${mode}" == "manual-frontend" ]]; then
  if [[ "${suitable_frontend}" -ne 1 ]]; then
    log "Insufficient free space for a frontend installation."
    exit 20
  fi
  log "Frontend bootstrap mode requested but not yet implemented in this script."
  exit 21
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
