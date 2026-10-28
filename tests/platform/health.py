#!/usr/bin/env python3
"""Test de echte Lua-healthcheck zonder Argo of cluster. Vereist lua en PyYAML."""
import subprocess
from pathlib import Path
import yaml
root = Path(__file__).resolve().parents[2]
code = yaml.safe_load((root / 'helm-values/argocd/values.yaml').read_text())['configs']['cm']['resource.customizations.health.argoproj.io_Application']
cases = [
    ('{}', 'Progressing'),
    ('{status={sync={status="Synced"},health={status="Healthy"}}}', 'Healthy'),
    ('{status={sync={status="OutOfSync"},health={status="Healthy"}}}', 'Progressing'),
    ('{status={sync={status="Synced"},health={status="Progressing"}}}', 'Progressing'),
    ('{status={sync={status="Synced"},health={status="Degraded",message="fout"}}}', 'Degraded'),
]
for fixture, expected in cases:
    script = 'obj = ' + fixture + '\nlocal function check()\n' + code + '\nend\nprint(check().status)\n'
    result = subprocess.run(['lua', '-'], input=script, text=True, capture_output=True, check=True)
    assert result.stdout.strip() == expected, result.stdout
print(f'Application-health: {len(cases)} gevallen geslaagd')
