# Netwerkpolicies

Actueel: [virtualisatiebeveiliging](virtualisatie-security.md) en
[voorbereiding](voorbereiding.md). De clusterbaseline bestaat uit één CCNP met
pod-default-deny buiten kube-system en DNS naar kube-dns. De nieuwe
virtualization-security-Application voegt gerichte controller-/API-/webhook-
en import-CNP's toe. De eigen Kyverno NetworkPolicy-generator is inactief.

Workloads vragen expliciete poorten en peers. CNP's en Kubernetes NetworkPolicies
werken additief; controleer daarom alle effectieve regels. Een VM-NIC op Multus
br0 valt buiten Cilium/Hubble. Router/VLAN-isolatie, blootstelling op hetzelfde L2
en het resterende gastverkeer moeten apart worden beoordeeld en geverifieerd.
