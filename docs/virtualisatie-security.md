# Single-node admission en netwerkgrenzen

Lokaal voorbereid voor SMA-175 op Teuns virtualisatiecommit `bf9b91b`.
Geen apply, sync, hostwijziging of PoC. Alle clusterlabels en vrijgavevlaggen
blijven uit. Dit document beschrijft de repo-configuratie, geen runtimebewijs.

## Admission en namespaces

| Namespace | PSA enforce / warn / audit | Reden en grens |
| --- | --- | --- |
| kubevirt | privileged / restricted / restricted, v1.36 | virt-handler heeft privileged, root, hostPID en hostPath nodig. De operator/API/controller vragen deze rechten niet. Alleen platformbeheerders en upstream controllers horen hier pods te mogen maken. |
| cdi | restricted / restricted / restricted, v1.36 | Operator en controllers gebruiken non-root, drop ALL, geen privilege-escalatie en RuntimeDefault. Geen uitzondering voor imports. |
| apps-homeassistant | restricted / restricted / restricted, v1.36 | HAOS-launcher met USB-resource en importer; geen hostDisk, hostNetwork of privileged Pod toegestaan. |
| apps-unifi-os-server | restricted / restricted / restricted, v1.36 | UniFi-launcher en importer; volgt de bestaande specs. De eerdere Teun-naam apps-unifi is in VM, DataVolume en NAD gelijkgetrokken. |
| Overige apps/agents | bestaande restricted | Geen namespace-, PSS- of projectverruiming. |

De nieuwe `virtualization-security`-Application beheert de vier namespaces en
vijf CNP's. Namespaceverwijdering en prune zijn beschermd. De operatorrenders
bevatten geen Namespace-objecten en nemen deze labels niet over.

PSA kan alleen per namespace uitzonderen. Daardoor is heel kubevirt op PSA-niveau
privileged. De upstream Kyverno-PSS blijft restricted/Audit/Ignore en slaat negen
specifieke controles alleen over bij een Pod met **alle** kenmerken:
namespace kubevirt, label kubevirt.io=virt-handler, ServiceAccount kubevirt-handler
en controller-owner apps/v1/DaemonSet/virt-handler. De overige acht PSS-controles
blijven van toepassing. Dit is rapportage, geen afdwingende blokkade; toegang tot
de namespace moet via Kubernetes-RBAC beperkt blijven. Een label is geen identiteit.

De KubeVirt-CR stelt voor virt-launcher expliciet RuntimeDefault-seccomp in.
De gepinde v1.9.1-code maakt nieuwe VMI's non-root (UID 107), dropt ALL en voegt
alleen NET_BIND_SERVICE toe. De gekozen DataVolume-disks gebruiken PVC/emptyDir,
geen hostDisk. CDI v1.66.1 stelt ook voor de HTTP-importer restricted-compatible
securityContext in. Daarom krijgen launchers en importers geen PSS-uitzondering.
De volledige werkelijk gegenereerde pods en USB-werking zijn nog niet getest.
Nieuwe hostDisk-, root-, sidecar-, hotplug- of andere netwerkmodes vragen herreview.

## Eén node en bestaande eigen policies

Alle vier Kyverno-controllers hebben één replica. De chart rendert daarbij geen
PDB; admissionuitval bij onderhoud is geaccepteerd. Upstream PSS blijft Audit en
alle webhook failure policies blijven Ignore. Een render bewijst geen werkende
admission op Kubernetes 1.36.5.

`require-minimum-replicas`, `require-zone-spread` en `generate-pdb` zijn bestaande
archiefbestanden. Hun Kustomization heeft **geen resources**; ze blijven inactief.
Er komt geen nieuwe eigen Kyverno-policy. Twee replica's of zone-spreiding voegen
op één node geen nodebeschikbaarheid toe. Een gegenereerde PDB is geen veilige
shutdownprocedure. Deze bestanden later activeren vereist een nieuw besluit en
compatibiliteitsreview; de oude developerhandleiding geldt hiervoor niet.

## Podnetwerk

De bestaande CCNP `cluster-default-deny` blijft ongewijzigd: podendpoints buiten
kube-system krijgen ingress/egress default-deny en alleen DNS naar kube-dns.
Er zijn geen nieuwe LAN-, world-, wildcard- of CIDR-allows.

| Bron | Doel | Toestemming in de nieuwe CNP's |
| --- | --- | --- |
| KubeVirt-controllercomponenten | entity kube-apiserver | TCP 443/6443; geen internetegress |
| kube-apiserver | virt-api / virt-operator | TCP 8443 / 8444 voor API en webhooks |
| virt-api | virt-handler, alleen kubevirt | TCP 8186 voor de console-/subresourceverbinding |
| CDI-controllercomponenten | entity kube-apiserver | TCP 443/6443 |
| kube-apiserver | cdi-apiserver | TCP 8443 voor API/webhooks |
| Kyverno-controllercomponenten | entity kube-apiserver | TCP 443/6443 |
| kube-apiserver | Kyverno admission/cleanup | TCP 9443 |
| CDI importer, alleen de twee VM-namespaces | exacte image-FQDNs | uitsluitend TCP 443; nu onbruikbare required-image-source.invalid |

Labels en backendpoorten zijn gecontroleerd tegen de gepinde broncode en renders.
Cilium herkent de API-server via een entity; DNS wordt door de bestaande CCNP
verzorgd. De CNP's gelden voor het primaire Cilium-podendpoint. Kubeletprobes van
de lokale node volgen Ciliums bestaande localhostgedrag; er is geen extra host-allow.

Vervang de `.invalid`-placeholder pas met de bevestigde HTTPS-imagehost(s) en alle
redirecthosts. Leg dezelfde exacte namen vast in `virtualization/security-inputs.yaml`
en controleer de imagebytes/checksum vóór import. Geen matchPattern `*`, world of
heel LAN als herstelactie. FQDN-regels begrenzen IP's die voor de naam zijn opgelost;
ze controleren geen URL-pad of TLS-identiteit. Gedeelde CDN-IP's vragen review.

Upload/clone/export/live-migration en externe metrics zijn niet vrijgegeven.
Andere platformcomponenten hebben nog hun bestaande CNP-voorbereiding nodig vóór
activering van de clusterbaseline. Dit werk maakt de hele stack niet uitrolgereed.
Controleer bij uitvoering ook operatorgegenereerde NetworkPolicies: CNP's en
Kubernetes NetworkPolicies zijn additief. Een extra allow kan de effectieve grens
verruimen. De KubeVirt-code bevat bredere netwerkpolicygenerators; deze zitten niet
in de hier gerenderde operatorobjecten en zijn geen bewijs van runtime-isolatie.

## VM-netwerk buiten Cilium

De gasten krijgen hun LAN-NIC via Multus bridge br0. Die NIC valt buiten Cilium
CNP/CCNP en Hubble. De primaire pod-NIC biedt beheer aan de launcher; een pod-deny
bewijst geen deny op gastverkeer. HAOS .233 en UniFi .235 delen in het huidige
adresplan hetzelfde LAN als Talos .232.

Router/VLAN/firewall-isolatie moet vóór live overname worden uitgewerkt met de
werkelijke router/switch, beheerbronnen, HA-integraties, UniFi-apparaatpoorten,
DNS/NTP/updatebronnen en terugvalroute. Er is geen VLAN-ID of routerregel verzonnen.
Hosts op hetzelfde L2 kunnen rechtstreeks praten en de router passeren daarbij
niet. Alleen een router-ACL beschermt dus niet tegen gast→Talos, gast→gast of
andere hosts op hetzelfde segment. Benodigde VLAN/switchisolatie of gastfirewalls
en het resterende L2-risico moeten expliciet worden beoordeeld. Geen claim dat
Hubble de gastverbindingen registreert of dat Multus die verbindingen isoleert.

## Argo-rechten

`platform` krijgt de vier namespaces en een expliciete cluster-kind-allowlist
voor de bestaande charts plus operators, CDI, CRDs, APIService en PriorityClass.
De oude cluster-wildcard vervalt. De normale `workloads` houdt uitsluitend zijn
bestaande Namespace-clusterrecht; de vervallen HA-chartbron/-bestemming is verwijderd.

De VM-Application gebruikt het nieuwe project `virtual-machines`, met alleen
apps-homeassistant en apps-unifi-os-server, Git als bron, en VM/DataVolume/NAD/PVC
als namespaced kinds. Alleen StorageClass is clusterbreed toegestaan wegens de
bestaande vm-disks-retain in dezelfde overlay. Argo begrenst die toestemming per
kind, niet per objectnaam; de render bevat precies die Retain/WFFC-StorageClass.
Geen nieuwe rechten voor codingagents. AppProjects vervangen het upstream
Kubernetes-RBAC van de operators niet.

## Controle en terugval

```bash
python3 scripts/validate.py
python3 scripts/validate_virtualization.py
scripts/render-kyverno.sh > /eigen/werkmap/kyverno.yaml
python3 scripts/validate_security.py --render /eigen/werkmap/kyverno.yaml
# Optioneel schema: --cilium-crd /pad/naar/cilium-v1.20.4-cnp-crd.yaml
kustomize build manifests/virtualization-security/talos
```

Gebruik Kyverno CLI v1.19.2, passend bij chart 3.9.2. De testcases gebruiken de
gerenderde upstream policies, met restricted fixtures, echte operatorpodtemplates,
en negatieve gevallen voor privilege, namespace-/SA-/owner-spoofing, seccomp en
capabilities. Handgeschreven launcher-/handlerfixtures zijn geen operatorruntime-render.
De bestaande add-default-security-context-fixture blijft een aparte archieftest.

`validate_virtualization.py --release` controleert ook het securitycontract en
weigert zolang security-inputs, imagehosts, runtimeverificatie en overige inputs
ontbreken. Booleans zijn registraties van bewijs, geen vervanging voor bewijs.
Bij uitvoering gefaseerd namespaces, policies, controllers, imports en launchers
controleren, met zowel toegestane als verboden pod- én gastverbindingen. Pas daarna
kan runtimevrijgave worden beoordeeld. De onafhankelijke repo-review staat daar los van.

Terugval voor dit repo-werk: de securitycommit gereviewd reverten; niet de bestaande
namespaces/CRDs/disks verwijderen. Bij latere runtimeproblemen eerst root en children
pauzeren en de laatste goede configuratie herstellen binnen de aparte uitvoering.
Verruim geen privileges of netwerkregels om een mislukte start te verbergen.

## Officiële bronnen

- [Kubernetes PSA-namespacelabels](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/) en [PSS](https://kubernetes.io/docs/concepts/security/pod-security-standards/).
- [KubeVirt v1.9.1 virt-handler](https://github.com/kubevirt/kubevirt/blob/v1.9.1/pkg/virt-operator/resource/generate/components/daemonsets.go), [launcher securityContext/capabilities](https://github.com/kubevirt/kubevirt/blob/v1.9.1/pkg/virt-controller/services/rendercontainer.go), [launcher seccomp](https://github.com/kubevirt/kubevirt/blob/v1.9.1/pkg/virt-controller/services/template.go) en [non-root VMI-default](https://github.com/kubevirt/kubevirt/blob/v1.9.1/pkg/virt-api/webhooks/mutating-webhook/mutators/vmi-mutator.go).
- [CDI v1.66.1 HTTP-importer](https://github.com/kubevirt/containerized-data-importer/blob/v1.66.1/pkg/controller/import-controller.go) en [restricted securityContext](https://github.com/kubevirt/containerized-data-importer/blob/v1.66.1/pkg/controller/common/util.go).
- [Kyverno chart 3.9.2 per-policy excludes](https://github.com/kyverno/kyverno/blob/kyverno-chart-3.9.2/charts/kyverno-policies/values.yaml).
- [Cilium policytypen en additieve werking](https://docs.cilium.io/en/stable/network/kubernetes/policy/) en [KubeVirt Multus-bridge](https://kubevirt.io/user-guide/network/interfaces_and_networks/#multus).
- [KubeVirt v1.9.1 netwerkpolicygenerators](https://github.com/kubevirt/kubevirt/blob/v1.9.1/pkg/virt-operator/resource/generate/components/networkpolicy.go) en [installatiereconciler](https://github.com/kubevirt/kubevirt/blob/v1.9.1/pkg/virt-operator/resource/apply/reconcile.go).
