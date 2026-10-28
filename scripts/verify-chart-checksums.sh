#!/usr/bin/env bash
# Controleert elk chartarchief in <map> tegen helm-values/chart-checksums.sha256.
# Een archief zonder regel in de lijst faalt; --ignore-missing zou dat
# stilzwijgend overslaan.
set -euo pipefail
repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
dir=$1
shopt -s nullglob
archives=("$dir"/*.tgz)
if (( ${#archives[@]} == 0 )); then
  echo "geen chartarchieven in $dir" >&2
  exit 1
fi
for tgz in "${archives[@]}"; do
  name=$(basename -- "$tgz")
  line=$(awk -v f="$name" '$2 == f' "$repo_root/helm-values/chart-checksums.sha256")
  if [[ -z "$line" ]]; then
    echo "geen checksum voor $name in helm-values/chart-checksums.sha256" >&2
    exit 1
  fi
  (cd -- "$dir" && sha256sum --strict -c - <<<"$line")
done
