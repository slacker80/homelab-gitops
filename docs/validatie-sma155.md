# Validatie SMA-155 — alleen lokale voorbereiding

Basis GitOps: actuele concept-PR 2, `515aeff562fcf8d7784424ad39fb2451ab66cb73`.
Basis infra: actuele concept-PR 2, `02a14fbeabb540927c1d37a34f5914553f5b7e84`.
OpenSpec: `homelab-specs/openspec/changes/gitops-bootstrap/`; geen specs gekopieerd.

| Controle | Resultaat |
| --- | --- |
| `python3 scripts/validate.py` | 92 YAML-bestanden; values-/overlaybronnen, één Talos-registratie, geen projectbinding, checksumregels en SSA gecontroleerd |
| `bash scripts/render-platform.sh` | argo-cd 10.2.0, cert-manager v1.21.0, cilium 1.20.4: SHA256 goed, elk Helm-lint geslaagd, tweemaal identieke render |
| `python3 tests/platform/health.py` | 5 echte Lua-healthgevallen geslaagd, waaronder Healthy maar OutOfSync |
| `scripts/render-apps.sh` en `scripts/render-kyverno.sh` | Alle behouden charts renderen met geldige checksum en Talos-values |
| Kustomize | Alle mappen met een kustomization.yaml bouwen, inclusief alle Talos-overlays |
| Gitleaks | Geen secrets gevonden in de GitOps-werkboom |
| `git diff --check` | Geslaagd |
| `python3 scripts/validate.py --release` | Weigert terecht; bestaande uitrolblokkades blijven staan |
| pre-commit / Trunk / yamllint | Niet beschikbaar; geen geslaagde check geclaimd. YAML is met PyYAML geparseerd |
| Terraform | Beide gewijzigde roots validate en fmt-check geslaagd; bootstrap-test met fictieve Helm-provider: 1 geslaagd |
| Terraform-overdracht | Plan tegen uitsluitend fictieve state: precies 3 forget-acties, 0 toevoegen/wijzigen/verwijderen. Geen apply uitgevoerd |

De controller-/webhook-readiness, functioneel netwerk, echte tweede sync,
imagecompatibiliteit, toegang en restore zijn niet live getest. Root/project/repo-
bootstrap is nog niet als script geïmplementeerd. Bestaande worker-, image-,
secret-, opslag- en netwerkblokkades staan in `preparation-state.yaml`.
Alle componentlabels blijven uit. Een render is geen uitrolvrijgave.

Argo kan de drie releases pas overnemen nadat Terraform ze heeft losgelaten.
De infra- en GitOps-wijzigingen moeten gezamenlijk worden gereviewd en gepind;
`main` bevat bij deze voorbereiding nog geen configuratie. Mergevolgorde GitOps:
PR 1, PR 2, daarna deze opvolg-PR; infra: PR 2, daarna de bijbehorende opvolg-PR.
Een latere uitvoering vraagt Peters afzonderlijke akkoord en een schriftelijk
terugvalplan op die taak. Pi, Hermes en Paperclip zijn niet benaderd of gewijzigd.
