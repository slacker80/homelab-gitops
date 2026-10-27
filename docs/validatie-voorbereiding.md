# Lokaal validatiebewijs — 27 oktober 2026

Dit bewijs betreft uitsluitend de conceptvoorbereiding. Geen echte clusteractie,
runtimeproef, modelrun, migratie of restore uitgevoerd. Geen uitrolvrijgave.

- `python3 scripts/validate.py`: 91 YAML-bestanden leesbaar, versie-/bron-/PSA-/databehoudgrenzen gecontroleerd.
- `python3 scripts/validate.py --release`: weigert zoals bedoeld wegens 11 open punten.
- Alle zes eigen charts: Helm lint geslaagd; standaardrender bevat geen resources.
- Alle zes met uitsluitend fictieve testwaarden: vier resources per chart gerenderd;
  Recreate, niet-root, geen ServiceAccount-token, PVC Prune=false,Delete=false gecontroleerd.
- Per chart vier negatieve renders gecontroleerd: alleen enabled=true, foutieve image-digest,
  ontbrekende secretreferentie en onbekend persistent mountpad. Alle weigeren zoals bedoeld. De fictieve image bestaat niet
  en staat alleen in een tijdelijke testfixture buiten de repo.
- Alle twaalf Kustomize-directories renderen: Cilium (3), Kyverno (2), namespaces (1),
  zes workload-overlays (6). De zes extra-manifestoverlays en Kyverno-custombasis zijn bewust leeg.
- Kyverno 3.9.2: 81 documenten lokaal gerenderd; appVersion v1.19.2, twee
  admission-replica's en daadwerkelijke controllerflag `--forceFailurePolicyIgnore=true` gecontroleerd.
- Kyverno-policies 3.9.2: 17 upstream ValidatingPolicies gerenderd;
  allemaal validationActions=[Audit], failurePolicy=Ignore en de vier namespace-uitzonderingen.
  De eerste test toonde een verkeerd valuesveld voor uitsluiting; dat is gecorrigeerd naar
  `vpolExclude.excludeNamespaces` en opnieuw tegen alle gerenderde policies gecontroleerd.
- Beide chartarchieven: SHA256 vergeleken met de officiële Kyverno-index;
  hashes vastgelegd in `helm-values/chart-checksums.sha256`.
- Gitleaks 8.30.1: geen geheimen gevonden in de voorbereide bronbestanden.
- pre-commit en Trunk: niet uitgevoerd; programmatuur en repo-configuratie ontbreken.
  De historische Kyverno-fixturetest is niet opnieuw uitgevoerd: die toetst een
  ongewijzigde oude eigen policy die geen onderdeel is van de actieve baseline.

Gebruikt: Helm v3.19.0, Kustomize v5.8.1, Python 3/PyYAML 6.0.2.
Kustomize-archiefhash tegen upstream checksums gecontroleerd:
`0953ea3e476f66d6ddfcd911d750f5167b9365aa9491b2326398e289fef2c142` (linux_arm64).
Alleen tijdelijke hulpmiddelen gebruikt; geen systeempackage of dienst aangepast.

De daadwerkelijke door Kyverno na installatie gegenereerde ValidatingPolicy-webhooks
zijn niet te bewijzen met alleen Helm-rendering. Ook app-health/auth, PVC/PV-Retain,
netwerkdataplane, readiness, gedeelde agentlimieten en herstel blijven open.
Zie [voorbereiding](voorbereiding.md) en [blokkades](../preparation-state.yaml).

Upstreambronnen: [Kyverno chartindex](https://kyverno.github.io/kyverno/index.yaml),
[Kyverno-configuratie](https://kyverno.io/docs/installation/customization/) en
[Kustomize v5.8.1](https://github.com/kubernetes-sigs/kustomize/releases/tag/kustomize%2Fv5.8.1).
