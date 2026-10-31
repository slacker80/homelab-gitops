#!/usr/bin/env bash
# Alleen lokaal: vendored checksums en Kustomize, geen clusterverbinding.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
kustomize_bin=${KUSTOMIZE_BIN:-kustomize}
python3 "$root/scripts/validate_virtualization.py" >&2
for component in kubevirt-operator kubevirt cdi-operator cdi multus virtual-machines; do
  printf '\n---\n# component: %s\n' "$component"
  "$kustomize_bin" build "$root/manifests/$component/talos"
done
