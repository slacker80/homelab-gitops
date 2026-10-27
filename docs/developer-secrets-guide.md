> Deze oorspronkelijke PR-1-handleiding is nog niet bijgewerkt. Voor de huidige
> voorbereiding geldt [voorbereiding.md](voorbereiding.md); oude eigen Kyverno-regels
> zijn niet actief.

# Secrets

Beheer Kubernetes Secrets buiten deze repository. Commit geen tokens,
wachtwoorden of andere secretwaarden. Deze repository installeert geen
operator voor secretsbeheer.

De huidige policy rapporteert secrets in environment-variabelen in Audit-modus.
Gebruik waar passend gemounte secretbestanden en een eigen ServiceAccount met
minimale rechten.
