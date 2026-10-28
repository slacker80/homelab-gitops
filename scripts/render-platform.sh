#!/usr/bin/env bash
# Download, checksum, lint en tweemaal renderen; geen clusterverbinding.
set -euo pipefail
repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
render_tmp=$(mktemp -d)
trap 'rm -rf -- "$render_tmp"' EXIT
helm_bin=${HELM_BIN:-helm}
components=(
 'argocd argo-cd https://argoproj.github.io/argo-helm argocd'
 'cert-manager cert-manager https://charts.jetstack.io cert-manager'
 'cilium cilium https://helm.cilium.io kube-system'
)
for entry in "${components[@]}"; do
 read -r component chart repo namespace <<<"$entry"
 ver=$(python3 -c 'import sys,yaml; print(yaml.safe_load(open(sys.argv[1]))[sys.argv[2]]["default"])' "$repo_root/helm-values/versions.yaml" "$component")
 "$helm_bin" pull "$chart" --repo "$repo" --version "$ver" --destination "$render_tmp" \
   --repository-cache "$render_tmp/cache" --repository-config "$render_tmp/repositories.yaml" >&2
 # Elke download moet in de lock staan; nooit stil overslaan.
 "$repo_root/scripts/verify-chart-checksums.sh" "$render_tmp" >&2
 archive="$render_tmp/$chart-$ver.tgz"
 args=(-f "$repo_root/helm-values/$component/values.yaml" -f "$repo_root/helm-values/$component/values-talos.yaml")
 "$helm_bin" lint "$archive" "${args[@]}" --kube-version 1.36.5 >&2
 for pass in 1 2; do
   "$helm_bin" template "$component" "$archive" --namespace "$namespace" --kube-version 1.36.5 "${args[@]}" > "$render_tmp/$component-$pass.yaml"
 done
 # Weiger willekeurige certificaten/wachtwoorden die blijvende drift geven.
 diff -u "$render_tmp/$component-1.yaml" "$render_tmp/$component-2.yaml" >&2
 cat "$render_tmp/$component-1.yaml"
done
