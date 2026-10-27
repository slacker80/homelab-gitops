#!/usr/bin/env bash
# Lokaal renderen; benadert geen Kubernetes-cluster.
set -euo pipefail
repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
render_tmp=$(mktemp -d)
trap 'rm -rf -- "$render_tmp"' EXIT
helm_bin=${HELM_BIN:-helm}
for component in kyverno kyverno-policies; do
  "$helm_bin" pull "$component" --repo https://kyverno.github.io/kyverno \
    --version 3.9.2 --destination "$render_tmp" \
    --repository-cache "$render_tmp/cache" --repository-config "$render_tmp/repositories.yaml"
done
(cd -- "$render_tmp" && sha256sum -c "$repo_root/helm-values/chart-checksums.sha256" >&2)
for component in kyverno kyverno-policies; do
  "$helm_bin" template "$component" "$render_tmp/$component-3.9.2.tgz" \
    --namespace kyverno --kube-version 1.36.5 \
    -f "$repo_root/helm-values/$component/values.yaml" \
    -f "$repo_root/helm-values/$component/values-management.yaml"
done
