# Gedeelde invoer voor Terraform-bootstrap

De voorbereide Terraform-root staat in homelab-infra: `terraform/platform-bootstrap`.
Centrale versies en basis-/managementvalues staan uitsluitend hier. Cilium 1.20.4
is toegevoegd aan `helm-values/versions.yaml`; de bestaande Talos-compatibele
Cilium-values zijn overgenomen uit homelab-infra. Argo behoudt chart 10.2.0.
Beide archieven zijn gepind in `helm-values/chart-checksums.sha256`.

Helm maakt bij de eerste Argo-installatie de namespace `argocd` aan. Het bestaande
namespacebestand beheert daarna dezelfde namespace, geen tweede installatie.
De eerdere keuze voor Helm is bevestigd; de vraag over het vaste install.yaml
is vervallen. Installeer nooit ook dat oude installatiebestand.

Nog te kiezen: blijven Cilium en Argo onder Terraform, of draagt Terraform na
installatie over aan Argo? Eerder projectontwerp vraagt zelfbeheer. Voor die route
moeten complete renders/CRDs/labels/TLS en stateoverdracht eerst worden uitgewerkt.
Argo rendert Helm-templates maar beheert niet de Helm-releaseadministratie.
Alle clusterlabels blijven uit. Root/bootstrap en de overige open punten zijn nog
niet uitrolgereed. Zie `preparation-state.yaml` en homelab-infra `docs/helm-bootstrap.md`.

Codeherstel: eigen concept-PR sluiten of na merge eigen commit reverten.
Doelruntime: toekomstig ThinkCentre/Talos-cluster, nog geen live bereikbaarheid
vastgesteld. Repos via bestaande private GitHub-verbinding bereikbaar.
Runtimeherstel vereist bekende Git-revisie plus externe state/secrets/appdata;
niet getest. Geen draaiend systeem gewijzigd.
