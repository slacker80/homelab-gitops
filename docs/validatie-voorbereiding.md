# Lokaal validatiebewijs — 27 oktober 2026

Alleen conceptvoorbereiding. Geen clusteractie, runtimeproef, modelrun,
migratie of restore uitgevoerd. Geen uitrolvrijgave.

- `python3 scripts/validate.py`: alle YAML-bestanden leesbaar; labels uit,
  appsets in project `workloads`, chartbron toegestaan in het project, checksum
  aanwezig, `CreateNamespace=true` met PSA restricted, PVC's beschermd en
  gekoppeld in de values, geen `charts/` of `manifests/namespaces/`.
- Negatieve test: één `apps/*`-label op `true` laat de validatie falen.
- `python3 scripts/validate.py --release`: weigert zoals bedoeld (open punten
  en TODO-waarden).
- `scripts/render-apps.sh`: twee chartarchieven gedownload en SHA256 gelijk aan
  de digest in de officiële index van elke chartrepo
  (home-assistant 0.3.89, app-template 5.3.0). Geen enkele app rendert een Secret.
  Alle zes apps renderen; geen chart maakt zelf een PVC, alle workloads mounten
  de PVC uit `manifests/<app>/base`. Helm-testresources (HA-testpod) slaat Argo over.
- `scripts/render-kyverno.sh`: beide archieven tegen de checksum gecontroleerd;
  101 documenten; alle gerenderde policies `failurePolicy: Ignore`,
  validationActions Audit en de vier namespace-uitzonderingen.
- Cilium 1.20.4: archief tegen checksum gecontroleerd; twee renders na elkaar
  zijn byte-gelijk (stabiel onder Argo).
- Kustomize: alle `manifests/*/talos`-overlays bouwen.
- Gitleaks 8.30.1 (`gitleaks dir .`): geen geheimen gevonden.
- pre-commit en Trunk: niet uitgevoerd; configuratie ontbreekt.

Gebruikt: Helm v3.19.0, Kustomize v5.7.1, Gitleaks 8.30.1, Python 3/PyYAML 6.0.2;
archiefhashes van de tools vergeleken met de upstream-checksums. Alleen tijdelijke
hulpmiddelen; geen systeempackage of dienst aangepast.

Niet te bewijzen met rendering: door Kyverno gegenereerde webhooks, app-health,
niet-root-compatibiliteit van de images, PV-Retain, netwerk, readiness,
gedeelde agentlimieten en herstel. Zie [voorbereiding](voorbereiding.md) en
[open punten](../preparation-state.yaml).
