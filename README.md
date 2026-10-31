# Homelab GitOps

GitOps-configuratie voor het homelab, beheerd door Argo CD. ApplicationSets
selecteren het ene Talos-cluster via labels op Argo CD cluster-Secrets.

## Werking

De root-Application in `argocd/bootstrap/root-app.yaml` leest recursief
`argocd/` uit `https://github.com/slacker80/homelab-gitops.git` op `main`.
Argo CD en toegang tot deze repository moeten vooraf zijn ingericht.
De root gebruikt het AppProject `platform`; dat moet bij bootstrap ook bestaan.

`argocd/cluster-secrets/talos-cluster.yaml` registreert het lokale cluster
als `talos` via `https://kubernetes.default.svc`. Het bestand bevat geen
externe clustercredentials. De labels schakelen de volgende componenten in:

| Label | Component |
| --- | --- |
| `argocd-install=true` | Argo CD zelfbeheer (na de Terraform-bootstrap) |
| `cilium-install=true` | Cilium zelfbeheer (na de Terraform-bootstrap) |
| `platform/cilium=true` | Cilium-netwerkpolicies; Cilium moet al geïnstalleerd zijn |
| `platform/kyverno=true` | Kyverno |
| `platform/kyverno-policies=true` | Pod Security Standards en aanvullende policies |
| `platform/cert-manager=true` | cert-manager |
| `platform/envoy-gateway=true` | Envoy Gateway-controller en gebundelde CRDs |
| `platform/gateway-routes=true` | Interne Gateway API-resources, vereist ook Envoy-label |
| `apps/<app>=true` | Paperclip, Hermes, Claude-, Codex- en OpenCode-worker |

## Indeling

- `argocd/`: root-Application, AppProjects, ApplicationSets en clusterregistratie.
- `helm-values/`: componentinstellingen en centrale chartversies in `versions.yaml`.
- `manifests/`: Cilium- en Kyverno-policies en per app de PVC's, met een `talos`-overlay.
- `docs/`: handleidingen voor netwerkpolicies, pod security en secrets.
- `tests/kyverno/`: bestaande regressietests voor een securityContext-variant.
- `scripts/`: lokale validatie en renders zonder clusterverbinding.

Apps gebruiken een upstream-chart waar die bestaat: de generieke bjw-s app-template voor Hermes, Paperclip
en de drie workers. Namespaces maakt Argo aan via `CreateNamespace=true`
met PSA-labels in `managedNamespaceMetadata`; er is geen aparte namespace-app.
PVC's staan als extra manifest met `Prune=false,Delete=false`, zodat data blijft
staan als een Application verdwijnt.

## Status

Conceptvoorbereiding voor SMA-94: alle clusterlabels staan `false`. Zie
[voorbereiding](docs/voorbereiding.md), [Terraform-bootstrap](docs/terraform-bootstrap.md)
en [open punten](preparation-state.yaml).

## Toegang en inrichting

Argo CD gebruikt de lokale adminlogin en serveert HTTPS via een ClusterIP-service.
Voor lokale toegang kun je `kubectl -n argocd port-forward svc/argocd-server 8443:443`
gebruiken. Repositorycredentials en wachtwoorden worden buiten deze repo beheerd.

Envoy Gateway en drie interne HTTPS-routes zijn voorbereid; zie
[Gateway API](docs/gateway-api.md) voor hostnaamvoorstel, beheer, TLS,
toegangsblokkade en herstel. ClusterIP en deny-all voorkomen publicatie.
cert-manager heeft nog geen gekozen Issuer; alle installatielabels blijven uit.

De bestaande replica-aantallen, resourcebudgetten en policies zijn behouden.
Controleer of ze bij de capaciteit van je homelab passen. Workloadpolicies
vereisen onder meer minimaal twee replica's en expliciete netwerktoestemming.

## Aanpassen en controleren

Chartversies staan in `helm-values/versions.yaml`. Optionele overrides heten
`helm-values/<component>/values-<cluster>.yaml`. De clusteroverride heet `talos`; er is geen afzonderlijk managementcluster.

Controleer lokaal zonder resources toe te passen:

```bash
kubectl kustomize manifests/cilium/talos
kubectl kustomize manifests/kyverno-policies/talos
kyverno test tests/kyverno/add-default-security-context
python3 scripts/validate.py
bash scripts/render-platform.sh  # Argo CD, cert-manager en Cilium: checksum, lint, stabiele render
bash scripts/render-gateway.sh # Envoy, CRD-schema en service-/routecontracten
scripts/render-apps.sh      # app-charts, met checksumcontrole
scripts/render-kyverno.sh   # Kyverno-charts, met checksumcontrole
```

Werk bij een chartversie ook `helm-values/chart-checksums.sha256` bij.

De Kyverno-test gebruikt `policy.yaml` in de testdirectory als fixture voor de
variant die expliciete securityContext-waarden behoudt; hij valideert niet de
actieve baselinepolicy.

Argo CD verzorgt de uitrol na publicatie. Lokale wijzigingen zijn geen bewijs
dat de configuratie al op een cluster draait.

HAOS en UniFi OS Server zijn als KubeVirt-gasten voorbereid. Zie [virtualisatie](docs/virtualisatie.md) voor pins, verplichte inputs, Gerrits integratiegrens en herstel. `platform/virtualization=false` houdt alle zes nieuwe ApplicationSets uit. Home Assistant als Helm-app en de oude Gateway-route zijn vervallen.
