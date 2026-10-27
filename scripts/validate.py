#!/usr/bin/env python3
"""Controleer de voorbereiding zonder een cluster te benaderen. Vereist PyYAML."""
import argparse
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
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
    for path in ROOT.rglob("*.yaml"):
        if "charts" in path.parts and "templates" in path.parts:
            continue
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
              if k.startswith(("apps/", "platform/")) or k == "argocd-install"),
          "Voorbereiding mag geen clustercomponent activeren.")
    versions = load("helm-values/versions.yaml")
    check(all(versions[n]["default"] == "3.9.2" for n in ["kyverno", "kyverno-policies"]),
          "Kyverno-versie wijkt af van gecontroleerde chart-lock/render-script")
    for chart in (ROOT / "charts").iterdir():
        name = chart.name
        meta = load(f"charts/{name}/Chart.yaml")
        values = load(f"helm-values/{name}/values.yaml")
        check(meta["version"] == versions[name]["default"], f"Versie wijkt af: {name}")
        check(values == load(f"charts/{name}/values.yaml"), f"Standaardvalues wijken af: {name}")
        check(not values["enabled"] and not values["runtimeVerified"], f"Runtime geactiveerd: {name}")
        check(labels["apps/" + name] == "false", f"Clusterlabel actief: {name}")
        app = load(f"argocd/applicationsets/{name}-appset.yaml")
        spec = app["spec"]["template"]["spec"]
        check(spec["project"] == "workloads", f"Verkeerd project: {name}")
        check(app["spec"]["syncPolicy"]["preserveResourcesOnDeletion"], f"Cascade delete: {name}")
        check(any(x.get("path") == f"charts/{name}" for x in spec["sources"]), f"Chartbron ontbreekt: {name}")
    root = load("argocd/bootstrap/root-app.yaml")
    check(root["metadata"]["name"] == "root", "Verkeerde rootnaam")
    check("bootstrap" in root["spec"]["source"]["directory"].get("exclude", ""), "Root selecteert zichzelf")
    check(not root["metadata"].get("finalizers"), "Root bevat cascade-delete-finalizer")
    nsdocs = list(yaml.safe_load_all((ROOT / "manifests/namespaces/namespaces.yaml").read_text()))
    for ns in nsdocs:
        meta = ns["metadata"]
        check(meta["annotations"]["argocd.argoproj.io/sync-options"] == "Prune=false,Delete=false",
              f"Namespace onbeschermd: {meta['name']}")
        if meta["name"].startswith(("apps-", "agents-")):
            check(meta["labels"]["pod-security.kubernetes.io/enforce"] == "restricted",
                  f"PSA onjuist: {meta['name']}")
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
    print(f"GEEN UITROLVRIJGAVE: {len(state['blockers'])} open punten.")
    if args.release:
        check(state["ready"] and not state["blockers"], "Uitrol geblokkeerd: zie preparation-state.yaml")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

