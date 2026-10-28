# Pod security

Kyverno beheert Pod Security Standards en aanvullende policies vanuit
`manifests/kyverno-policies/base/`. De management-overlay gebruikt deze baseline.

Workloads moeten onder meer resource limits, probes en een expliciete
ServiceAccount instellen. De baseline beperkt privileges en RBAC en vereist
minimaal twee replica's voor Deployments en StatefulSets, of een bijbehorende
HPA met minimaal twee replica's. Controleer deze eisen voor je homelabcapaciteit.

Kyverno genereert een PodDisruptionBudget voor geschikte workloads. Wie zelf
een PDB beheert, kan de workloadannotatie `homelab.local/skip-pdb: "true"`
gebruiken. Platformuitzonderingen staan in `base/exceptions.yaml`.
