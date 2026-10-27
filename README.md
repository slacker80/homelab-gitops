# Homelab GitOps

Conceptvoorbereiding voor SMA-94 op basis van Peters PR 1. Alle clusterlabels
en nieuwe charts staan uit. Dit is geen uitvoerbare of goedgekeurde bootstrap.
Zie [voorbereiding](docs/voorbereiding.md) en [open punten](preparation-state.yaml).

## Indeling

- `helm-values/versions.yaml`: centrale chartversies, met een standaard en optionele clusteroverrides.
- `helm-values/<component>/values.yaml` en `values-management.yaml`: componentinstellingen.
- `manifests/<component>/management/`: extra manifests via Kustomize.
- `argocd/`: root, AppProjects, ApplicationSets en clusterregistratie.
- `charts/`: eigen charts voor Home Assistant, Paperclip, Hermes, Claude, Codex en OpenCode.
- `scripts/validate.py`: controles zonder clusterverbinding; `--release` weigert zolang blokkades bestaan.

De root `argocd/bootstrap/root-app.yaml` heet `root` en leest `argocd/`
recursief, met `bootstrap/` uitgesloten. Argo, repositorytoegang en het
AppProject `platform` moeten vooraf bestaan. De definitieve bootstrapbron en
Argo-zelfbeheer wachten op Peters keuze via SMA-149.

Cluster `management` is overgenomen uit PR 1. Labels op
`argocd/cluster-secrets/management-cluster.yaml` selecteren de componenten.
Ze staan allemaal `false`; chartvalues staan eveneens uit. Verander die pas
nadat de concrete builds, secrets, opslag, netwerkregels en herstelroute zijn
voorbereid en uitvoering afzonderlijk is geautoriseerd.

Upstream Kyverno gebruikt restricted/Audit/Ignore. Alleen de upstream policies
zijn gekoppeld; de oorspronkelijke eigen policies uit PR 1 zijn niet actief.
De Cilium-basis bevat één CCNP buiten kube-system en moet uit blijven tot de
componentgerichte netwerktoestemmingen compleet zijn.

## Lokaal controleren

Vereist Python 3 met PyYAML, Helm en Kustomize:

```bash
python3 scripts/validate.py
helm lint charts/homeassistant -f helm-values/homeassistant/values.yaml
helm template homeassistant charts/homeassistant -f helm-values/homeassistant/values.yaml
kustomize build manifests/cilium/management
kustomize build manifests/namespaces
```

Herhaal de Helm-controles voor alle zes charts. Een lege render met standaardvalues
is verwacht. Inschakelen zonder geverifieerde runtimegegevens moet weigeren.
Voor bewijs en grenzen: [validatie](docs/validatie-voorbereiding.md).
Pre-commit- en Trunk-configuratie ontbreken; deze checks zijn niet uitgevoerd.

Geen secrets of decryptiesleutels in Git. Secrets worden later lokaal ingevoerd;
Argo krijgt geen decryptiesleutel. Geen bestaande Pi-diensten wijzigen zonder
Peters expliciete akkoord op de uitvoeringstaak. Codeherstel en later systeemherstel
staan beschreven in [voorbereiding](docs/voorbereiding.md#beheer-en-herstel).
