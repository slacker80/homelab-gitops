# Secrets

Beheer Kubernetes Secrets buiten deze repository. Commit geen tokens,
wachtwoorden of andere secretwaarden. Deze repository installeert geen
operator voor secretsbeheer.

De huidige policy rapporteert secrets in environment-variabelen in Audit-modus.
Gebruik waar passend gemounte secretbestanden en een eigen ServiceAccount met
minimale rechten.
