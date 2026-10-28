# Eén Talos-cluster: bootstrap en overdracht aan Argo

Uitwerking van Peters besluiten SMA-149, SMA-150 en SMA-154; implementatie SMA-155.
Dit is voorbereide code, geen toestemming voor live uitvoering.
De bijbehorende OpenSpec-change staat in `homelab-specs/openspec/changes/gitops-bootstrap/`.

## Gedeelde bron en clusterregistratie

`argocd/cluster-secrets/talos-cluster.yaml` is de enige registratie. Secretnaam
`talos-cluster`, Argo-clusternaam `talos`, server `https://kubernetes.default.svc`.
`talos` is een logische naam, geen hostnaam of DNS-adres. Dit is het lokale
cluster van Argo; er zijn geen externe tokens of certificaten nodig. De registratie
is niet aan één AppProject gebonden, zodat platform én workloads haar kunnen gebruiken.
Alle installatielabels blijven `false`; er is geen tweede cluster of overlay.

Terraform in `homelab-infra/terraform/platform-bootstrap` leest de chartversies
uit `helm-values/versions.yaml`, de basisvalues en `values-talos.yaml` van
`cilium`, `argocd` en `cert-manager`. De drie bijbehorende ApplicationSets lezen
precies dezelfde bestanden. Releasenamen/namespaces:

| Component | Release | Namespace | Label voor Argo-overname |
| --- | --- | --- | --- |
| Cilium | cilium | kube-system | cilium-install |
| Argo CD | argocd | argocd | argocd-install |
| cert-manager | cert-manager | cert-manager | platform/cert-manager |

Gebruik de archieven met SHA256 uit `helm-values/chart-checksums.sha256`.
Cilium-certificaten komen via de certgen-CronJob, zodat renders niet telkens
nieuwe certificaten bevatten. cert-manager bewaart zijn CRDs; automatische prune
staat voor Cilium en cert-manager uit. Gateway API-integratie in cert-manager
blijft uit totdat de Gateway-CRDs zijn ingericht; een Issuer hoort niet bij bootstrap.

## Volgorde voor een latere, afzonderlijk goedgekeurde uitvoering

1. Leg beide exacte repo-commits, doelhost/account, context, directe API-route,
   back-ups, verificatie en terugval op de uitvoeringstaak vast. Deze repo kent
   geen bewezen hostnaam, IP of bereikbaarheid. Voeg voor de private repo een
   read-only sleutel en geverifieerde SSH-hostkey buiten Git toe wanneer SSH
   wordt gebruikt; de bestaande HTTPS-bron vereist bijpassende HTTPS-repocredentials.
2. Terraform installeert na Talos achtereenvolgens Cilium, Argo CD en cert-manager.
   Pas de oude losse Cilium-render niet daarnaast toe. Wacht op controllers en
   CRDs; de netwerkplugin moet bestaan voordat je Ready-nodes kunt verwachten.
3. Richt repositorytoegang, AppProject `platform` en de afzonderlijke `root` in.
   Root gebruikt `main`, map `argocd/`, recursief, met `bootstrap/` uitgesloten.
   Deze credential/root-bootstrap is nog niet als script geïmplementeerd.
   Merge de gereviewde voorbereidings-PR's vóór root Git gaat lezen; `main` is
   momenteel nog leeg. Controleer eerst de root zonder installatielabels.
4. Bewaar Terraform-state buiten Git. De aparte root `platform-handover` gebruikt
   dezelfde state en drie `removed`-blokken met `destroy=false`. Review het plan:
   uitsluitend drie forget-acties, 0 toevoegen/wijzigen/verwijderen. Pas alleen
   dat gecontroleerde plan toe. Controleer daarna dat geen `helm_release` meer in
   die state staat en een tweede handover-plan leeg is. De bootstrap-root mag
   na overdracht nooit opnieuw op deze state worden toegepast.
5. Zet pas daarna de drie bovenstaande labels aan via een gereviewde Git-wijziging.
   Argo neemt dezelfde objecten over met Server-Side Apply. Het bestaande
   Helm-releasesecret blijft staan; gebruik geen `helm uninstall` als opruiming.
6. Controleer alle drie Applications afzonderlijk op Synced én Healthy. De
   Application-healthcheck in de Argo-values maakt dit zichtbaar. Waves op
   gegenereerde Applications garanderen geen volgorde tussen ApplicationSets;
   controller-, CRD- en webhook-readiness blijven expliciete controles.

## Verificatie na uitvoering (hier niet uitgevoerd)

Gebruik steeds de vooraf vastgelegde context, bijvoorbeeld via `kubectl --context
"$cluster_context"`. Controleer minimaal:

- `rollout status daemonset/cilium -n kube-system` en
  `rollout status deployment/cilium-operator -n kube-system`; alle verwachte nodes
  Ready, DNS én verkeer tussen twee pods werken. Een rollout alleen bewijst dat niet.
- `wait --for=condition=Established --timeout=180s crd/ciliumnetworkpolicies.cilium.io`
  en `crd/applications.argoproj.io`, `crd/applicationsets.argoproj.io`,
  `crd/certificates.cert-manager.io` en `crd/issuers.cert-manager.io`.
- Argo application-controller, repo-server, server en ApplicationSet-controller
  zijn uitgerold; `root`, `cilium-talos`, `argocd-talos` en `cert-manager-talos`
  tonen Synced/Healthy. Tweede sync geeft geen onbedoelde diff.
- cert-manager, cert-manager-webhook en cert-manager-cainjector zijn uitgerold;
  de webhook accepteert een apart afgesproken testcertificaat. Dat testobject
  vereist eigen toestemming; deze code maakt geen certificaataanvragen.
- Via `kubectl -n argocd port-forward svc/argocd-server 8443:443` is de lokale
  HTTPS-login bereikbaar. Controleer Cilium/Hubble-fouten en de webhooklogs.

## Terugval en herstel

Codevoorbereiding: sluit de PR of revert na merge de eigen commits.
Vóór overdracht: installatielabels uit laten; Terraform houdt het beheer.
Na overdracht: pauzeer eerst root en de betrokken children (auto-sync én self-heal),
voordat je labels of bronrevisie wijzigt. Een label uitzetten alleen is onvoldoende:
ApplicationSets behouden Applications, en die kunnen dus blijven synchroniseren.
Pauzeer zo nodig ook de ApplicationSet-controller volgens de vooraf goedgekeurde
procedure, zodat hij een handmatige childwijziging niet terugzet. Herstel de
bekende Git-revisie, controleer de render/diff en hervat daarna pas synchronisatie.

Zet niet zomaar een oude Terraform-state terug nadat Argo wijzigingen heeft
uitgevoerd. Eventuele terugoverdracht aan Terraform vraagt een eigen plan met
import/verificatie van de actuele objecten. Verwijder geen CRDs, namespaces,
PVCs of releases als algemene herstelactie. Dataherstel vereist de externe
appdata-/secrets-/etcd-herstelset. Deze herstelroute is niet getest.

## Systeemnotitie

Argo CD beheert configuratie in het toekomstige Talos-cluster op de ThinkCentre;
Cilium verzorgt netwerk en cert-manager certificaten. Locaties binnen Kubernetes
staan in de tabel. Argo is lokaal bereikbaar via bovenstaande port-forward;
exacte host/API-adressen en live herstel zijn nog niet vastgesteld. Bij uitval:
herstel eerst Talos/API en netwerk, daarna de gepinde bootstrap/Git-revisie met
de externe herstelset. De Pi met Hermes en Paperclip is niet benaderd of gewijzigd.

Bronnen: [Application-health](https://argo-cd.readthedocs.io/en/stable/operator-manual/health/),
[Terraform removed](https://developer.hashicorp.com/terraform/language/block/removed),
[cert-manager Helm](https://cert-manager.io/docs/installation/helm/).
