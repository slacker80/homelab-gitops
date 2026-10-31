# Lokale verificatie SMA-175 — 2026-10-31

Lokaal voorbereid op Teuns GitOps-commit `bf9b91b`, in
`/home/peter/sma175-work/gitops`, branch `riekus/sma-175-kubevirt-security`.
De oorspronkelijke Gerrit-werkboom en zijn WIP zijn niet gewijzigd. Geen publicatie
naar GitHub: de zoekactie vond voor Riekus geen bruikbare koppeling. De setup-tool
kon zonder geïndexeerde toolnamen geen toegangskaart maken (422). De afgesproken
lokale commit/patch is daarom de overdracht; geweigerde toegang is niet omzeild.

## Uitgevoerd en lokaal geverifieerd

- `validate.py`: 140 YAML-bestanden leesbaar; alle lokale refs en labels consistent.
- `render-kyverno.sh`: beide chartchecksums 3.9.2 akkoord. Vier Deployments met elk één replica, geen PDB; 17 upstream ValidatingPolicies in Audit/Ignore.
- Kyverno CLI v1.19.2, officiële releasechecksum gecontroleerd: 93 testverwachtingen tegen de echte gerenderde upstream PSS-policies slagen. Vier restricted fixtures, echte operatorpodtemplates, alleen handler uitgezonderd voor negen controles; foutieve namespace/SA/owner, privileged VM/app/agent, ontbrekende seccomp en extra capabilities leveren de verwachte overtreding op. Audit is geen runtime-Deny.
- Bestaande `add-default-security-context`-archieftest: 6 verwachtingen geslaagd. Deze test activeert de eigen policy niet.
- Vijf CNP's tegen het officiële Cilium v1.20.4-CRD-schema gevalideerd. CCNP ongewijzigd; geen world/LAN/CIDR-fallback.
- `render-virtualization.sh`: zeven overlays, 40 objecten, inclusief vier expliciete namespaces en vijf CNP's. KubeVirt/CDI-schema's en vendored checksums akkoord.
- Projectcontrole: alle 20 ApplicationSets hebben toegestane bronnen/bestemmingen. 148 platformobjecten, 98 Kyverno-objecten, 40 virtualisatieobjecten en 13 appobjecten passen bij hun AppProject. De negen securityobjecten ook afzonderlijk gecontroleerd. Geen extra VM-rechten voor agents.
- `render-platform.sh`: Argo, cert-manager en Cilium, checksums/lint en twee identieke renders akkoord.
- `render-apps.sh`: vijf apps, chartchecksum akkoord. `render-gateway.sh`: lint, checksum, herhaalrender, schema en backendcontract akkoord; 8 resources en 5 verwachte negatieve controles.
- Security- en virtualisatie-`--release` weigeren terecht op ontbrekende securityvrijgave. Algemene `validate.py --release` weigert op de bestaande 20 open punten.
- Bash-syntax en `git diff --check` akkoord. Gitleaks 1,14 MB gescand, geen bevindingen.
- `pre-commit run --all-files` en `trunk check` konden niet draaien: beide binaries en hun repo-configuraties ontbreken. Niet als geslaagd gerekend.

Renders/logs blijven buiten Git in `/home/peter/sma175-work/evidence/`.
De controle van AppProject-rechten betreft Argo-objecten; dynamische operatoracties
gebruiken upstream Kubernetes-RBAC.

## Ontbrekende invoer en niet getest

Geen clusterverbinding, admission/CEL op de echte API-server, Cilium-identiteiten,
effectieve NetworkPolicy-unie, CDI-import, virt-launcher-runtime, USB, VM-start,
gast-DHCP, router/VLAN-isolatie, shutdown/reboot, capaciteit of restore bewezen.
De offline handler-/launcherfixtures zijn geen volledige operatorruntime-renders.

De bestaande hardware-, storage-, MAC-, USB- en image/checksum-inputs blijven
vereist. Nieuw expliciet: exacte HTTPS-image-FQDNs plus redirecthosts, router/switch/
VLAN-ontwerp, beoordeling van rechtstreeks verkeer op hetzelfde L2 en echte
admission/netwerkverificatie. De `.invalid`-importpeer en alle vlaggen blijven
onbruikbaar/false. Geen vrijgave of verdere uitvoeringsactie door deze commit.

## Reviewrisico's voor de specs/integratie

1. `apps-unifi-os-server` is nu in deze branch gelijk aan de specs. Combineer met deze namespacecorrectie; Teuns eerdere `apps-unifi` niet alsnog terugbrengen.
2. Restricted VM-namespaces vereisen de toegevoegde KubeVirt RuntimeDefault-seccompconfig; geen generieke privileged uitzondering voor launcher/importer aannemen.
3. PSA is per namespace: kubevirt is privileged; de nauwe Kyverno-uitzonderingen zijn Audit. Kubernetes-RBAC en onafhankelijke controle blijven nodig.
4. Routerregels dekken rechtstreeks verkeer op hetzelfde L2 niet. VM-NIC's via br0 hebben geen Cilium/Hubble-isolatie; nog geen VLAN/routerregels gekozen.
5. Import-SHA256 wordt niet door CDI afgedwongen in dit ontwerp. HTTPS-bronbytes, redirecthosts en scratch/storage blijven afzonderlijke uitvoeringsvoorwaarden.
6. Geen nieuwe eigen Kyverno-policies activeren. Minimumreplica's/zone/PDB zijn inactief; shutdown gebruikt expliciet gestopte gasten, geen generieke drain.
7. Argo-waves zijn geen readinessbewijs. Controleer faseovergangen en operatorgegenereerde netwerkregels; alle platformlabels blijven uit.

Terugval en officiële bronnen staan in [virtualisatie-security.md](virtualisatie-security.md).
Onafhankelijke repo-review wordt door Truus op deze concrete commit uitgevoerd;
runtimeacceptatie blijft bij de afzonderlijke uitvoering onder SMA-173.
