# Voorbereiding SMA-94 — concept, geen uitrolvrijgave

Basis: Peters [PR 1](https://github.com/slacker80/homelab-gitops/pull/1),
commit `acda1db69a6bae01e3f561205c90c83ee16e4959`.
Besluitbron: [homelab-specs](https://github.com/slacker80/homelab-specs),
`docs/besluiten.md` en de changes `gitops-bootstrap`, `persistent-storage`,
`network-policy-baseline`, `admission-policy`, `homeassistant`, `paperclip`,
`hermes`, de drie agentchanges en `agent-dispatch`.
De specs blijven daar; deze repo bevat implementatievoorbereiding.

## Structuur van Peter

- `helm-values/versions.yaml`: centrale chartversies met `default` en eventueel
  een clusternaam als override. Voor lokale charts controleert `validate.py`
  dat deze versie gelijk is aan `charts/<naam>/Chart.yaml`; Argo haalt een lokale
  chart uit dezelfde Git-revisie, niet uit een Helm-register.
- `helm-values/<component>/values.yaml` en `values-management.yaml`: expliciete
  basis en clusteroverrides. Ontbrekende values worden niet stilzwijgend genegeerd.
- `manifests/<component>/management/`: extra resources via Kustomize.
- `argocd/applicationsets/`: clusterselectie, chartbron, valuesbron en waar nodig
  een afzonderlijke manifestbron. De naam `management` uit PR 1 blijft behouden.
- `charts/`: zes eigen, nog uitgeschakelde charts; geen verzonnen publieke charts.

## Lokaal voorbereid

| Onderdeel | Voorbereid | Nog niet gereed |
| --- | --- | --- |
| Root | naam `root`, bootstrap uitgesloten uit eigen recursieve inventaris, geen cascade-finalizer | definitieve bootstrapbron en readiness |
| Kyverno | charts 3.9.2, engine 1.19.2; twee admission-replica's, restricted/Audit/Ignore; geen eigen actieve policies | gegenereerde webhooks en compatibiliteitsproef op Kubernetes 1.36.5 |
| Cilium | één `cluster-default-deny`, DNS, alleen kube-system uitgezonderd | volledige component-CNPs vóór inschakelen; Cilium-zelfbeheer |
| Namespaces | apps-*/agents-* PSA restricted, opslagnamespace privileged; Prune=false,Delete=false | platform-readiness en secrets-invoer |
| Home Assistant | eigen chart, Recreate, 6Gi `/config`, 2Gi limiet | image, UID, integraties, LAN-poorten, eventuele afzonderlijke hardware-uitzondering |
| Paperclip | serverchart, Recreate, 6Gi persistente files, 1Gi limiet | echte build/config/pad, eigen PostgreSQL met 8Gi PVC, scheduler-uit herstel |
| Hermes | eigen chart, Recreate, 8Gi `/opt/data`, 2Gi limiet | exacte image/gatewaycommand/poort/auth/toolbackend en UID |
| Claude/Codex/OpenCode | afzonderlijke charts en namespaces; totaal 8Gi werkdirs, 256Mi wachtlimiet per runtime | echte worker/serverimages, bridge/leasecontract en gedeeld actief taakbudget |
| cert-manager/Envoy Gateway | PR-1-versies en indeling behouden, labels uit | noodzaak, capaciteit, Gateway/TLS/Issuer/adressen |
| UniFi | niet toegevoegd | optionele aparte VM-route; geen stilzwijgende Kubernetes-migratie |

De generieke workloadtemplates zijn een basis, geen bewezen applicatieconfiguratie.
De exacte Paperclip-datadir en mogelijke extra schrijfbare apppaden moeten tegen de
gekozen build worden gecontroleerd. Een TCP-probe bewijst alleen een luisterende
poort; app-authenticatie en functionele health moeten afzonderlijk bewezen worden.
De agentcharts begrenzen nu alleen de wachtende runtime; ze bieden geen dispatcher
en geen vrijgave voor een modelrun. Ze mogen pas aan wanneer de gedeelde limiet en
annulering van alle subprocessen aantoonbaar zijn afgedwongen.

Alle componentlabels staan `false`. De zes charts hebben `enabled: false` en
`runtimeVerified: false`. Alleen inschakelen weigert de render; een echte image
met digest, bestaande Secret, gecontroleerde niet-root UID/GID en poort zijn
verplicht. `runtimeVerified` is een handmatig vrijgaveveld en geen vervanging
voor bewijs. Ook een geldige render geeft geen toestemming voor uitvoering.

De oude eigen Kyverno-policybestanden en oude Cilium-bestanden uit PR 1 blijven
voorlopig als ongerefereerde bron aanwezig. De actieve Kustomizations en de
Kyverno-ApplicationSet laden ze niet. De oude fixturetest valideert geen nieuwe
baseline. De oorspronkelijke ontwikkelaarshandleidingen wachten op herziening.

## Open keuzes en uitvoering

[SMA-149](/SMA/issues/SMA-149) vraagt Peter via Hermien of Argo zijn eerder
gekozen vaste installatiebestand houdt, of ook naar de Helm-structuur gaat.
De bestaande Argo-chart uit PR 1 is bewaard maar uitgeschakeld. Er is nog geen
bootstrap-script dat twee verschillende beheerders naast elkaar installeert.

`preparation-state.yaml` bevat alle resterende uitvoeringsblokkades. Onder meer
local-path-provisioner 0.0.37, echte Talos-volume/nodeselectie, Retain, de lokale
secrets-invoer, Cilium-render en volledige platform-CNPs ontbreken nog.
Schakel de CCNP nooit in vóór die complete allows en bewezen directe API-route;
de voorbereide baseline omvat ook Argo- en Kyverno-pods. Application-waves zijn
geen controller/CRD/webhook-readinessbewijs.

## Controleren

Vereist lokaal: Python 3/PyYAML, Helm, Kustomize; geen clusterverbinding nodig.

```bash
python3 scripts/validate.py
python3 scripts/validate.py --release # hoort zolang ready=false te weigeren
helm lint charts/homeassistant -f helm-values/homeassistant/values.yaml
helm template homeassistant charts/homeassistant -f helm-values/homeassistant/values.yaml
kustomize build manifests/cilium/management
kustomize build manifests/namespaces
```

Herhaal Helm lint/template voor alle zes charts. Test inschakelen zonder gegevens
als negatieve test: de render moet stoppen. Test uitsluitend met fictieve waarden
dat de template resources genereert; presenteer die niet als echte deployment.
Controleer ook de gerenderde upstream policies op Audit, Ignore en de vier
namespace-uitzonderingen. `pre-commit`- en Trunk-configuratie ontbreken nog.

## Beheer en herstel

Private repository: `slacker80/homelab-gitops`, bereikbaar via de bestaande
GitHub-verbinding voor Teun. De bedoelde runtime is het toekomstige Talos-cluster
op de ThinkCentre; exacte host/adressen en live bereikbaarheid zijn niet bewezen.
De bestaande Pi/Hermes/Paperclip zijn niet gewijzigd.

Codevoorbereiding terugdraaien: eigen concept-PR sluiten of, na latere merge,
de voorbereidingscommit met `git revert` terugdraaien. Dit herstelt geen appdata.
Bij latere runtimeproblemen eerst root én betrokken children pauzeren, nieuwe
schrijvers/scheduler/actuaties stoppen, nieuwe writes veiligstellen en een bekende
Git-revisie plus versiepassende externe herstelset gebruiken. Daarna pas sync
hervatten en functie/data verifiëren. Voor een netwerkfout moet de vooraf bewezen
directe API-route beschikbaar zijn; alleen een allow verwijderen heft default-deny
niet op. Nooit namespaces/PVCs als generieke herstelactie verwijderen.

Namespace/PVC-objecten hebben Prune=false,Delete=false; ApplicationSets behouden
childresources bij verwijderen. Het onderliggende PV-Retain en een echte restore
moeten nog worden bewezen. Geen garantie bij handmatig wissen of schijfverlies.
Live uitvoering en herstelproef blijven onder SMA-102 met vooraf geschreven
terugvalplan, back-up en Peters afzonderlijke akkoord. Geen betaalde runs of kosten.
