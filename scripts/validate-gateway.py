#!/usr/bin/env python3
"""Offline CRD-schema- en routecontrole; geen API- of clusterverbinding."""
from pathlib import Path
import sys
import jsonschema
import yaml

def documents(path):
    return [d for d in yaml.safe_load_all(Path(path).read_text()) if d]

def check(ok, message):
    if not ok:
        raise ValueError(message)

def validate(objects, definitions, services):
    schemas = {}
    for crd in definitions:
        if crd.get('kind') == 'CustomResourceDefinition':
            for version in crd['spec']['versions']:
                schemas[(crd['spec']['group'] + '/' + version['name'], crd['spec']['names']['kind'])] = version['schema']['openAPIV3Schema']
    for obj in objects:
        key = (obj['apiVersion'], obj['kind'])
        check(key in schemas, f'Schema ontbreekt: {key}')
        jsonschema.Draft7Validator(schemas[key]).validate(obj)
    by_kind = lambda kind: [d for d in objects if d['kind'] == kind]
    gateway, = by_kind('Gateway')
    check(gateway['metadata']['namespace'] == 'envoy-gateway-system', 'Gateway-namespace')
    listeners = {l['name']: l for l in gateway['spec']['listeners']}
    check(set(listeners) == {'argocd', 'paperclip', 'hubble'}, 'UI-inventaris')
    check(gateway['spec']['gatewayClassName'] == 'envoy-internal', 'GatewayClass')
    proxy, = by_kind('EnvoyProxy')
    check(proxy['spec']['provider']['kubernetes']['envoyService']['type'] == 'ClusterIP', 'Extern adres verboden')
    policy, = by_kind('SecurityPolicy')
    check(policy['spec']['authorization'] == {'defaultAction': 'Deny'}, 'Deny-all vereist')
    check(policy['spec']['targetRefs'] == [{'group': 'gateway.networking.k8s.io', 'kind': 'Gateway', 'name': 'admin'}], 'Policy-target')
    service_index = {(s['metadata'].get('namespace'), s['metadata']['name']): s for s in services if s.get('kind') == 'Service'}
    hosts = set()
    for route in by_kind('HTTPRoute'):
        ns = route['metadata']['namespace']
        parent, = route['spec']['parentRefs']
        check(parent['name'] == gateway['metadata']['name'] and parent['namespace'] == gateway['metadata']['namespace'], 'Verkeerde parent')
        listener = listeners[parent['sectionName']]
        check(listener['port'] == 443 and listener['protocol'] == 'HTTPS', 'HTTPS verplicht')
        check(listener['tls'] == {'mode': 'Terminate', 'certificateRefs': [{'group': '', 'kind': 'Secret', 'name': parent['sectionName'] + '-admin-tls'}]}, 'TLS-reference')
        check(listener['allowedRoutes']['namespaces']['selector']['matchLabels'] == {'kubernetes.io/metadata.name': ns}, 'Namespacebegrenzing')
        host, = route['spec']['hostnames']
        check(host == listener['hostname'] and host.endswith('.admin.home.arpa') and host not in hosts, 'Hostnaam')
        hosts.add(host)
        for rule in route['spec']['rules']:
            for backend in rule['backendRefs']:
                check('namespace' not in backend, 'Cross-namespace backend verboden')
                service = service_index.get((ns, backend['name']))
                check(service is not None, f'Service ontbreekt: {ns}/{backend["name"]}')
                check(backend['port'] in [p['port'] for p in service['spec']['ports']], f'Backendpoort ontbreekt: {ns}/{backend["name"]}:{backend["port"]}')
    tls, = by_kind('BackendTLSPolicy')
    check(tls['spec']['validation']['hostname'] == 'argocd-server.argocd.svc', 'Backend-SAN')
    check(tls['spec']['validation']['caCertificateRefs'] == [{'group': '', 'kind': 'ConfigMap', 'name': 'argocd-server-ca'}], 'Backend-CA')
    argo = service_index[('argocd', 'argocd-server')]
    check(any(p['name'] == tls['spec']['targetRefs'][0]['sectionName'] and p['port'] == 443 for p in argo['spec']['ports']), 'TLS-servicepoort')

if __name__ == '__main__':
    routes, controller, *rendered_services = sys.argv[1:]
    objects = documents(routes)
    definitions = documents(controller)
    services = [d for p in rendered_services for d in documents(p)]
    validate(objects, definitions, services)
    # Negatieve proeven: iedere fout moet worden geweigerd.
    from copy import deepcopy
    changes = [
        ('HTTPRoute', lambda d: d['spec']['rules'][0]['backendRefs'][0].update(port=1)),
        ('HTTPRoute', lambda d: d['spec']['parentRefs'][0].update(name='wrong')),
        ('Gateway', lambda d: d['spec']['listeners'][0].update(protocol='HTTP')),
        ('SecurityPolicy', lambda d: d['spec']['authorization'].update(defaultAction='Allow')),
        ('EnvoyProxy', lambda d: d['spec']['provider']['kubernetes']['envoyService'].update(type='LoadBalancer')),
    ]
    for kind, mutate in changes:
        broken = deepcopy(objects)
        mutate(next(d for d in broken if d['kind'] == kind))
        try:
            validate(broken, definitions, services)
        except (ValueError, jsonschema.ValidationError):
            continue
        raise ValueError(f'Negatieve proef geaccepteerd: {kind}')
    print(f'{len(objects)} resources: CRD-schema en routes goed; 5 negatieve proeven geweigerd. CEL/live controller-validatie niet uitgevoerd.')
