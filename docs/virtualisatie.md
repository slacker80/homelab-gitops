# Talos met HAOS en UniFi OS Server

Repo-voorbereiding voor SMA-174/SMA-172. Geen installatie, sync, apply of PoC.
Alle labels blijven uit. Een render met `REQUIRED_` is alleen een reviewbestand,
geen toepasbare configuratie. Riekus integreert pas na review van beide branches.

## Beheerkaart

| Systeem | Functie en plaats | Bereikbaarheid (doel) | Herstelroute |
| --- | --- | --- | --- |
| KubeVirt v1.9.1 | Virtualisatie op één M720q/Talos-node, namespace kubevirt | Kubernetes API; virtctl met dezelfde kubeconfig | Bekende gepinde operator/CR, daarna bestaande VM-disks; nooit CRDs verwijderen als reparatie |
| CDI v1.66.1 | Diskimport, namespace cdi | DataVolume-status via API | Herstel operator en gepinde CR; bestaande disks behouden, geen herimport over data |
| Multus v4.2.3 thick | Extra VM-netwerk, kube-system, bridge br0 van Talos | DaemonSet en NAD via API | Vooraf bekende Cilium/Multus-config; eerst directe API/console-route zekerstellen |
| HAOS | UEFI zonder Secure Boot, 2 vCPU/3Gi/32Gi, apps-homeassistant | LAN 192.168.1.233:8123; DHCP-reservering op bevestigde vaste MAC | Retain-disk herkoppelen of externe diskkopie terugzetten; daarna HA-backup en USB-inventaris herstellen |
| UniFi OS Server | Linux-gast, 2 vCPU/4Gi/20Gi, apps-unifi | LAN 192.168.1.235; gastconsole via virtctl; HTTPS-poort bij installatie bevestigen | Bestaande gastdisk of externe kopie herstellen; gepinde OS Server-hostinstaller en UniFi-export gebruiken |
| vm-disks-retain | Local-path StorageClass op dezelfde SSD; RWO/Filesystem, Retain/WFFC | PVC/PV via API | Bestaande PV en data-inhoud identificeren en onder review herkoppelen; Retain is geen back-up |

Dit zijn doeltoestanden, geen aangetoonde bereikbaarheid of herstelproeven.
Adresplan: .231 reserve, .232 Talos, .233 HAOS, .234 reserve, .235 UniFi,
gateway/DNS .1 op 192.168.1.0/24; LB .240-.247. Geen live migratie.
Beide gasten gebruiken alleen de Multus-NIC; de virt-launcher-pod houdt zijn
Kubernetes-beheernetwerk. De NAD heeft lege IPAM: de gast zelf doet DHCP.
`br0` is de Talos 1.14 BridgeConfig uit homelab-infra, geen Kubernetes-bridge.

## Pins en verplichte invoer

`virtualization/versions.yaml` bevat de bron-URL, exacte versie en werkelijk
berekende SHA256 van ieder ongewijzigd vendored manifest. Kustomize-patches
staan apart. Multus' tagmanifest verwees naar snapshot-thick; beide containers
worden daarom naar de gecontroleerde GHCR-indexdigest voor v4.2.3-thick omgezet.
Een manifestchecksum bewijst de bronbytes; het is geen handtekening of runtimebewijs.
KubeVirt/CDI houden de images uit hun officiële releasemanifesten.

Vul `virtualization/required-inputs.yaml` én de bijbehorende manifesten in:

- Echte vaste MACs, DHCP-reserveringen .233/.235, HAOS qcow2.xz-image en Linux amd64-gastimage met versie, immutable HTTPS-URL en lokaal gecontroleerde SHA256. Geen fictieve digests. De Linux-image moet een bruikbare login/herstelconsole hebben; credentials nooit in Git.
- HAOS-image moet UEFI en virtio ondersteunen; import van xz/qcow2 via CDI en uitbreiden naar 32Gi zijn nog niet getest. De UniFi-gast gebruikt BIOS; kies een BIOS-geschikt Linux-image met systemd dat de actuele OS Server-eisen ondersteunt.
- USB vendor/product, aantal en fysieke identiteit. De huidige `ha-usb`-groep is een verplichte invoerplek, geen claim dat één apparaat volstaat. Bij meerdere sticks de selectors/resourcegroepen en hostDevices samen aanpassen. Vendor/product selecteert geen serienummer: twee identieke sticks mogen niet onbedoeld verwisselen. Geen USB-fallback zonder Peters besluit.
- UniFi **OS Server-hostinstaller**: exacte versie, officiële URL en SHA256. Installer later in de Linux-gast uitvoeren; geen Network-only-container/chart. De hostinstaller is niet ingebakken of uitgevoerd. Gast-OS, Podman-afhankelijkheden, benodigde poorten, login en herstelpad moeten vóór vrijgave bevestigd zijn.
- Bevestigde Talos UserVolume/diskindeling, beschikbare capaciteit en local-path-provisioner met dezelfde provisionernaam. Deze branch installeert de provisioner niet en verzint geen SSD-pad. Controleer provisionerconfig: filesystem op de bedoelde persistente Talos UserVolume, geen vluchtige rootfs, voldoende scratchruimte voor CDI. De StorageClass bewaart PVs bij PVC-verwijdering.
- Externe consistente VM-diskkopieën, HA-backup en UniFi-export met herstelrechten en een uitvoerbaar herstelplan. Alle reviewvlaggen blijven false tot het bewijs er is.

CDI verifieert in dit ontwerp de opgegeven SHA256 niet zelf. Vóór een echte import
moet de operator de download lokaal tegen die SHA256 controleren en dezelfde bytes
op een onveranderlijke HTTPS-bron aanbieden. Zonder dat bewijs geen import.

## Integratiegrens voor Gerrit

Deze branch verandert geen Kyverno, policies, CNPs, PSA of AppProject-security.
De Applications zijn daarom bewust nog niet activeerbaar. Gerrit levert op zijn
branch de namespaces en gerichte toestemmingen vóór `platform/virtualization=true`.
Geen `CreateNamespace=true`: namespaces moeten expliciet gereed zijn. De upstream Namespace-objecten zijn uit de render gefilterd, zodat deze Applications Gerrits namespacebeheer niet overnemen.

| Namespace/gebied | Benodigde resources en review |
| --- | --- |
| kubevirt | Operator Deployment/ServiceAccount/RBAC; KubeVirt-CR; door operator gemaakte virt-api/controller/handler, webhooks, services, secrets en jobs. Infra en operator ieder één replica, virt-template uit; HostDevices-featuregate aan voor USB. Privileged/hostPath/KVM/USB en runtimepolicies gericht beoordelen. |
| cdi | CDI-operator en gegenereerde API/controller/uploadproxy/RBAC/webhooks; CDI-CR is clusterbreed. Import- en scratchpods moeten mogen draaien. |
| kube-system | Multus thick DaemonSet, initcontainer, ConfigMap/ServiceAccount/RBAC; privileged, hostPID/hostNetwork en hostPaths naar CNI/run/kubelet. Cilium cni.exclusive=false in beide repos. |
| apps-homeassistant | VM haos, DV/PVC haos-disk, NAD lan-br0, virt-launcher, importer/scratchpods; USB resource kubevirt.io/ha-usb. |
| apps-unifi | VM unifi, DV/PVC unifi-disk, NAD lan-br0, virt-launcher, importer/scratchpods. |
| clusterbreed | KubeVirt/CDI/VM/NAD-CRDs, ClusterRoles/Bindings, webhooks/APIServices, PriorityClass en StorageClass vm-disks-retain. AppProject platform/workloads moeten de juiste bronnen, bestemmingen en kinds toestaan. |

De lijst omvat ook wat de operators dynamisch aanmaken; alleen de declaratieve
CR toestaan is onvoldoende. Gerrit bepaalt uitzonderingen op replica's,
securityContext, serviceaccounts, probes, images en hosttoegang. Controleer ook
namespace-selectors en netwerktoestemming voor operator/API/webhooks/importers.
Verkeer op de VM-NIC via br0 valt buiten Cilium/CNP/Hubble: LAN-isolatie hoort
bij router/VLAN/firewall, waarvan keuzes en toegestane toegang nog ontbreken.

## Volgorde en verificatie

1. Talos br0, storage/UserVolume en Cilium voorbereiden; Gerrits namespaces/security integreren. Alle inputs verifiëren; `python3 scripts/validate_virtualization.py --release` moet slagen. Deze controle verleent geen toestemming voor uitvoering.
2. Operatoren/Multus (wave 4), daarna KubeVirt/CDI-CR (wave 5), dan opslag/NADs/VMs (wave 6). App-wave is geen bewijs van CRD/webhook-readiness: bij uitvoering per fase wachten en foutsignalen beoordelen vóór volgende activering.
3. Bewijs exact één infra/operatorreplica, geen virt-template, werkende CDI-import, virt-launcher/USB-toewijzing, gast-LAN-adressen, HA-integraties en UniFi-apparaten Online. Controleer geen ongewenste migratie of tweede netwerkinterface in de gast.
4. Gastgrace is 120s; Talos' prioriteitsgroepen reserveren 150s voor prioriteit 0 en daarna 30s/30s. Shutdown, reboot, opslagherstel, USB en herstart met Always zijn nog niet live bewezen.

Lokaal: `python3 scripts/validate.py`, `bash scripts/render-virtualization.sh`,
KubeVirt/CDI-CRD-schema’s, alle gewijzigde Kustomize-overlays en de bestaande app/platform/Gateway-renders.
`validate.py --release` blijft terecht weigeren zolang andere apps ook blokkades hebben.

## Home Assistant Gateway

De Helm-app, values en container/PVC-manifesten zijn verwijderd. De HA-route én
listener zijn verwijderd om een backend naar de verdwenen Service te voorkomen.
Gebruik later alleen de bevestigde LAN-toegang .233:8123. Een nieuwe Gateway-route
vereist een bewezen selectorloze Service/EndpointSlice of andere ondersteunde
backend, TLS/auth en netwerktoestemming onder aparte review. De drie resterende
routes blijven ClusterIP met deny-all. Bestaande oude HA-data wordt niet verwijderd:
Argo-prune van een oude installatie eerst gericht beoordelen en externe back-up maken.

## Terugval

Repo: PR sluiten of na merge gereviewde revert. Tijdens een echte installatie
vóór iedere wijziging laatste goede Git-revisie, nodeconfig, PV-identiteit en
externe back-ups bewaren. Pauzeer root én children vóór terugval; labels uitzetten
laat bestaande Applications bestaan. VM en DataVolume hebben Prune=false,Delete=false;
ApplicationSets bewaren resources en hebben prune=false. Dit beschermt niet tegen
handmatige verwijdering, SSD-uitval of een kapotte provisioner.
Bij een configuratiefout de bekende Git-revisie herstellen en pas dan gericht syncen.
Bij datafout de gast stoppen binnen de goedgekeurde uitvoering, de disk behouden,
een nieuwe herstelkopie herstellen en pas na verificatie de VM eraan koppelen.
Geen CRD-, namespace- of PVC-delete als algemene reparatie. Retain-PVs expliciet
herkoppelen onder review; geen lege herimport over bestaande gegevens. Hostverlies:
eerst Talos/etcd/USB/br0/storage terug, daarna operatoren en de bewaarde disks,
dan HA-backup en UniFi-export. De Pi met Hermes/Paperclip wordt niet benaderd.

Bronnen: [Talos KubeVirt](https://docs.siderolabs.com/talos/v1.14/advanced-guides/install-kubevirt),
[Multus op Talos](https://docs.siderolabs.com/kubernetes-guides/cni/multus),
[KubeVirt host devices](https://kubevirt.io/user-guide/compute/host-devices/),
[CDI ondersteunde import](https://github.com/kubevirt/containerized-data-importer/blob/v1.66.1/doc/supported_operations.md).
