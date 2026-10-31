#!/usr/bin/env bash
# Offline na downloads; geen kubectl of clustercredentials nodig.
set -euo pipefail
repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
render_tmp=$(mktemp -d)
trap 'rm -rf -- "$render_tmp"' EXIT
helm_bin=${HELM_BIN:-helm}
kustomize_bin=${KUSTOMIZE_BIN:-kustomize}
ver=$(python3 -c 'import sys,yaml; print(yaml.safe_load(open(sys.argv[1]))["envoy-gateway"]["default"])' "$repo_root/helm-values/versions.yaml")
"$helm_bin" pull oci://docker.io/envoyproxy/gateway-helm --version "$ver" --destination "$render_tmp"
"$repo_root/scripts/verify-chart-checksums.sh" "$render_tmp"
archive="$render_tmp/gateway-helm-$ver.tgz"
args=(-f "$repo_root/helm-values/envoy-gateway/values.yaml" -f "$repo_root/helm-values/envoy-gateway/values-talos.yaml")
"$helm_bin" lint "$archive" "${args[@]}" --kube-version 1.36.5
for pass in 1 2; do
  "$helm_bin" template envoy-gateway "$archive" --namespace envoy-gateway-system --include-crds "${args[@]}" > "$render_tmp/envoy-$pass.yaml"
done
diff -u "$render_tmp/envoy-1.yaml" "$render_tmp/envoy-2.yaml"
"$kustomize_bin" build "$repo_root/manifests/gateway/talos" > "$render_tmp/routes.yaml"
# Service contracts must use the same chart versions, releases and values as Argo.
for entry in 'argocd argo-cd https://argoproj.github.io/argo-helm argocd' 'cilium cilium https://helm.cilium.io kube-system' 'paperclip app-template https://bjw-s-labs.github.io/helm-charts apps-paperclip'; do
  read -r component chart repo namespace <<<"$entry"
  version=$(python3 -c 'import sys,yaml; print(yaml.safe_load(open(sys.argv[1]))[sys.argv[2]]["default"])' "$repo_root/helm-values/versions.yaml" "$component")
  "$helm_bin" pull "$chart" --repo "$repo" --version "$version" --destination "$render_tmp" --repository-cache "$render_tmp/cache" --repository-config "$render_tmp/repositories.yaml"
  "$repo_root/scripts/verify-chart-checksums.sh" "$render_tmp"
  values=(-f "$repo_root/helm-values/$component/values.yaml" -f "$repo_root/helm-values/$component/values-talos.yaml")
  "$helm_bin" lint "$render_tmp/$chart-$version.tgz" "${values[@]}" --kube-version 1.36.5
  "$helm_bin" template "$component" "$render_tmp/$chart-$version.tgz" --namespace "$namespace" --kube-version 1.36.5 "${values[@]}" > "$render_tmp/$component.yaml"
done
python3 "$repo_root/scripts/validate-gateway.py" "$render_tmp/routes.yaml" "$render_tmp/envoy-1.yaml" "$render_tmp/argocd.yaml" "$render_tmp/cilium.yaml" "$render_tmp/paperclip.yaml"
