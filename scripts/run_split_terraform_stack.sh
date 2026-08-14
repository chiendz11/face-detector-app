#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
if [ "$action" != "apply" ] && [ "$action" != "destroy" ]; then
  echo "Usage: $0 apply|destroy" >&2
  exit 2
fi

required_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi
}

for name in \
  TF_STATE_BUCKET \
  TF_STATE_LOCK_TABLE \
  TF_STATE_REGION \
  NETWORK_STATE_KEY \
  CLUSTER_STATE_KEY \
  DATA_STATE_KEY \
  PLATFORM_STATE_KEY; do
  required_env "$name"
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export TF_VAR_terraform_state_bucket="${TF_VAR_terraform_state_bucket:-$TF_STATE_BUCKET}"
export TF_VAR_terraform_state_region="${TF_VAR_terraform_state_region:-$TF_STATE_REGION}"
export TF_VAR_network_state_key="${TF_VAR_network_state_key:-$NETWORK_STATE_KEY}"
export TF_VAR_cluster_state_key="${TF_VAR_cluster_state_key:-$CLUSTER_STATE_KEY}"

init_root() {
  local root="$1"
  local key="$2"

  terraform -chdir="$repo_root/$root" init -input=false \
    -backend-config="bucket=$TF_STATE_BUCKET" \
    -backend-config="dynamodb_table=$TF_STATE_LOCK_TABLE" \
    -backend-config="key=$key" \
    -backend-config="region=$TF_STATE_REGION"
}

run_root() {
  local root="$1"
  local key="$2"
  local verb="$3"

  echo "::group::Terraform $verb $root"
  init_root "$root" "$key"
  terraform -chdir="$repo_root/$root" "$verb" -auto-approve -input=false
  echo "::endgroup::"
}

if [ "$action" = "apply" ]; then
  run_root "terraform/network" "$NETWORK_STATE_KEY" apply
  run_root "terraform/cluster" "$CLUSTER_STATE_KEY" apply
  run_root "terraform/data" "$DATA_STATE_KEY" apply
  run_root "terraform/platform" "$PLATFORM_STATE_KEY" apply
else
  run_root "terraform/platform" "$PLATFORM_STATE_KEY" destroy
  run_root "terraform/data" "$DATA_STATE_KEY" destroy
  run_root "terraform/cluster" "$CLUSTER_STATE_KEY" destroy
  run_root "terraform/network" "$NETWORK_STATE_KEY" destroy
fi
