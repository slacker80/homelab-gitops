# Pod security

Actueel: [virtualisatiebeveiliging](virtualisatie-security.md). Upstream Kyverno
PSS is restricted/Audit/Ignore. Alleen virt-handler heeft negen gerichte
PSS-uitzonderingen; CDI, virt-launchers en andere apps/agents krijgen die niet.
PSA enforce is privileged in kubevirt en restricted in CDI en de VM-namespaces.
De KubeVirt-CR configureert RuntimeDefault-seccomp voor virt-launchers.

Kyverno gebruikt één replica per controller op de ene node. De oude eigen
policies voor minimumreplica's, zone-spreiding, probes, ServiceAccounts en
PDB-generatie zijn niet actief: hun Kustomization is leeg. Activeer deze niet
zonder een nieuw besluit en compatibiliteitscontrole. Een policytest of render
bewijst geen werkende admission, VM-start of veilige shutdown.
