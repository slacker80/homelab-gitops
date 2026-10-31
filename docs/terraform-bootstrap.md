# Oude Terraform-bootstrap vervallen

De actieve procedure staat in [bootstrap.md](bootstrap.md): talosctl → Cilium Helm
→ Argo Helm → Argo-overname; cert-manager rechtstreeks via Argo. Bestaande
versiepins, release-identiteiten en SMA-155-controles blijven behouden.

De drie Terraform-roots zijn uit homelab-infra verwijderd. Bestaande state wordt
niet verwijderd of vernietigd: eerst inventariseren en bestaande clusteridentiteit
veiligstellen; zie infra `docs/helm-bootstrap.md`. Dit document blijft als verwijzing
voor bestaande links. Geen apply, sync, uninstall, hostactie of restore uitgevoerd.
