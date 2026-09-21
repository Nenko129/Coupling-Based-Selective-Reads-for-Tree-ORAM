"""Portable public entry point. No package downloads, no resealing on verify."""
from pathlib import Path
import argparse,json,hashlib,sys,time,platform
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    doc=json.loads((ROOT/'BUNDLE_MANIFEST.json').read_text())
    assert doc['format']=='SOC3-audit-bundle-v1'
    for name,digest in doc['files'].items():
        path=(ROOT/name).resolve();path.relative_to(ROOT)
        assert sha(path)==digest,'bundle file changed: '+name
    print('manifest PASS',len(doc['files']),'files',flush=True)
    return len(doc['files'])

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['verify','quick','all'],default='verify')
    p.add_argument('--out',type=Path)
    p.add_argument('--building-release',action='store_true',help='maintainer only: manifest does not exist yet; result is NOT a frozen-release verification')
    a=p.parse_args();start=time.perf_counter()
    hashes=None if a.building_release else verify()
    if a.mode=='verify':
        assert not a.building_release
        from integrated import identities
        print(json.dumps(identities(),indent=2));return
    assert a.out is not None,'--out is required; use an empty output directory outside the bundle'
    out=a.out.resolve()
    if not a.building_release:
        assert not out.is_relative_to(ROOT),'keep the frozen bundle read-only; --out must be outside it'
    assert not out.exists() or not any(out.iterdir()),'use a new empty output directory'
    out.mkdir(parents=True,exist_ok=True)
    inputs=[*sorted((ROOT/'audit').glob('*.py')),ROOT/'research_20260914/optimization_v1/variant_contract.json']
    input_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    import fusion,integrated,numerical
    numerical.seed_check();print('exact seed PASS',flush=True)
    f=fusion.audit(out/'fusion.json');print('fusion coupled execution PASS',flush=True)
    i=integrated.audit(out/'integrated');print('integrated artifact audit PASS',flush=True)
    n=numerical.audit(out/'numerical',full=True) if a.mode=='all' else None
    assert input_hashes=={p.relative_to(ROOT).as_posix():sha(p) for p in inputs},'audit inputs changed while running'
    result=dict(mode=a.mode,bundle_root=str(ROOT),output_root=str(out),frozen_manifest_files_verified=hashes,
                building_release=a.building_release,python=platform.python_version(),
                elapsed_seconds=time.perf_counter()-start,limited_scope='fusion proof interfaces; Z7A6 reduction/numerics; integrated evidence only',
                fusion_directed_cases=len(f['directed_cases']),paired_online_operations=sum(x['online_top_operations'] for x in f['paired_traces']),
                profiles_recomputed=len(i['profiles']),numeric_full_recomputed=n is not None,
                inputs_sha256=input_hashes,
                output_sha256={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*.json')) if 'tamper_fixture' not in p.parts})
    (out/'run_receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
