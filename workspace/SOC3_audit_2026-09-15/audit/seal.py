"""Maintainer operation: build a new explicit audit identity, never an audit pass."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'research_20260914/optimization_v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def contract():
    old=json.loads((V/'variant_contract.json').read_text())
    files=[V/name for name in old['artifact_sha256']]
    files += list((ROOT/'proofs').glob('*.md'))
    files += [V/'results/profile_comparison.json']
    import os
    old['scope_id']='SOC3-AUDIT-m2-Z4A3-Z7A6-2026-09-15'
    old['numeric_domains']={'Z4A3':{'height':[1,31],'threshold':[0,280]},'Z7A6':{'height':[1,24],'threshold':[0,280]}}
    old['deterministic_exception']='R>=N uses the actual current-count bound, not a larger ghost certificate.'
    old['artifact_sha256']={os.path.relpath(p,V).replace('\\','/'):sha(p) for p in sorted(set(files))}
    old['interpretation']='Audited research release; mathematical proofs and reproducible tests, not proof-assistant formalization or external third-party attestation.'
    (V/'variant_contract.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
    print('bound audit contract',len(files),'entries (before deduplication)')

def manifest():
    files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(ROOT.rglob('*'))
           if p.is_file() and p.name!='BUNDLE_MANIFEST.json' and '__pycache__' not in p.parts
           and 'tamper_fixture' not in p.parts}
    (ROOT/'BUNDLE_MANIFEST.json').write_text(json.dumps({'format':'SOC3-audit-bundle-v1','files':files},indent=2))
    print('bundle files',len(files))

if __name__=='__main__':
    import sys
    if '--contract' in sys.argv:contract()
    if '--manifest' in sys.argv:manifest()
