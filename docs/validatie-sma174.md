# Lokale verificatie SMA-174 — 2026-10-31

- validate.py geslaagd: YAML, references en voorbereidingsgrenzen consistent; labels uit.
- Zes virtualisatie-overlays renderen: 31 objecten, zonder Namespace-objecten. Upstream-checksums en KubeVirt/CDI-CRD-schema’s akkoord. Alle zeven gewijzigde Kustomize-overlays afzonderlijk gecontroleerd.
- render-apps.sh: vijf apps renderen; chartchecksum akkoord; geen HA-chart meer.
- render-platform.sh: Cilium/Argo/cert-manager render en lint/checksums geslaagd.
- render-kyverno.sh: bestaand renderpad geslaagd; securitybronnen niet gewijzigd.
- render-gateway.sh: lint/herhaalrender/schema en Service-contract geslaagd: acht resources en drie routes; vijf negatieve proeven geweigerd. Geen HA-backend.
- validate_virtualization.py --release terecht geweigerd: verplichte invoer en reviews ontbreken. Algemene releasevrijgave blijft ook door bestaande app-/platformpunten geblokkeerd.
- Bash-syntax en git diff --check akkoord. pre-commit en trunk niet aanwezig, configuraties ontbreken; niet uitgevoerd.

Geen apply, sync, clusterverbinding of PoC. Geen admission/CEL, USB, CDI-import,
VM-start, DHCP, gastinstallatie, shutdownduur, capaciteitsmeting of restore bewezen.
Verplichte hardware-/image-invoer, storage en Gerrits security-integratie staan in
docs/virtualisatie.md en virtualization/required-inputs.yaml.

Worktree: /home/peter/sma174-work/gitops. Gepubliceerde main 9b66db1 gecombineerd
met lokale SMA-155-inhoud. Publieke Git-fetch werkte; publicatie via geautoriseerde
GitHub-koppeling. Renders blijven buiten Git onder /home/peter/sma174-work.
Geen gegenereerde secrets gepubliceerd.
