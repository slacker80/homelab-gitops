# Eén Talos-cluster: bootstrap en Argo-overname

Actieve route na Peters bootstrapkeuze (SMA-172/SMA-174). Geen live uitvoering.
De scripts en niet-geheime Talos-patches staan in homelab-infra; zie daar
`docs/helm-bootstrap.md`. Bestaande Terraform-state eerst inventariseren;
geen destroy, uninstall of nieuwe clusteridentiteit bij een bestaand cluster.

## Identiteiten en gedeelde bron

`argocd/cluster-secrets/talos-cluster.yaml` blijft de enige registratie: secret
`talos-cluster`, clusternaam `talos`, server `https://kubernetes.default.svc`.
Dit is een logische clusternaam; fysieke node .232/hostnaam staat los daarvan.
Alle installatie- en applabels blijven false in deze voorbereiding.

| Component | Chartpin | Release / namespace | Beheer |
| --- | --- | --- | --- |
| Cilium | cilium 1.20.4 | cilium / kube-system | Eenmalig Helm; daarna cilium-talos via cilium-install |
| Argo CD | argo-cd 10.2.0 | argocd / argocd | Eenmalig Helm; daarna argocd-talos via argocd-install |
| cert-manager | cert-manager v1.21.0 | cert-manager / cert-manager | Meteen Argo via platform/cert-manager; geen bootstraprelease |

Exacte GitOps-commit, `helm-values/versions.yaml`, `chart-checksums.sha256`, basisvalues
én `values-talos.yaml` worden voor bootstrap en Argo gelijk gehouden. Cilium Hubble
gebruikt de certgen-CronJob; dubbele renders blijven gelijk. Argo gebruikt
`application.resourceTrackingMethod: annotation`: Applicationnamen verschillen van
releaseName, maar app.kubernetes.io/instance-labels/selectors moeten gelijk blijven.
cert-manager-CRDs blijven behouden, geen Issuer/Certificate tijdens bootstrap.
Envoy/Gateway komen uitsluitend later via Argo; Cilium Gateway API blijft uit.

## Volgorde en controlepunten

1. Uitvoeringstaak met doelhost/account, exacte beide commits, Peters akkoord,
   geschreven rollback, externe versleutelde herstelset en bewezen directe
   laptop→Talos/API plus console. SSD/NIC/USB/MAC/storage zijn verplichte echte inputs.
2. Talosctl gen secrets/config (één cp, Kubernetes **1.36.5** expliciet), offline
   metal-validatie, externe secretskopie. Apply op bevestigde onderhouds-API,
   daarna één keer bootstrap van nieuw etcd en aparte kubeconfig. Directe
   CA-gecontroleerde API .232:6443 en `/readyz` incl. etcd vóór Cilium controleren.
   Node Ready en pod-DNS zijn op dit moment nog geen geldige acceptatie-eis.
3. Cilium Helm vanuit gechecksumd archief, release/values zoals hierboven. Talos
   ResolverConfig zet hostDNS.enabled/forwardKubeDNSToHost true; Cilium zet daarom
   bpf.hostLegacyRouting=true. Offline renderbewijs: cilium-config
   enable-host-legacy-routing="true", cni-exclusive="false". Nu pas agent/operator,
   node Ready, CoreDNS, interne én externe DNS en podverkeer verifiëren.
   Er wordt niet automatisch een onbeoordeeld testpodimage uitgerold: kies/pin
   de testfixture en toegestane bestemmingen op de uitvoeringstaak.
4. Argo Helm met dezelfde chart/values, controllers en CRDs controleren; lokale
   HTTPS-login via `kubectl --context <context> -n argocd port-forward
   svc/argocd-server 8443:443`. Repositorytoegang met read-only credentials buiten
   Git. Bij HTTPS de passende repocredentials; bij SSH geverifieerde hostkey.
   Wacht op repo-servertoegang en noteer de exacte gereviewde main-revisie.
5. Infra root-fase maakt alleen project platform en root aan. Root leest
   main/argocd recursief met bootstrap uitgesloten. Laat alle labels false;
   verifieer root Synced/Healthy én juiste revisie vóór overname.
6. Vergelijk `helm get metadata`, `helm get values --all` en `helm get manifest`
   van beide bestaande releases met dezelfde gepinde lokale renders en de
   verwachte Argo-bronnen. Bewaar deze mogelijk gevoelige output alleen in de
   externe privéherstelset. Identiteiten/versies/namespaces/selectors moeten
   gelijk zijn; alleen verklaarde tracking-/beheerannotaties zijn toegestaan.
   Controleer ook live CRDs/API-compatibiliteit. Onverklaarde diff: stoppen.
7. Infra handover-fase schrijft ARGO-OWNS-lock vóór labelactivatie. Vanaf dan
   geen Helm/Terraform-install/upgrade/rollback naast Argo. Helm-release-Secrets
   blijven staan; verwijder of uninstall de releases niet. Scripts controleren
   zowel lokale lock als live Argo-labels/Applications, zodat een ontbrekende
   lock op een andere laptop geen toestemming voor een tweede schrijver wordt.
8. De templates voor cilium en argocd hebben aanvankelijk automated.enabled=false.
   Zet pas na de lock via een gereviewde Git-commit cilium-install/argocd-install
   true. ApplicationSet maakt nu de twee children aan met automatische sync uit.
   Controleer namen, releaseName, chart/values, namespace/server en exacte revisie;
   review `argocd app diff cilium-talos` en `argocd app diff argocd-talos` vóór de
   eerste handmatige sync. Geen onverklaarde selectorwijzigingen of verwijderingen.
   Synchroniseer afzonderlijk volgens de goedgekeurde uitvoeringstaak; geen prune.
   Pas na de verificatie activeert een tweede gereviewde Git-commit
   automated.enabled=true in beide templates. Self-heal wordt dan actief;
   scripts blijven permanent geblokkeerd. Deze twee reviewstappen zijn expliciet
   onderdeel van de overdracht en worden hier niet live uitgevoerd.
9. cilium-talos en argocd-talos afzonderlijk Synced/Healthy, daarna tweede sync
   zonder onbedoelde diff. Cert-manager-label in een volgende gereviewde stap
   aan; controllers, CRDs en webhook gereed voordat afhankelijke resources volgen.
   Waves tussen ApplicationSets garanderen geen readiness of onderlinge volgorde.

Gebruik voor Kubernetes-controles uitsluitend de aparte kubeconfig en expliciete
context. Controleer CRDs Established, Cilium DS/operator, Argo application-controller,
repo-server/server/ApplicationSet-controller, root en children; na cert-manager
ook cert-manager/webhook/cainjector. Controleer foutsignalen en functionele DNS/pod-
communicatie opnieuw na overname. Een testcertificaat vraagt een afzonderlijk
beoordeelde fixture; deze voorbereiding maakt geen Issuer of Certificate.

## Terugval en herstel

Repo: PR sluiten vóór merge, daarna gereviewde revert. Voor de eerste sync kan de
gepauzeerde overdracht worden afgebroken met behoud van de bestaande werkende
Helm-objecten; geen uninstall. Een gedeeltelijke installatie vraagt inspectie,
geen blinde herhaling. Na Argo-overname eerst root, children en ApplicationSet-
reconciliatie gecontroleerd pauzeren; herstel bekende Git-revisie, render/diff
reviewen en dan sync hervatten. Alleen labels false zetten is onvoldoende:
behouden Applications blijven schrijven. Helm-administratie is geen actuele
terugvalbron na Argo-wijzigingen; geen oude Helm-rollback of Terraform-state
terugzetten zonder apart plan voor actuele eigenaarschapsoverdracht.

Bij hostverlies eerst Talos/API/etcd met dezelfde clusteridentiteit en bekende
snapshot herstellen, daarna Cilium, Argo en Git. VM-disks/PVCs en HA/UniFi-data
vereisen eigen externe back-ups. Geen CRDs/namespaces/PVCs leeg verwijderen of
gasten opnieuw importeren als algemene herstelactie. Lock niet verwijderen om
bootstrap als tweede schrijver te gebruiken. Restore is nog niet getest.

## Beheerkaart en integratiegrens

| Systeem | Wat en waar | Bereiken | Herstel |
| --- | --- | --- | --- |
| Talos/Kubernetes | Bare-metal M720q, doel 192.168.1.232 | Talos 50000/clientcert, Kubernetes 6443/CA | Zelfde secrets/nodeconfig, gepind ISO/installer en etcd-snapshot |
| Cilium | Podnetwerk op dezelfde node, kube-system | Directe API/Cilium-status, Hubble via interne service | Bekende Git-values, directe API/console, gerichte goedgekeurde terugval |
| Argo CD | Configuratiebeheer op dezelfde node, argocd | Lokale HTTPS port-forward 8443:443 | Gepinde chart/Git-bron en repo/secrets uit externe herstelset |
| cert-manager | Certificaten op dezelfde node, cert-manager | API en webhookstatus | Gepinde Argo-bron, beschermde CRDs en externe secrets |
| HAOS / UniFi OS Server | KubeVirt-gasten M720q, .233 / .235 | Gast-LAN, .233:8123; UniFi-poorten nog bevestigen | Retain-opslag, externe VM-disk/HA-back-up/UniFi-export |

Adressen zijn ontwerpdoelen, geen bereikbaarheidstest. Pi/Hermes/Paperclip niet benaderd.
Gerrits securitydelta blijft apart: `de602a7` op basis `bf9b91b`, in
`/home/peter/sma175-work/gitops`. Deze delta verandert geen securitybestanden.
Riekus integreert na review; neem Gerrits `apps-unifi-os-server`-correctie, PSA,
AppProjects, namespaces en policies mee vóór activering. Bestaande virtualisatie-
input/storageblokkades blijven staan. Zie `virtualisatie.md` en de reviewtaak.

Bronnen: [Cilium op Talos](https://docs.cilium.io/en/stable/installation/k8s-install-talos-linux/),
[Argo Helm releaseName](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/#helm-release-name),
[Argo tracking](https://argo-cd.readthedocs.io/en/stable/user-guide/resource_tracking/),
[Talos startprocedure](https://docs.siderolabs.com/talos/v1.14/getting-started/getting-started).
