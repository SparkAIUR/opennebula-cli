#!/usr/bin/env bash
set -euo pipefail

workspace="${1:?workspace required}"
opennebula_endpoint="${OPENNEBULA_ENDPOINT:-http://127.0.0.1:2633/RPC2}"
vnet_name="${ONE_E2E_VNET_NAME:-e2e-vnet}"
image_name="${ONE_E2E_IMAGE_NAME:-e2e-alpine-lxc}"
template_name="${ONE_E2E_TEMPLATE_NAME:-e2e-alpine-lxc}"
vm_prefix="${ONE_E2E_VM_PREFIX:-e2e-vm-}"
market_app_name="${ONE_E2E_MARKET_APP_NAME:-alpine_3.20}"
market_arch="${ONE_E2E_MARKET_APP_ARCH:-x86_64}"
market_hypervisor="${ONE_E2E_MARKET_APP_HYPERVISOR:-lxc}"

mkdir -p "${workspace}"
template_dir="${workspace}/templates"
log_file="${workspace}/seed.log"
summary_txt="${workspace}/seed-summary.txt"
fixtures_env="${workspace}/fixtures.env"
fixtures_json="${workspace}/fixtures.json"
mkdir -p "${template_dir}"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${log_file}"
}

run_as_oneadmin() {
  local command="${1:?command required}"
  log "Running as oneadmin: ${command}"
  sudo -u oneadmin -H bash -lc "ONE_XMLRPC='${opennebula_endpoint}' ${command}" >>"${log_file}" 2>&1
}

show_id() {
  local family="${1:?family required}"
  local name="${2:?name required}"
  sudo -u oneadmin -H bash -lc \
    "ONE_XMLRPC='${opennebula_endpoint}' one${family} show '${name}' 2>/dev/null | awk -F':' '/^ID[[:space:]]*:/ {gsub(/ /, \"\", \$2); print \$2; exit}'"
}

ensure_vnet() {
  local vnet_template="${template_dir}/vnet.tmpl"
  if [[ -n "$(show_id vnet "${vnet_name}")" ]]; then
    log "Virtual network ${vnet_name} already exists."
    return 0
  fi

  cat > "${vnet_template}" <<'EOF'
NAME="e2e-vnet"
VN_MAD="bridge"
BRIDGE="onebr0"
BRIDGE_TYPE="linux"
SECURITY_GROUPS="0"
AR=[
  TYPE="IP4",
  IP="172.20.10.10",
  SIZE="16" ]
EOF
  run_as_oneadmin "onevnet create '${vnet_template}'"
}

resolve_market_source() {
  local app_id
  app_id="$(
    sudo -u oneadmin -H bash -lc \
      "ONE_XMLRPC='${opennebula_endpoint}' onemarketapp list | awk '\$2 == \"${market_app_name}\" && \$5 == \"${market_arch}\" && \$6 == \"${market_hypervisor}\" { print \$1; exit }'"
  )"
  if [[ -z "${app_id}" ]]; then
    log "Unable to resolve marketplace app for ${market_app_name}/${market_arch}/${market_hypervisor}."
    return 1
  fi

  sudo -u oneadmin -H bash -lc \
    "ONE_XMLRPC='${opennebula_endpoint}' onemarketapp show '${app_id}' | awk -F': ' '/^SOURCE[[:space:]]*:/ { sub(/^ +/, \"\", \$2); print \$2; exit }'"
}

ensure_image() {
  local image_template="${template_dir}/image.tmpl"
  local source_path
  if [[ -n "$(show_id image "${image_name}")" ]]; then
    log "Image ${image_name} already exists."
    return 0
  fi

  source_path="$(resolve_market_source)"
  if [[ -z "${source_path}" ]]; then
    log "Unable to resolve image source for ${image_name}."
    return 1
  fi

  cat > "${image_template}" <<EOF
NAME="${image_name}"
TYPE="OS"
PATH="${source_path}"
DEV_PREFIX="sd"
EOF
  run_as_oneadmin "oneimage create -d default '${image_template}'"
}

ensure_template() {
  local vm_template="${template_dir}/vm.tmpl"
  if [[ -n "$(show_id template "${template_name}")" ]]; then
    log "Template ${template_name} already exists."
    return 0
  fi

  cat > "${vm_template}" <<EOF
NAME="${template_name}"
CPU="1"
VCPU="2"
MEMORY="768"
HYPERVISOR="lxc"
LXC_UNPRIVILEGED="false"
DISK=[
  IMAGE="${image_name}" ]
GRAPHICS=[
  LISTEN="0.0.0.0",
  TYPE="vnc" ]
NIC=[
  NETWORK="${vnet_name}" ]
CONTEXT=[
  NETWORK="YES",
  SET_HOSTNAME="\$NAME",
  SSH_PUBLIC_KEY="\$USER[SSH_PUBLIC_KEY]" ]
RAW=[
  DATA="lxc.apparmor.profile=unconfined",
  TYPE="lxc" ]
SCHED_REQUIREMENTS="HYPERVISOR=lxc & ARCH=x86_64"
EOF
  run_as_oneadmin "onetemplate create '${vm_template}'"
}

write_fixtures() {
  local vnet_id image_id template_id
  vnet_id="$(show_id vnet "${vnet_name}")"
  image_id="$(show_id image "${image_name}")"
  template_id="$(show_id template "${template_name}")"

  cat > "${fixtures_env}" <<EOF
ONE_E2E_VNET_NAME=${vnet_name}
ONE_E2E_VNET_ID=${vnet_id}
ONE_E2E_IMAGE_NAME=${image_name}
ONE_E2E_IMAGE_ID=${image_id}
ONE_E2E_TEMPLATE_NAME=${template_name}
ONE_E2E_TEMPLATE_ID=${template_id}
ONE_E2E_VM_PREFIX=${vm_prefix}
EOF

  cat > "${fixtures_json}" <<EOF
{
  "vnet": {"id": ${vnet_id:-0}, "name": "${vnet_name}"},
  "image": {"id": ${image_id:-0}, "name": "${image_name}"},
  "template": {"id": ${template_id:-0}, "name": "${template_name}"},
  "vm_prefix": "${vm_prefix}"
}
EOF

  {
    printf 'vnet=%s (%s)\n' "${vnet_name}" "${vnet_id}"
    printf 'image=%s (%s)\n' "${image_name}" "${image_id}"
    printf 'template=%s (%s)\n' "${template_name}" "${template_id}"
    printf 'vm_prefix=%s\n' "${vm_prefix}"
  } > "${summary_txt}"
}

ensure_vnet
ensure_image
ensure_template
write_fixtures
log "Fixture seed completed successfully."
