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

def image_tags(node):
    """Alle image-tags in values; een lege tag valt terug op appVersion zonder digest."""
    if isinstance(node, dict):
        if "repository" in node and "tag" in node:
            yield node["tag"]
        for value in node.values():
            yield from image_tags(value)
    elif isinstance(node, list):
        for value in node:
            yield from image_tags(value)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true", help="Weiger zolang uitvoeringsblokkades bestaan.")
    args = parser.parse_args()
    count = 0
    todo = []
    undigested = []
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
    cluster = load("argocd/cluster-secrets/talos-cluster.yaml")
    labels = cluster["metadata"]["labels"]
    check(all(v == "false" for k, v in labels.items()
              if k.startswith(("apps/", "platform/")) or k in ("argocd-install", "cilium-install")),
          "Voorbereiding mag geen clustercomponent activeren.")
    versions = load("helm-values/versions.yaml")
    check(all(versions[n]["default"] == "3.9.2" for n in ["kyverno", "kyverno-policies"]),
          "Kyverno-versie wijkt af van gecontroleerde chart-lock/render-script")
    checksums = (ROOT / "helm-values/chart-checksums.sha256").read_text()
    check(cluster["metadata"]["name"] == "talos-cluster" and cluster["stringData"]["name"] == "talos",
          "Er is precies één logische Talos-clusterregistratie")
    check(cluster["stringData"]["server"] == "https://kubernetes.default.svc", "Onverwachte clusterbestemming")
    check("project" not in cluster["stringData"], "Cluster moet ook voor project workloads beschikbaar zijn")
    check(len(list((ROOT / "argocd/cluster-secrets").glob("*.yaml"))) == 1, "Tweede clusterregistratie")
    for appset in (ROOT / "argocd/applicationsets").glob("*.yaml"):
        template = yaml.safe_load(appset.read_text())["spec"]["template"]["spec"]
        for source in template.get("sources", [template.get("source", {})]):
            if "chart" in source:
                for ref in source["helm"]["valueFiles"]:
                    local = ref.replace("$values/", "").replace("{{ .name }}", "talos")
                    check((ROOT / local).is_file(), f"Ontbrekende values: {local}")
            if "path" in source:
                check((ROOT / source["path"].replace("{{ .name }}", "talos")).is_dir(),
                      f"Ontbrekende overlay: {source['path']}")
    for component, chartname in [("argocd", "argo-cd"), ("cilium", "cilium"), ("cert-manager", "cert-manager")]:
        check(f"{chartname}-{versions[component]['default']}.tgz" in checksums, f"Checksum ontbreekt: {component}")
        spec = load(f"argocd/applicationsets/{component}-appset.yaml")["spec"]["template"]["spec"]
        chart = next(s for s in spec["sources"] if "chart" in s)
        check(chart["helm"]["releaseName"] == component, f"Bootstrap-release wijkt af: {component}")
        check("ServerSideApply=true" in spec["syncPolicy"]["syncOptions"], f"Geen SSA: {component}")
    check(load("helm-values/cert-manager/values.yaml")["crds"]["keep"], "cert-manager CRDs onbeschermd")
    check(load("helm-values/cilium/values.yaml")["hubble"]["tls"]["auto"]["method"] == "cronJob", "Hubble-render is willekeurig")
    check(load("helm-values/cilium/values.yaml")["gatewayAPI"]["enabled"] is False,
          "Envoy moet de enige Gateway API-controller zijn")
    check(load("helm-values/envoy-gateway/values.yaml")["crds"]["enabled"] is True,
          "Envoy-chart moet de Gateway API-CRDs beheren")
    check(f"gateway-helm-{versions['envoy-gateway']['default']}.tgz" in checksums,
          "Envoy-checksum ontbreekt")
    route_app = load("argocd/applicationsets/gateway-routes-appset.yaml")
    selector = route_app["spec"]["generators"][0]["clusters"]["selector"]["matchLabels"]
    check(selector == {"platform/envoy-gateway": "true", "platform/gateway-routes": "true"},
          "Gateway-routes vereisen een afzonderlijke selectiekeuze")
    for name in ["envoy-gateway", "gateway-routes"]:
        app = load(f"argocd/applicationsets/{name}-appset.yaml")
        check(app["spec"]["syncPolicy"]["preserveResourcesOnDeletion"], "Gateway-cascade-delete")
        check(app["spec"]["template"]["spec"]["syncPolicy"]["automated"]["prune"] is False,
              "Gateway/CRD-prune moet afzonderlijk worden beoordeeld")
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
        if not all("@sha256:" in str(tag) for tag in image_tags(yaml.safe_load(values_text))):
            undigested.append(name)
    ha = load("argocd/applicationsets/homeassistant-appset.yaml")["spec"]["template"]["spec"]
    check(next(x for x in ha["sources"] if "chart" in x)["helm"].get("skipTests") is True,
          "Home Assistant-testpod moet via skipTests uit")
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
    print(f"GEEN UITROLVRIJGAVE: {len(state['blockers'])} open punten; TODO-waarden in: {', '.join(todo) or 'geen'}; "
          f"images zonder digest in: {', '.join(undigested) or 'geen'}.")
    if args.release:
        check(state["ready"] and not state["blockers"] and not todo and not undigested,
              "Uitrol geblokkeerd: zie preparation-state.yaml")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

