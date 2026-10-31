#!/usr/bin/env python3
"""Offline contractcontrole; --release weigert ontbrekende hardware/image/securityinputs."""
from pathlib import Path
import argparse
import hashlib
import jsonschema
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ['kubevirt-operator', 'kubevirt', 'cdi-operator', 'cdi', 'multus', 'virtual-machines']
def load(path):
    return yaml.safe_load((ROOT / path).read_text())
def require(ok, message):
    if not ok:
        raise ValueError(message)
def validate(release=False):
    lock = load('virtualization/versions.yaml')
    for component in ['kubevirt-operator', 'cdi-operator', 'multus']:
        raw = ROOT / f'manifests/{component}/vendor/upstream.yaml'
        require(hashlib.sha256(raw.read_bytes()).hexdigest() == lock[component]['sha256'], f'Upstream-checksum: {component}')
    # Validate custom resources against the actual pinned operator CRDs.
    for operator, name in [('kubevirt-operator', 'kubevirt'), ('cdi-operator', 'cdi')]:
        docs = list(yaml.safe_load_all((ROOT / f'manifests/{operator}/vendor/upstream.yaml').read_text()))
        obj = load(f'manifests/{name}/talos/{name}.yaml')
        crd = next(d for d in docs if d and d.get('kind') == 'CustomResourceDefinition' and d['spec']['names']['kind'] == obj['kind'])
        version = next(v for v in crd['spec']['versions'] if v['name'] == obj['apiVersion'].split('/')[1])
        jsonschema.Draft7Validator(version['schema']['openAPIV3Schema']).validate(obj)
    require('@sha256:' in lock['multus']['image'], 'Multus-image zonder digest')
    for component in COMPONENTS:
        app = load(f'argocd/applicationsets/{component}-appset.yaml')['spec']
        require(app['syncPolicy']['preserveResourcesOnDeletion'], 'ApplicationSet cascade-delete')
        require(app['template']['spec']['syncPolicy']['automated']['prune'] is False, 'Argo prune')
        require(app['generators'][0]['clusters']['selector']['matchLabels'] == {'platform/virtualization': 'true'}, 'Selectiegrens')
    require(load('helm-values/cilium/values.yaml')['cni']['exclusive'] is False, 'Multus/Cilium-conflict')
    kv = load('manifests/kubevirt/talos/kubevirt.yaml')['spec']
    require('HostDevices' in kv['configuration']['developerConfiguration']['featureGates'], 'USB feature gate ontbreekt')
    require(kv['infra']['replicas'] == 1 and kv['configuration']['virtTemplateDeployment']['enabled'] is False, 'KubeVirt capaciteitsgrens')
    require(kv['configuration']['evictionStrategy'] == 'None' and kv['workloadUpdateStrategy']['workloadUpdateMethods'] == [], 'Migratie ingeschakeld')
    patch = load('manifests/kubevirt-operator/talos/kustomization.yaml')['patches'][0]['patch']
    require(yaml.safe_load(patch) == [{'op':'replace','path':'/spec/replicas','value':1}], 'Operator moet één replica hebben')
    sc = load('manifests/virtual-machines/talos/storageclass.yaml')
    require(sc['reclaimPolicy'] == 'Retain' and sc['volumeBindingMode'] == 'WaitForFirstConsumer', 'Opslagbescherming')
    for name, memory, size in [('haos','3Gi','32Gi'), ('unifi','4Gi','20Gi')]:
        vm = load(f'manifests/virtual-machines/talos/{name}.yaml')
        dv = load(f'manifests/virtual-machines/talos/{name}-disk.yaml')
        spec = vm['spec']['template']['spec']
        domain = spec['domain']
        require(vm['spec']['runStrategy'] == 'Always' and spec['evictionStrategy'] == 'None' and spec['terminationGracePeriodSeconds'] == 120, f'VM lifecycle: {name}')
        require(domain['cpu']['cores'] == 2 and domain['resources']['requests']['memory'] == memory, f'VM resources: {name}')
        require(dv['spec']['pvc']['resources']['requests']['storage'] == size and dv['spec']['pvc']['storageClassName'] == 'vm-disks-retain', f'Disk: {name}')
        require(spec['volumes'] == [{'name':'rootdisk','dataVolume':{'name':name+'-disk'}}], f'Diskkoppeling: {name}')
        require(spec['networks'] == [{'name':'lan','multus':{'networkName':'lan-br0'}}], f'Gastnetwerk: {name}')
        require(all('pod' not in n for n in spec['networks']), 'Onbedoeld gast-podnetwerk')
        for obj in [vm,dv,sc]:
            require(obj['metadata']['annotations']['argocd.argoproj.io/sync-options'] == 'Prune=false,Delete=false', 'Data onbeschermd')
        if name == 'haos':
            require(domain['firmware']['bootloader']['efi']['secureBoot'] is False, 'HAOS UEFI')
            require(domain['devices']['hostDevices'][0]['deviceName'] == kv['configuration']['permittedHostDevices']['usb'][0]['resourceName'], 'USB resourcekoppeling')
    require(not (ROOT/'argocd/applicationsets/homeassistant-appset.yaml').exists(), 'Oude HA-app')
    require(not (ROOT/'manifests/gateway/base/homeassistant-route.yaml').exists(), 'Verweesde HA-route')
    inputs = load('virtualization/required-inputs.yaml')
    missing = [str(p.relative_to(ROOT)) for parent in ['virtualization','manifests/kubevirt/talos','manifests/virtual-machines/talos'] for p in (ROOT/parent).rglob('*.yaml') if 'REQUIRED_' in p.read_text()]
    print('Virtualisatiecontract en upstream-checksums consistent; geen runtimebewijs.')
    print(f'Uitrol geblokkeerd: {len(missing)} bestanden met verplichte invoer; security/storage-review nog vereist.')
    if release:
        require(not missing and inputs['ready'] and inputs['securityIntegrationReviewed'] and inputs['storage']['provisionerAndBackupVerified'], 'Geen uitrolvrijgave: verplichte invoer/review ontbreekt')
        macs = []
        for name in ['haos','unifi']:
            i = inputs[name]
            require(re.fullmatch(r'[0-9a-fA-F]{64}',i['sha256']) is not None, f'Image SHA256: {name}')
            require(i['imageURL'].startswith('https://'), 'Image vereist immutable HTTPS URL en vooraf geverifieerde SHA256')
            mac = i['mac'].lower()
            require(re.fullmatch(r'[0-9a-f]{2}(:[0-9a-f]{2}){5}',mac) is not None and int(mac[:2],16) & 1 == 0 and mac != '00:00:00:00:00:00', 'Ongeldige gast-MAC')
            vm = load(f'manifests/virtual-machines/talos/{name}.yaml')
            dv = load(f'manifests/virtual-machines/talos/{name}-disk.yaml')
            require(vm['spec']['template']['spec']['domain']['devices']['interfaces'][0]['macAddress'].lower() == mac and dv['spec']['source']['http']['url'] == i['imageURL'], 'Manifest/input wijkt af')
            macs.append(mac)
        require(len(set(macs)) == 2, 'Dubbele gast-MAC')
        selectors = kv['configuration']['permittedHostDevices']['usb'][0]['selectors']
        require(selectors == [{'vendor':inputs['usb']['vendor'], 'product':inputs['usb']['product']}], 'USB-invoer wijkt af')
        require(all(re.fullmatch(r'[0-9a-fA-F]{4}',v) for s in selectors for v in s.values()), 'Ongeldige USB-selector')
        require(re.fullmatch(r'[0-9a-fA-F]{64}',inputs['unifi']['hostInstallerSha256']) is not None and inputs['unifi']['hostInstallerURL'].startswith('https://'), 'UniFi OS Server-installer mist verificatie')
if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--release', action='store_true')
    try:
        validate(p.parse_args().release)
    except (ValueError, KeyError) as exc:
        p.exit(1, str(exc)+'\n')
