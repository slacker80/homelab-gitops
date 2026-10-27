# Netwerkpolicies

De Cilium-baseline blokkeert ingress en egress voor workloadnamespaces en staat
DNS naar kube-dns toe. Cilium moet vooraf op het cluster zijn geïnstalleerd.
Platformnamespaces staan in
`manifests/cilium/base/platform-namespace-exclusions.yaml`.

Workloads moeten hun benodigde verbindingen expliciet toestaan met eigen
NetworkPolicies of CiliumNetworkPolicies. Leg poorten, bestemmingen en
ingressbronnen vast bij de workload. Er zijn geen vooraf ingestelde private
netwerkranges of load-balancerbronnen.

Kyverno maakt daarnaast een standaard deny-NetworkPolicy voor nieuwe
workloadnamespaces. Controleer beide policylagen wanneer verkeer niet werkt.
