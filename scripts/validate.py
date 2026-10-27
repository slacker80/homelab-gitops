#!/usr/bin/env python3
"""Controleer de voorbereiding zonder een cluster te benaderen. Vereist PyYAML."""
import argparse
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
APPS = ["homeassistant", "hermes", "paperclip", "claude-agent", "codex-agent", "opencode-agent"]
def load(path):
    return yaml.safe_load((ROOT / path).read_text())
def check(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true", help="Weiger zolang uitvoeringsblokkades bestaan.")
    args = parser.parse_args()
    count = 0
    todo = []
    for path in ROOT.rglob("*.yaml"):
        list(yaml.safe_load_all(path.read_text()))
        count += 1
    for path in ROOT.rglob("kustomization.yaml"):
        data = yaml.safe_load(path.read_text())
        for ref in data.get("resources", []):
            check((path.parent / ref).exists(), f"Ontbrekende Kustomize-bron: {path}: {ref}")
        for patch in data.get("patches", []):
            if isinstance(patch, dict) and "path" in patch:
                check((path.parent / patch["path"]).is_file(), f"Ontbrekende patch: {path}")
    state = load("preparation-state.yaml")
    cluster = load("argocd/cluster-secrets/management-cluster.yaml")
    labels = cluster["metadata"]["labels"]
    check(all(v == "false" for k, v in labels.items()
              if k.startswith(("apps/", "platform/")) or k in ("argocd-install", "cilium-install")),
          "Voorbereiding mag geen clustercomponent activeren.")
    versions = load("helm-values/versions.yaml")
    check(all(versions[n]["default"] == "3.9.2" for n in ["kyverno", "kyverno-policies"]),
          "Kyverno-versie wijkt af van gecontroleerde chart-lock/render-script")
    checksums = (ROOT / "helm-values/chart-checksums.sha256").read_text()
    workloads = load("argocd/projects/workloads.yaml")["spec"]
    for name in APPS:
        check(labels["apps/" + name] == "false", f"Clusterlabel actief: {name}")
        app = load(f"argocd/applicationsets/{name}-appset.yaml")
        spec = app["spec"]["template"]["spec"]
        check(spec["project"] == "workloads", f"Verkeerd project: {name}")
        check(app["spec"]["syncPolicy"]["preserveResourcesOnDeletion"], f"Cascade delete: {name}")
        chart = next(x for x in spec["sources"] if "chart" in x)
        check(chart["repoURL"] in workloads["sourceRepos"], f"Chartbron niet in project: {name}")
        check(f"{chart['chart']}-{versions[name]['default']}.tgz" in checksums, f"Checksum ontbreekt: {name}")
        sync = spec["syncPolicy"]
        check("CreateNamespace=true" in sync["syncOptions"], f"CreateNamespace ontbreekt: {name}")
        check(sync["managedNamespaceMetadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted",
              f"PSA onjuist: {name}")
        pvcs = [d for d in yaml.safe_load_all((ROOT / f"manifests/{name}/base/pvc.yaml").read_text())]
        for pvc in pvcs:
            check(pvc["metadata"]["annotations"]["argocd.argoproj.io/sync-options"] == "Prune=false,Delete=false",
                  f"PVC onbeschermd: {pvc['metadata']['name']}")
        values_text = (ROOT / f"helm-values/{name}/values.yaml").read_text()
        claims = {p["metadata"]["name"] for p in pvcs}
        check(all(c in values_text for c in claims), f"PVC niet gekoppeld: {name}")
        if "TODO" in values_text:
            todo.append(name)
    check(not (ROOT / "charts").exists(), "Eigen charts/ hoort niet meer te bestaan")
    check(not (ROOT / "manifests/namespaces").exists(), "Namespaces horen via de ApplicationSets te lopen")
    root = load("argocd/bootstrap/root-app.yaml")
    check(root["metadata"]["name"] == "root", "Verkeerde rootnaam")
    check("bootstrap" in root["spec"]["source"]["directory"].get("exclude", ""), "Root selecteert zichzelf")
    check(not root["metadata"].get("finalizers"), "Root bevat cascade-delete-finalizer")
    policies = load("helm-values/kyverno-policies/values.yaml")
    check(policies["validationFailureAction"] == "Audit", "Kyverno moet Audit gebruiken")
    check(policies["failurePolicy"] == "Ignore", "Policy-webhooks moeten Ignore gebruiken")
    check(policies["podSecurityStandard"] == "restricted" and policies["policyType"] == "ValidatingPolicy",
          "Verkeerd upstream policyprofiel")
    engine = load("helm-values/kyverno/values.yaml")
    check(engine["admissionController"]["replicas"] == 2, "Twee admission-replica's vereist")
    check(engine["features"]["forceFailurePolicyIgnore"]["enabled"], "Ignore niet afgedwongen")
    custom = load("manifests/kyverno-policies/base/kustomization.yaml")
    check(custom["resources"] == [], "Eigen Kyverno-policies mogen niet actief zijn")
    cilium = load("manifests/cilium/base/kustomization.yaml")
    check(cilium["resources"] == ["cluster-default-deny.yaml"] and not cilium.get("patches"),
          "Exact één CCNP vereist")
    baseline = load("manifests/cilium/base/cluster-default-deny.yaml")
    spec = baseline["spec"]
    check(spec["enableDefaultDeny"] == {"ingress": True, "egress": True}, "Default deny ontbreekt")
    check(not spec.get("ingressDeny") and not spec.get("egressDeny"), "Expliciete deny is verboden")
    print(f"{count} YAML-bestanden leesbaar; voorbereidingsgrenzen consistent.")
    print(f"GEEN UITROLVRIJGAVE: {len(state['blockers'])} open punten; TODO-waarden in: {', '.join(todo) or 'geen'}.")
    if args.release:
        check(state["ready"] and not state["blockers"] and not todo, "Uitrol geblokkeerd: zie preparation-state.yaml")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

