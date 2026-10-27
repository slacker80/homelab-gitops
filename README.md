# Homelab GitOps

GitOps-configuratie voor het homelab, beheerd door Argo CD. ApplicationSets
selecteren clusters via labels op Argo CD cluster-Secrets.

## Werking

De root-Application in `argocd/bootstrap/root-app.yaml` leest recursief
`argocd/` uit `https://github.com/slacker80/homelab-gitops.git` op `main`.
Argo CD en toegang tot deze repository moeten vooraf zijn ingericht.
De root gebruikt het AppProject `platform`; dat moet bij bootstrap ook bestaan.

`argocd/cluster-secrets/management-cluster.yaml` registreert het lokale cluster
als `management` via `https://kubernetes.default.svc`. Het bestand bevat geen
externe clustercredentials. De labels schakelen de volgende componenten in:

| Label | Component |
| --- | --- |
| `argocd-install=true` | Argo CD |
| `platform/cilium=true` | Cilium-netwerkpolicies; Cilium moet al geïnstalleerd zijn |
| `platform/kyverno=true` | Kyverno |
| `platform/kyverno-policies=true` | Pod Security Standards en aanvullende policies |
| `platform/cert-manager=true` | cert-manager |
| `platform/envoy-gateway=true` | Envoy Gateway-controller |

## Indeling

- `argocd/`: root-Application, AppProjects, ApplicationSets en clusterregistratie.
- `helm-values/`: componentinstellingen en centrale chartversies in `versions.yaml`.
- `manifests/`: Cilium- en Kyverno-policies met een `management`-overlay.
- `docs/`: handleidingen voor netwerkpolicies, pod security en secrets.
- `tests/kyverno/`: bestaande regressietests voor een securityContext-variant.

## Toegang en inrichting

Argo CD gebruikt de lokale adminlogin en serveert HTTPS via een ClusterIP-service.
Voor lokale toegang kun je `kubectl -n argocd port-forward svc/argocd-server 8443:443`
gebruiken. Repositorycredentials en wachtwoorden worden buiten deze repo beheerd.

De Envoy Gateway-controller heeft nog geen Gateway, LoadBalancer-configuratie of
HTTPRoute. cert-manager heeft nog geen Issuer. Kies en configureer deze
onderdelen voor het homelab voordat je
workloads erop aansluit; zie [TODO.md](TODO.md).

De bestaande replica-aantallen, resourcebudgetten en policies zijn behouden.
Controleer of ze bij de capaciteit van je homelab passen. Workloadpolicies
vereisen onder meer minimaal twee replica's en expliciete netwerktoestemming.

## Aanpassen en controleren

Chartversies staan in `helm-values/versions.yaml`. Optionele overrides heten
`helm-values/<component>/values-<cluster>.yaml`. Voor extra clusters met
Cilium- of Kyverno-policies is ook een gelijknamige manifestoverlay nodig.

Controleer lokaal zonder resources toe te passen:

```bash
kubectl kustomize manifests/cilium/management
kubectl kustomize manifests/kyverno-policies/management
kyverno test tests/kyverno/add-default-security-context
```

De Kyverno-test gebruikt `policy.yaml` in de testdirectory als fixture voor de
variant die expliciete securityContext-waarden behoudt; hij valideert niet de
actieve baselinepolicy.

Argo CD verzorgt de uitrol na publicatie. Lokale wijzigingen zijn geen bewijs
dat de configuratie al op een cluster draait.
