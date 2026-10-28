# Gateway API — SMA-156

Dit is broncodevoorbereiding voor het ene toekomstige Talos-cluster op ThinkCentre.
Geen uitrol, DNS-wijziging of migratie van de huidige Pi-diensten. Alle labels blijven
`false`; het cluster, API-adres en de LAN/VPN-adressen zijn hier niet vastgesteld.

## Beheer en volgorde

Envoy Gateway gebruikt de bestaande pin `gateway-helm` **1.8.3** via
`oci://docker.io/envoyproxy/gateway-helm`. De chartarchive heeft een SHA256-lock.
De expliciete gedeelde values en Talos-override horen bij dezelfde ApplicationSet.
Argo beheert de controller én de bij deze chart gebundelde Gateway API- en
Envoy-CRDs (`crds.enabled=true`, `skipCrds=false`). Geen tweede CRD-installatie,
geen Terraform-release voor Envoy en geen Cilium Gateway-controller. Terraform
blijft uitsluitend de drie SMA-155-bootstrapreleases beheren tot handover.
Er is daarom geen aanvullende infra-code nodig in infra-PR 3.

1. Na apart uitvoeringsakkoord: rond SMA-155-bootstrap en overdracht af. Laat
   `platform/gateway-routes=false`.
2. Activeer eerst alleen Envoy. Controleer CRDs Established, controller Available,
   webhooks/certgen en stabiele tweede sync. Een sync-wave bewijst die volgorde niet.
3. Zorg dat de vier backendnamespaces/services bestaan. Hubble UI is expliciet
   opgenomen in de Cilium-values; gewone Ingress en Cilium Gateway API blijven uit.
4. Kies en realiseer de toegang en certificaten hieronder. Controleer de aanvullende
   Cilium-netwerktoestemming voor proxy → backend; de bestaande default-deny wordt
   niet versoepeld door deze voorbereiding. Home Assistant vereist ook gecontroleerde
   `use_x_forwarded_for`/`trusted_proxies` in zijn eigen config, en Paperclip een
   gecontroleerde publieke basis-URL/hosttoelating tegen de gekozen build.
5. Pas daarna mag een apart gereviewde wijziging `platform/gateway-routes=true`
   selecteren. De ApplicationSet vereist ook `platform/envoy-gateway=true`.

Beide nieuwe beheergrenzen gebruiken behoud bij ApplicationSet-verwijdering en
geen automatische prune. Dat beschermt CRDs, maar betekent ook dat een verwijderd
manifest bewust opgeschoond moet worden; labels uitzetten verwijdert niets en
stopt bestaande Applications niet.

## Routes en systeemnotities

Hostnamen zijn **voorstellen**, geen bestaand DNS en geen goedgekeurde publicatie.
Alle routes zijn uitsluitend intern bedoeld; geen enkele route is extern bedoeld.

| Systeem en functie | Voorgestelde URL | Locatie/backend in Talos | Herstelroute |
| --- | --- | --- | --- |
| Envoy, toegangspoort voor webverkeer | Geen eigen UI | Controller/proxy: `envoy-gateway-system`; Gateway `admin`, class `envoy-internal` | API en netwerk herstellen, bekende chart/values/Git-revisie terug, TLS-Secrets uit beveiligde herstelset; CRDs behouden |
| Argo CD, configuratiebeheer | `https://argocd.admin.home.arpa` | `argocd/argocd-server:443` | Directe API-toegang en bestaande port-forward; gepinde bootstrap en Git/config/secrets herstellen |
| Home Assistant, woningautomatisering | `https://homeassistant.admin.home.arpa` | `apps-homeassistant/homeassistant-home-assistant:8080` | Vastgelegde image/config/PVC en externe backup terug; integraties controleren |
| Paperclip, taakbeheer | `https://paperclip.admin.home.arpa` | `apps-paperclip/paperclip-server:3100` | Consistente database-dump, bestanden en sleutels samen herstellen; Pi blijft buiten deze wijziging |
| Hubble, netwerkweergave | `https://hubble.admin.home.arpa` | `kube-system/hubble-ui:80` | Eerst Cilium en relay herstellen, daarna Cilium-values opnieuw synchroniseren; geen UI-database |

cert-manager (`cert-manager`) verzorgt certificaten en heeft geen UI. Kyverno heeft
geen UI in deze configuratie. Hermes heeft hier geen HTTP-Service/UI, en de drie
coding-workers evenmin: daarom geen verzonnen backendpoorten of routes. UniFi en
andere externe diensten zijn niet als backend opgenomen; hun exacte locatie,
verbinding en toegang moeten eerst afzonderlijk worden vastgesteld. Dit zijn
herstelroutes op papier; geen restore is getest en backupbeschikbaarheid is nog
niet bewezen.

## Veilige uitgangsstand en TLS

De proxy heeft uitsluitend een **ClusterIP**: geen LoadBalancer, NodePort,
hostNetwork of openbaar IP. Vier HTTPS-listeners op 443 staan alleen HTTPRoutes
uit de bijbehorende namespace toe. Backends staan in dezelfde namespace als hun
route; er zijn geen ReferenceGrants of wildcardhosts. Er is geen HTTP-listener.

`admin-deny-all` is een Gateway-brede Envoy SecurityPolicy met `defaultAction: Deny`
en zonder allowregels. Zelfs na activering wordt geen webverkeer toegelaten.
Voor bruikbaar intern verkeer moet Peter vooraf een concrete keuze kunnen
reviewen: toegang via welke LAN/VPN-route, welke bronadressen en welke login.
Hubble heeft geen ingebouwde gebruikerslogin; alleen intern noemen is geen
beveiliging. Behoud deny-all tot die keuze is uitgewerkt en getest. Geen brede
privénetwerk-allowlist, geen ongeverifieerde X-Forwarded-For-vertrouwensketen.

Elk listener verwijst naar `<component>-admin-tls` in `envoy-gateway-system`.
Gebruik na PKI-keuze cert-manager Certificates met die secretNames en een
gecontroleerde Issuer. Voor `home.arpa` is een vertrouwde interne PKI nodig;
geen publiek ACME-certificaat veronderstellen. Issuer/Certificate-objecten en
secretmateriaal worden bewust niet verzonnen. Een ontbrekend TLS-Secret mag
geen terugval naar HTTP geven. Sleutels en certificaten blijven buiten Git.

Argo blijft zelf HTTPS gebruiken (`server.insecure=false`). De BackendTLSPolicy
vereist de DNS-SAN `argocd-server.argocd.svc` en de publieke CA via ConfigMap
`argocd/argocd-server-ca` (`ca.crt`, buiten Git). Configureer het servercertificaat
via de bestaande cert-manager/PKI-procedure met die SAN. Geen TLS-skip-verify.
Zolang die CA/certificaten ontbreken is dit doelbewust geen werkende Argo-route.

## Verificatie en terugval

Lokaal: `bash scripts/render-gateway.sh` (Helm, Kustomize, PyYAML en jsonschema nodig).
Het script controleert de chartlock, vijf lints, een identieke dubbele Envoy-render,
CRD-schema's uit exact die chart, namespaces/hosts/TLS/policy, backendnamen en
poorten tegen echte renders van vier charts, plus vijf negatieve gevallen.
JSON-schema valideert geen CEL-regels en bewijst geen controllerfunctie.
Bij weinig ruimte in `/tmp`: kies `TMPDIR` in de werkruimte; verwijder geen
bestanden van andere processen.

Later live te bewijzen, pas na akkoord: Gateway Accepted/Programmed,
HTTPRoutes Accepted/ResolvedRefs, SecurityPolicy Accepted, BackendTLSPolicy
Accepted/ResolvedRefs en certificaatketens/SAN. Bewijs eerst deny-all (403 of
weigering), daarna de afgesproken toegang en weigering voor andere bronnen,
verkeerde host en verkeerde route-namespace. Controleer WebSockets bij Home
Assistant/Paperclip, Argo-login/API, Hubble-relay, default-deny en tweede sync.

Broncode terug: revert uitsluitend de SMA-156-commit op de bestaande PR-branch.
Vóór iedere runtimewijziging komt het concrete terugvalplan op de uitvoeringstaak.
Bij een later toegangsprobleem: houd directe Kubernetes-API-toegang beschikbaar,
pauzeer root/child-auto-sync én zo nodig ApplicationSet-reconciliatie, sluit de
nieuwe toegangsroute, herstel de laatste bekende Git-revisie en externe TLS-set,
controleer diff en hervat pas daarna. Een Git-revert verwijdert door `prune=false`
geen oude routes: verwijder uitsluitend de geïdentificeerde SMA-156-routes/Gateway
via een apart goedgekeurde en gecontroleerde beheeractie als die niet behouden
mogen blijven. Verwijder nooit CRDs, namespaces, PVC's of releases als algemene
terugvalactie. Geen Pi-container, service of pakket wordt hiervoor gewijzigd.

Bronnen: [Envoy IP-beperking](https://gateway.envoyproxy.io/latest/tasks/security/restrict-ip-access/),
[Envoy deployment modes](https://github.com/envoyproxy/gateway/blob/main/site/content/en/v1.8/tasks/operations/deployment-mode.md).
De lokaal gecontroleerde chart-CRDs zijn leidend voor de schemastructuur.
