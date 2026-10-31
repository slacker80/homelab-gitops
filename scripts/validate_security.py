#!/usr/bin/env python3
"""Offline securitycontract; optioneel echte Kyverno-CEL-tests op een chartrender."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
VM_NAMESPACES = {"apps-homeassistant", "apps-unifi-os-server"}


def load(path):
    return yaml.safe_load((ROOT / path).read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_repository(release=False):
    engine = load("helm-values/kyverno/values.yaml")
    for name in ["admission", "background", "cleanup", "reports"]:
        require(engine[name + "Controller"]["replicas"] == 1, "Kyverno moet één replica per controller houden")
    require(engine["features"]["forceFailurePolicyIgnore"]["enabled"], "Kyverno Ignore ontbreekt")
    pss = load("helm-values/kyverno-policies/values.yaml")
    require(pss["validationFailureAction"] == "Audit" and pss["failurePolicy"] == "Ignore", "PSS Audit/Ignore gewijzigd")
    require(pss["podSecurityStandard"] == "restricted", "PSS-profiel verruimd")
    require(load("manifests/kyverno-policies/base/kustomization.yaml")["resources"] == [], "Eigen policies geactiveerd")
    for path in (ROOT / "argocd/applicationsets").glob("*-agent-appset.yaml"):
        labels = yaml.safe_load(path.read_text())["spec"]["template"]["spec"]["syncPolicy"]["managedNamespaceMetadata"]["labels"]
        require(labels["pod-security.kubernetes.io/enforce"] == "restricted", "Agent-PSA verruimd")
    directory = ROOT / "manifests/virtualization-security/talos"
    for ns in {"kubevirt", "cdi"} | VM_NAMESPACES:
        obj = load(f"manifests/virtualization-security/talos/{ns}-namespace.yaml")
        require(obj["metadata"]["name"] == ns, "Namespace-naam wijkt af")
        labels = obj["metadata"]["labels"]
        require(labels["pod-security.kubernetes.io/enforce"] == ("privileged" if ns == "kubevirt" else "restricted"), "PSA-grens wijkt af")
        require(all(labels[f"pod-security.kubernetes.io/{mode}"] == "restricted" for mode in ["warn", "audit"]), "PSA-rapportage verruimd")
        require(all(labels[f"pod-security.kubernetes.io/{mode}-version"] == "v1.36" for mode in ["enforce", "warn", "audit"]), "PSA-versie niet gepind")
    kv = load("manifests/kubevirt/talos/kubevirt.yaml")
    require(kv["spec"]["configuration"]["seccompConfiguration"]["virtualMachineInstanceProfile"]["customProfile"]["runtimeDefaultProfile"], "Launcher-seccomp ontbreekt")
    for path in (ROOT / "manifests/virtual-machines/talos").glob("*.yaml"):
        obj = yaml.safe_load(path.read_text())
        if obj["kind"] in {"VirtualMachine", "DataVolume", "NetworkAttachmentDefinition"}:
            require(obj["metadata"]["namespace"] in VM_NAMESPACES, "VM-namespace wijkt af van specs")
    workloads = load("argocd/projects/workloads.yaml")["spec"]
    require(workloads["clusterResourceWhitelist"] == [{"group": "", "kind": "Namespace"}], "Clusterrechten voor gewone workloads verruimd")
    require(not any(x["group"] in {"kubevirt.io", "cdi.kubevirt.io", "k8s.cni.cncf.io"} for x in workloads["namespaceResourceWhitelist"]), "VM-rechten voor apps/agents")
    project = load("argocd/projects/virtual-machines.yaml")["spec"]
    require({x["namespace"] for x in project["destinations"]} == VM_NAMESPACES, "VM-projectbestemmingen verruimd")
    require(project["clusterResourceWhitelist"] == [{"group": "storage.k8s.io", "kind": "StorageClass"}], "VM-projectclusterrechten verruimd")
    platform = load("argocd/projects/platform.yaml")["spec"]
    require(all("*" not in x.values() for x in platform["clusterResourceWhitelist"]), "Platformclusterrechten bevatten wildcard")
    for name in ["virtualization-security", "kubevirt", "kubevirt-operator", "cdi", "cdi-operator", "multus"]:
        require(load(f"argocd/applicationsets/{name}-appset.yaml")["spec"]["template"]["spec"]["project"] == "platform", "Platformeigenaarschap gewijzigd")
    require(load("argocd/applicationsets/virtual-machines-appset.yaml")["spec"]["template"]["spec"]["project"] == "virtual-machines", "VM-project niet gekoppeld")
    domains = set()
    for path in directory.glob("*.yaml"):
        obj = yaml.safe_load(path.read_text())
        if obj["kind"] != "CiliumNetworkPolicy":
            continue
        for spec in obj["specs"]:
            require(spec["endpointSelector"], "Lege endpointselector")
            for direction in ["ingress", "egress"]:
                for rule in spec.get(direction, []):
                    require(rule.get("toPorts"), "Netwerkregel zonder poortgrens")
                    require(all(p.get("protocol") == "TCP" and p["port"].isdigit() for group in rule["toPorts"] for p in group["ports"]), "Onbegrensd protocol/poort")
                    peers = set(rule) - {"toPorts"}
                    require(peers and peers <= {"fromEntities", "toEntities", "fromEndpoints", "toEndpoints", "toFQDNs"}, "Onbegrensde netwerkpeer")
                    for kind in ["fromEntities", "toEntities"]:
                        if kind in rule:
                            require(rule[kind] == ["kube-apiserver"], "Brede entitytoestemming")
                    for kind in ["fromEndpoints", "toEndpoints"]:
                        require(all(x.get("matchLabels", {}).get("k8s:io.kubernetes.pod.namespace") for x in rule.get(kind, [])), "Peer zonder namespace")
                    for fqdn in rule.get("toFQDNs", []):
                        require(set(fqdn) == {"matchName"} and "*" not in fqdn["matchName"], "FQDN-wildcard")
                        domains.add(fqdn["matchName"])
    if release:
        inputs = load("virtualization/security-inputs.yaml")
        require(all(inputs[k] for k in ["ready", "routerVlanIsolationReviewed", "sameL2ExposureAccepted", "admissionAndNetworkRuntimeVerified"]), "Securityvrijgave ontbreekt")
        require(domains and not any(d.endswith(".invalid") for d in domains), "Import-egress bevat placeholder")
        require(domains == set(inputs["imageImportFQDNs"]), "Import-FQDNs wijken af van de gereviewde lijst")
        for name in ["haos", "unifi"]:
            url = load(f"manifests/virtual-machines/talos/{name}-disk.yaml")["spec"]["source"]["http"]["url"]
            require(urlsplit(url).scheme == "https" and urlsplit(url).hostname in domains, "Imagebron niet in FQDN-allowlist")
    print("Securitycontract consistent; deze controle levert geen runtimebewijs.")


def test_render(render, kyverno_bin, cilium_crd=None):
    docs = [x for x in yaml.load_all(render.read_text(), Loader=yaml.CSafeLoader) if x]
    require(not any(x["kind"] == "PodDisruptionBudget" for x in docs), "Onverwachte Kyverno-PDB")
    deployments = [x for x in docs if x["kind"] == "Deployment"]
    require(len(deployments) == 4 and all(x["spec"]["replicas"] == 1 for x in deployments), "Gerenderde controllerreplica's wijken af")
    policies = [x for x in docs if x["kind"] == "ValidatingPolicy"]
    require(len(policies) == 17, "Upstream PSS-inventaris gewijzigd; herbeoordeel tests")
    require(all(x["spec"]["validationActions"] == ["Audit"] and x["spec"]["failurePolicy"] == "Ignore" for x in policies), "Gerenderde PSS-acties wijken af")
    expected = load("tests/security/expectations.yaml")
    results = []
    for policy in policies:
        name = policy["metadata"]["name"]
        results.append({"isValidatingPolicy": True, "kind": "Pod", "policy": name, "resources": expected["restrictedResources"], "result": "pass"})
        results.append({"isValidatingPolicy": True, "kind": "Pod", "policy": name, "resources": [expected["handlerResource"]], "result": "skip" if name in expected["handlerExemptPolicies"] else "pass"})
    for case in expected["negativeCases"]:
        results.append({"isValidatingPolicy": True, "kind": "Pod", **case, "result": "fail"})
    with tempfile.TemporaryDirectory(prefix="security-test-") as temp:
        target = Path(temp)
        (target / "policies.yaml").write_text(yaml.safe_dump_all(policies, sort_keys=False))
        shutil.copyfile(ROOT / "tests/security/resources.yaml", target / "resources.yaml")
        test = {"apiVersion": "cli.kyverno.io/v1alpha1", "kind": "Test", "metadata": {"name": "virtualization-pss-boundaries"}, "policies": ["policies.yaml"], "resources": ["resources.yaml"], "results": results}
        (target / "kyverno-test.yaml").write_text(yaml.safe_dump(test, sort_keys=False))
        subprocess.run([kyverno_bin, "test", str(target), "--require-tests", "--remove-color", "--fail-only"], check=True)
    if cilium_crd:
        crd = yaml.safe_load(cilium_crd.read_text())
        schema = next(v["schema"]["openAPIV3Schema"] for v in crd["spec"]["versions"] if v["name"] == "v2")
        validator = jsonschema.Draft7Validator(schema)
        count = 0
        for path in (ROOT / "manifests/virtualization-security/talos").glob("*.yaml"):
            obj = yaml.safe_load(path.read_text())
            if obj["kind"] == "CiliumNetworkPolicy":
                validator.validate(obj)
                count += 1
        print(f"{count} CNP's voldoen aan het opgegeven Cilium-CRD-schema.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--render", type=Path)
    parser.add_argument("--kyverno-bin", default="kyverno")
    parser.add_argument("--cilium-crd", type=Path)
    args = parser.parse_args()
    try:
        validate_repository(args.release)
        if args.render:
            test_render(args.render, args.kyverno_bin, args.cilium_crd)
    except (ValueError, KeyError, jsonschema.ValidationError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")
