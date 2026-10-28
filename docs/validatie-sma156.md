# Validatie SMA-156 — 28 oktober 2026

Basis: bestaande GitOps-PR 3 op `f9d50d617fcbfe16ba790fbdfaea9bb18ca14dec`.
De tien gewijzigde bestaande bestanden zijn vóór publicatie inhoudelijk vergeleken
met die exacte remote revisie; geen afwijkende basis. Infra-PR 3 blijft op
`6341420799dd10c7ffc0b07df72876aab52b3096`: geen Envoy/Gateway-resources in Terraform.

Geslaagd:

- `python3 scripts/validate.py`: 104 YAML-bestanden, lokale verwijzingen,
  ApplicationSets, afzonderlijke routeselectie en beheergrenzen.
- `bash scripts/render-gateway.sh`: SHA256-controle Envoy 1.8.3 en vier backendcharts;
  vijf Helm-lints (Envoy, Argo CD, Cilium, Home Assistant en Paperclip/app-template),
  identieke dubbele Envoy-render inclusief CRDs, Kustomize-render van de routes.
- Negen Gateway-resources gevalideerd tegen OpenAPI/JSON-schema uit exact die
  Envoy-chart. Backendnamen én servicepoorten vergeleken met de vier chartrenders.
- Vijf negatieve proeven geweigerd: onjuiste backendpoort, verkeerde parent,
  HTTP-listener, allow-all en LoadBalancer-proxy. Home Assistant-service is 8080;
  de eerste voorbereiding verwees foutief naar applicatiepoort 8123 en is hersteld.
- Shellsyntax en `git diff --check`; Gitleaks vindt geen secrets.
- `validate.py --release` weigert terecht: geen uitrolvrijgave, bestaande
  images/secrets/opslag/netwerkvragen en nieuwe toegang/TLS-keuzes staan open.

De eerste renderrun faalde door onvoldoende ruimte op `/tmp`. De voltooide run
gebruikte `TMPDIR` in de projectwerkruimte; er zijn geen bestanden van andere
processen verwijderd. Reproduceer met beschikbare tijdelijke opslag, bijvoorbeeld:

```bash
TMPDIR=/pad/met/vrije/ruimte bash scripts/render-gateway.sh
```

Niet uitgevoerd of niet bewezen: pre-commit, Trunk en yamllint ontbreken;
CEL-validatieregels, server-side schema/admission, Gateway-policyacceptatie,
TLS-uitgifte, werkelijke IP/auth-beperking, netwerk/WebSockets, readiness/tweede
sync en herstel. De schema- en negatieve proeven zijn statisch en vervangen deze
controles niet. Geen live apply, DNS, merge, installatie of kosten.

Systeemnotities, voorgestelde hosts, beheer, activeringsvolgorde en terugval:
[gateway-api.md](gateway-api.md). De routes blijven standaard geblokkeerd en alle
installatielabels false. De huidige Pi-diensten zijn niet benaderd of gewijzigd.
