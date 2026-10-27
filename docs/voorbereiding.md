# Voorbereiding SMA-94 — concept, geen uitrolvrijgave

Basis: Peters [PR 1](https://github.com/slacker80/homelab-gitops/pull/1),
commit `acda1db69a6bae01e3f561205c90c83ee16e4959`.
Besluitbron: [homelab-specs](https://github.com/slacker80/homelab-specs),
`docs/besluiten.md` en de changes `gitops-bootstrap`, `persistent-storage`,
`network-policy-baseline`, `admission-policy`, `homeassistant`, `paperclip`,
`hermes`, de drie agentchanges en `agent-dispatch`.

## Structuur van Peter

- `helm-values/versions.yaml`: centrale chartversies met Renovate-annotaties,
  `default` en eventueel een clusternaam als override. Checksums van de
  chartarchieven staan in `helm-values/chart-checksums.sha256`.
- `helm-values/<component>/values.yaml` en `values-management.yaml`: basis en
  clusteroverrides. Ontbrekende valuesbestanden laten de render falen.
- `manifests/<component>/management/`: extra resources via Kustomize.
- `argocd/applicationsets/`: clusterselectie, chartbron, valuesbron en extra manifests.

## Besluiten van Peter (SMA-94, 27 oktober 2026)

- **Charts:** upstream waar het kan. Er is voor geen van de zes apps een
  officiële chart van de maker gevonden. Daarom:
  - Home Assistant: community-chart [pajikos/home-assistant-helm-chart](https://github.com/pajikos/home-assistant-helm-chart) 0.3.89.
  - Hermes: community-chart [jyje/hermes-agent-helm](https://github.com/jyje/hermes-agent-helm) 1.22.0.
  - Paperclip en de Claude-, Codex- en OpenCode-worker: [bjw-s app-template](https://github.com/bjw-s-labs/helm-charts) 5.3.0.
    Voor Paperclip bestaat alleen een operator van een derde partij
    (paperclipinc/paperclip-operator, met CRD's en eigen controller); die is
    bewust niet gekozen.
  - De eigen map `charts/` is vervallen.
- **Namespaces:** via de ApplicationSets met `CreateNamespace=true` en
  `managedNamespaceMetadata` (PSA restricted voor apps-*/agents-*). Volgens de
  [Argo CD-documentatie](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/#create-namespace)
  wordt zo'n namespace normaal niet gevolgd en dus niet met de Application
  verwijderd. De aparte namespace-app en `manifests/namespaces/` zijn vervallen.
  `argocd` maakt de Terraform-bootstrap aan. Platformnamespaces krijgen geen
  PSA-labels en volgen de Talos-baseline.
- **Beheer na bootstrap (SMA-150):** Terraform installeert Cilium en Argo
  eenmalig; daarna beheert Argo beide vanuit deze repo. Zie
  [Terraform-bootstrap](terraform-bootstrap.md).

## Lokaal voorbereid

| Onderdeel | Voorbereid | Nog niet gereed |
| --- | --- | --- |
| Root | naam `root`, `bootstrap/` uitgesloten, geen cascade-finalizer | definitieve bootstrap, toegang en readiness |
| Cilium | zelfbeheer-ApplicationSet (label `cilium-install`, geen prune); Hubble-certificaten via certgen-job zodat de render stabiel is; één CCNP buiten kube-system | overdracht in homelab-infra; component-CNPs vóór inschakelen CCNP |
| Argo CD | zelfbeheer via bestaande ApplicationSet (label `argocd-install`) | overdracht in homelab-infra |
| Kyverno | Peters values, met alleen de spec-afwijkingen: chart 3.9.2, failurePolicy Ignore en `forceFailurePolicyIgnore`; upstream policies restricted/Audit met vier namespace-uitzonderingen | compatibiliteitsproef op Kubernetes 1.36.5 |
| Home Assistant | community-chart, Deployment/Recreate, PVC `homeassistant-config` 6Gi, 2Gi limiet | image-digest, niet-root onder PSA restricted, integraties en LAN-poorten |
| Hermes | community-chart, Deployment/Recreate, PVC `hermes-data` 8Gi op `/opt/data`, 2Gi limiet, testjob uit | image gelijk aan huidige build, gateway/auth/toolbackend, UID; chart maakt altijd een eigen Secret |
| Paperclip | app-template: server (Deployment/Recreate) en PostgreSQL (StatefulSet), PVC's `paperclip-data` 6Gi en `paperclip-postgres` 8Gi | build, datadir, poort/health, PostgreSQL-versie, herstel |
| Claude/Codex/OpenCode | app-template per worker, PVC 3/3/2Gi, 256Mi wachtlimiet, read-only rootfs | echte workerimages, bridge/leasecontract en gedeeld taakbudget |
| cert-manager/Envoy Gateway | PR-1-versies en indeling behouden, labels uit | Gateway/TLS/Issuer/adressen |

Alle componentlabels staan `false`; dat is de enige uitrolpoort. Waarden die nog
niet bekend zijn staan als `TODO-…` in de values; `validate.py --release` weigert
zolang die bestaan. Een geldige render geeft geen toestemming voor uitvoering.

### Bekende beperkingen van de gekozen charts

- De Hermes-chart zet `env` altijd in een eigen Secret (zonder External Secrets
  Operator). Met `env: {}` staan er geen sleutels in Git, maar het lege Secret
  botst met de blokkade op kind `Secret` in project `workloads`. Keuze nodig:
  die blokkade voor deze ene Secret loslaten, of Hermes ook op app-template zetten.
- Project `workloads` staat nu cluster-resource `Namespace` toe, nodig voor
  `CreateNamespace=true`. Dat laat ook een Namespace-object uit een chart toe;
  controleer de render bij elke chartupdate.
- De drie community/derde-partijcharts worden door één persoon of klein team
  onderhouden. Renovate stelt updates voor; majors vragen review.

## Controleren

Vereist lokaal: Python 3/PyYAML, Helm en Kustomize; geen clusterverbinding.

```bash
python3 scripts/validate.py
python3 scripts/validate.py --release   # hoort te weigeren
scripts/render-apps.sh > /tmp/apps.yaml
scripts/render-kyverno.sh > /tmp/kyverno.yaml
kustomize build manifests/<component>/management
```

## Beheer en herstel

Repository: `slacker80/homelab-gitops` op GitHub. Let op: GitHub meldt deze repo
op 27 oktober 2026 als **publiek**, terwijl SMA-94 om een private repo vroeg.
Er staan geen secrets in, maar wel de inrichting van het homelab.

De bedoelde runtime is het toekomstige Talos-cluster op de ThinkCentre; host,
adressen en live bereikbaarheid zijn niet bewezen. De bestaande
Pi/Hermes/Paperclip zijn niet gewijzigd.

Codevoorbereiding terugdraaien: de concept-PR sluiten of, na een merge, de
voorbereidingscommits met `git revert` terugdraaien. Dat herstelt geen appdata.
Bij latere runtimeproblemen eerst root en betrokken children pauzeren, schrijvers
stoppen en met een bekende Git-revisie plus externe herstelset terug. Nooit
namespaces of PVC's als generieke herstelactie verwijderen.

PVC's hebben `Prune=false,Delete=false`; ApplicationSets behouden children bij
verwijderen; namespaces uit `CreateNamespace` worden normaal niet gevolgd.
PV-Retain en een echte restore moeten nog worden bewezen. Live uitvoering en
herstelproef blijven onder SMA-102 met vooraf geschreven terugvalplan en Peters
afzonderlijke akkoord.
