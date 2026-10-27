# Agent-instructies

GitOps-repository voor het homelab. Lees eerst [README.md](README.md).

## Code discovery

Gebruik bij voorkeur codebase-memory-mcp: `search_graph`, `trace_path`,
`get_code_snippet` en `query_graph`. Indexeer de repository wanneer nodig.
Gebruik tekstzoekopdrachten voor configuratiewaarden en wanneer de graph
onvoldoende resultaat geeft.

## Indeling en conventies

- `argocd/`: Argo CD-objecten; de root-Application leest deze map recursief.
- `helm-values/`: Helm-values en centrale chartversies in `versions.yaml`.
- `manifests/`: gewone Kubernetes-resources en Kustomize-overlays.
- Componenten worden geselecteerd via labels op cluster-Secrets.
- Voeg geen credentials of wachtwoorden toe aan Git.
- Gebruik Gateway API voor routes.
- Pas resources via Argo CD toe; voer geen lokale `kubectl apply` uit.
- Controleer de werkboom vóór wijzigingen en behoud niet-gerelateerde wijzigingen.

## Validatie

Render alle gewijzigde Kustomize-overlays en draai relevante bestaande tests.
Controleer YAML, lokale bestandsverwijzingen en ApplicationSet-bronnen.

De eerder voorgeschreven commando's vóór een commit zijn:

```bash
pre-commit run --all-files
trunk check
```

Deze clone bevat momenteel geen pre-commit- of Trunk-configuratie. Meld ontbrekende
checks expliciet; presenteer ze niet als geslaagd. Maak geen commit of push tenzij
de gebruiker daarom vraagt.
