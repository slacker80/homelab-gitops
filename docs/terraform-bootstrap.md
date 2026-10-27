# Terraform-bootstrap en overdracht aan Argo

Besluit (Peter, SMA-150, 27 oktober 2026): Terraform installeert na Talos eerst
Cilium en daarna Argo CD via Helm. Daarna beheert Argo beide vanuit deze repo.
Terraform en Argo beheren nooit tegelijk dezelfde release.

## Gedeelde invoer

De Terraform-root in homelab-infra (`terraform/platform-bootstrap`) leest de
chartversies uit `helm-values/versions.yaml` en de values uit
`helm-values/{cilium,argocd}/values.yaml` plus `values-management.yaml`.
De chartarchieven zijn gepind in `helm-values/chart-checksums.sha256`.
Argo gebruikt via `cilium-appset.yaml` en `argocd-appset.yaml` exact dezelfde
bestanden en dezelfde releasenamen (`cilium` in kube-system, `argocd` in argocd).
Helm maakt bij de eerste Argo-installatie de namespace `argocd` aan.

Cilium gebruikt `hubble.tls.auto.method: cronJob`. Met de standaardmethode
`helm` maakt elke render nieuwe certificaten; Argo zou dan blijvend afwijken.

## Volgorde

1. Terraform: Talos, daarna Cilium, daarna Argo CD, repositorytoegang en root.
2. Argo synchroniseert de root. `cilium-install` en `argocd-install` staan nog uit.
3. Terraform laat beide releases los zonder ze te verwijderen (`removed`-blok
   met `destroy = false` in homelab-infra) en `terraform plan` toont geen
   verdere wijziging aan Cilium of Argo.
4. Pas dan `cilium-install` en `argocd-install` op `true`. Argo neemt dezelfde
   objecten over met Server-Side Apply. Cilium heeft geen automatische prune.
5. Controleer dat beide Applications Synced/Healthy zijn en dat netwerk en
   Argo-UI blijven werken.

Na stap 4 blijft het Helm-releasesecret van Terraform staan; Argo gebruikt het
niet. Helm-upgrades daarna alleen nog via deze repo, niet met `helm` of Terraform.

## Terugval

Vóór stap 4: label uit laten; Terraform beheert nog. Na stap 4: labels weer op
`false` zetten; dankzij `preserveResourcesOnDeletion` blijven de objecten staan.
Herstel daarna met dezelfde chartversie en values. Deze route is niet getest;
live uitvoering valt onder SMA-102 met eigen terugvalplan en Peters akkoord.
