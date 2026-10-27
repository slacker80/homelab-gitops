#!/usr/bin/env bash
# Lokaal renderen van de zes app-charts; benadert geen Kubernetes-cluster.
set -euo pipefail
repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
render_tmp=$(mktemp -d)
trap 'rm -rf -- "$render_tmp"' EXIT
helm_bin=${HELM_BIN:-helm}
version() {
  python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))[sys.argv[2]]["default"])' \
    "$repo_root/helm-values/versions.yaml" "$1"
}
# app chart repo namespace
apps=(
  "homeassistant home-assistant https://pajikos.github.io/home-assistant-helm-chart apps-homeassistant"
  "hermes hermes-agent https://jyje.github.io/hermes-agent-helm apps-hermes"
  "paperclip app-template https://bjw-s-labs.github.io/helm-charts apps-paperclip"
  "claude-agent app-template https://bjw-s-labs.github.io/helm-charts agents-claude"
  "codex-agent app-template https://bjw-s-labs.github.io/helm-charts agents-codex"
  "opencode-agent app-template https://bjw-s-labs.github.io/helm-charts agents-opencode"
)
for entry in "${apps[@]}"; do
  read -r app chart repo _ <<<"$entry"
  ver=$(version "$app")
  [[ -f "$render_tmp/$chart-$ver.tgz" ]] && continue
  "$helm_bin" pull "$chart" --repo "$repo" --version "$ver" --destination "$render_tmp" \
    --repository-cache "$render_tmp/cache" --repository-config "$render_tmp/repositories.yaml"
done
(cd -- "$render_tmp" && sha256sum --ignore-missing -c "$repo_root/helm-values/chart-checksums.sha256" >&2)
for entry in "${apps[@]}"; do
  read -r app chart _ namespace <<<"$entry"
  ver=$(version "$app")
  args=(-f "$repo_root/helm-values/$app/values.yaml" -f "$repo_root/helm-values/$app/values-management.yaml")
  echo "---"
  echo "# app: $app ($chart $ver)"
  "$helm_bin" template "$app" "$render_tmp/$chart-$ver.tgz" \
    --namespace "$namespace" --kube-version 1.36.5 "${args[@]}"
done
