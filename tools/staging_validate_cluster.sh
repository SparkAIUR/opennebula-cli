#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  staging_validate_cluster.sh capture

Environment:
  STAGING_FRONTEND         Frontend IP or SSH target
  STAGING_EVIDENCE_DIR     Default: refs/tasks/staging-validate/<timestamp>

The script captures read-only OpenNebula and host health from the staging frontend.
EOF
}

run_ssh() {
  local target="${1:?target required}"
  shift
  ssh -o StrictHostKeyChecking=accept-new "root@${target}" "$@"
}

command="${1:-}"
if [[ "${command}" != "capture" ]]; then
  usage
  exit 64
fi

if [[ -z "${STAGING_FRONTEND:-}" ]]; then
  printf 'STAGING_FRONTEND must be set\n' >&2
  exit 64
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence_dir="${STAGING_EVIDENCE_DIR:-refs/tasks/staging-validate/${timestamp}}"
mkdir -p "${evidence_dir}"

run_ssh "${STAGING_FRONTEND}" "bash -lc '
  echo \"== systemctl ==\"
  systemctl --no-pager --type=service --state=running | egrep \"opennebula|ceph|nginx|docker\" || true
  echo
  echo \"== ceph ==\"
  ceph -s || true
  echo
  echo \"== onehost ==\"
  sudo -u oneadmin -H onehost list || true
  echo
  echo \"== onecluster ==\"
  sudo -u oneadmin -H onecluster list || true
  echo
  echo \"== onedatastore ==\"
  sudo -u oneadmin -H onedatastore list || true
  echo
  echo \"== onevnet ==\"
  sudo -u oneadmin -H onevnet list || true
  echo
  echo \"== oneimage ==\"
  sudo -u oneadmin -H oneimage list || true
  echo
  echo \"== onetemplate ==\"
  sudo -u oneadmin -H onetemplate list || true
  echo
  echo \"== onevm ==\"
  sudo -u oneadmin -H onevm list || true
' " > "${evidence_dir}/frontend-capture.txt"

printf '%s\n' "${evidence_dir}"
