# Bootstrapdelta SMA-174 — alleen lokale verificatie

In eigen bestaande worktree op basis bf9b91b; securitydelta de602a7 op Gerrits
worktree blijft afzonderlijk behouden. Riekus integreert na onafhankelijke review.
Geen securitybestanden gewijzigd en geen live toegang gebruikt.

- validate.py slaagt: YAML/bronnen, alle labels false, centrale pins/checksums,
  releaseName/SSA, DNS-combinatie, annotation tracking en eerste autosync uit.
- render-platform.sh: SHA256/lint en twee identieke renders voor Argo 10.2.0,
  cert-manager v1.21.0 en Cilium 1.20.4. cilium-config bevat daadwerkelijk
  enable-host-legacy-routing=true en cni-exclusive=false; argocd-cm bevat
  application.resourceTrackingMethod=annotation.
- Bestaande app-, Kyverno-, virtualisatie- en Gateway-renders opnieuw uitgevoerd.
  Application-health: vijf echte Lua-gevallen geslaagd.
- Talos metal-render en twaalf negatieve faseproeven staan in infra docs/validatie.md.
- Uitrolcontrole --release moet blijven weigeren: secrets/images, echte hardware,
  storage en security-integratie zijn nog geen uitvoeringsvrijgave.
- pre-commit/Trunk/shellcheck ontbreken. Shellsyntax, Python-parse en YAML gecontroleerd.

Geen clusterverbinding, API/apply, sync, merge, DNS-pakkettest, USB/VM-start,
Argo-overname, tweede echte sync of restore uitgevoerd. De overdracht bevat een
verplichte diff/handmatige eerste sync met autosync uit en daarna een tweede
reviewcommit. Zie bootstrap.md voor identiteit, eigenaarschap, beheer en terugval.

Integratieproef: eigen geïsoleerde worktree op de602a7, bootstrapdelta met git apply
--3way zonder conflicten. Gecombineerde validate.py slaagt (140 YAML-bestanden,
securitycontract intact); gecombineerde virtualisatierender is gecontroleerd.
Dit publiceert/integreert Gerrits branch niet en vervangt Truus' review niet.
Secretsscan van publiceerbare GitOps-bestanden: geen bevindingen. Infra idem; een
bestaande genegeerde oude _out-render bevat gegenereerde TLS-sleutels en blijft
buiten Git/oplevering. De nieuwe herstelrender gebruikt certgen en bevat nul Secrets.
