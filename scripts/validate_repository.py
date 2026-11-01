#!/usr/bin/env python3
"""Controleer Git-bronnen en de gedeelde officiële GitHub-hostkey."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
URL = 'git@github.com:slacker80/homelab-gitops.git'
KEY = 'github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl'


def validate():
    count = 0
    def walk(v):
        nonlocal count
        if isinstance(v, str) and 'slacker80/homelab-gitops' in v:
            if v != URL: raise ValueError('Afwijkende homelab-gitops-bron')
            count += 1
        elif isinstance(v, dict):
            for x in v.values(): walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
    for file in (ROOT/'argocd').rglob('*.yaml'):
        for doc in yaml.safe_load_all(file.read_text()): walk(doc)
    if count != 40: raise ValueError(f'Verwacht 40 bestaande Git-bronnen, gevonden {count}; review dekking')
    shared = yaml.safe_load((ROOT/'helm-values/argocd/values.yaml').read_text())['configs']['ssh']['knownHosts'].strip()
    if shared != KEY or (ROOT/'bootstrap/github_known_hosts').read_text().strip() != KEY:
        raise ValueError('GitHub-hostkeys verschillen van officiële pin')
    print(f'{count} Git-bronnen gebruiken één SSH-URL; gedeelde GitHub-hostkey klopt.')


if __name__ == '__main__': validate()
