"""Raw artifact identities, exact profile re-evaluation, gates, protocol oracles."""
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
import sys,json,hashlib,zipfile,shutil

ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'research_20260914/optimization_v1'
B=ROOT/'selective_oram_final_chain_2026-09-11'
sys.path.insert(0,str(V/'src'));sys.path.append(str(B/'src'));sys.path.append(str(B/'legacy'))
import optimized_gate as gate
from optimized_oram import Config
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def identities():
    received=json.loads((ROOT/'provenance/received_manifest.json').read_text())['files']
    original=json.loads((B/'MANIFEST.sha256.json').read_text())['files']
    for name,digest in original.items():assert sha(B/name)==digest
    with zipfile.ZipFile(ROOT/'provenance/SOC3_received.zip') as z:
        names=set(z.namelist())
        for name,digest in received.items():
            if name.startswith('research_20260914/optimization_v1/'):
                assert name in names and hashlib.sha256(z.read(name)).hexdigest()==digest
        prefix='research_20260914/optimization_v1/'
        ct=json.loads(z.read(prefix+'variant_contract.json'))
        for name,digest in ct['artifact_sha256'].items():assert hashlib.sha256(z.read(prefix+name)).hexdigest()==digest
        manifest=json.loads(z.read(prefix+'OUTPUT_MANIFEST.sha256.json'))
        for name,digest in manifest.items():assert hashlib.sha256(z.read(prefix+name)).hexdigest()==digest
    bank=gate.OptimizedBank()
    # Algorithm changes would require a new proof, not just resealing hashes.
    for name in ('src/optimized_oram.py','src/fused_logical.py','src/optimized_cost.py','numerics/ghost_z7a6.cpp'):
        assert sha(V/name)==received['research_20260914/optimization_v1/'+name]
    receipt=json.loads((V/'numerics/recompute_receipt.json').read_text())
    for name,digest in receipt['source_and_outputs_sha256'].items():assert sha(V/'numerics'/name)==digest
    return dict(original_SOC2_manifest_files=len(original),received_SOC3_contract_files=len(ct['artifact_sha256']),
                received_SOC3_manifest_files=len(manifest),audited_contract_files=len(json.loads((V/'variant_contract.json').read_text())['artifact_sha256']),
                original_kernel_protocol_and_cost_byte_identical=True,original_numeric_receipt_verified=True)

def plans():
    from optimized_cost import expected_tree,sum_rows
    data=json.loads((V/'results/profile_comparison.json').read_text());bank=gate.OptimizedBank();out=[]
    online=(1<<64)-12582912-12288
    for row in data['variants']:
        cs=[Config(**x) for x in row['configs']];kind='sde' if row['label'].startswith('SDE-') else 'r0';off=2 if kind=='sde' else 6
        limit=(online+12582912)*bank.grids[4,3][24,192-off]+(online+12582912+12288)*bank.grids[4,3][14,144-off]
        fresh=bank.plan(cs,online,limit);old=row['capacity_plan']
        for key in ('online_horizon','stash_lifetime_upper','primitive_calls_upper','conditional_advantage_upper','persistent_payload_plus_terminal'):
            assert fresh[key]==old[key],(row['label'],key)
        for x,y in zip(fresh['points'],old['points']):
            assert {k:x[k] for k in y}==y
        cost=sum_rows([expected_tree(c) for c in cs])
        assert cost['total']==row['total'] and cost['components']==row['components']
        out.append(dict(label=row['label'],plan=fresh,bytes_recomputed=cost['total']))
    return out

def boundaries_and_tampering(out):
    bank=gate.OptimizedBank();c=Config('r0',23,1000,64,Z=7,A=6,S=6,R=280)
    accepted=bank.plan([c],0);assert accepted['points'][0]['certified_height_max']==24
    rejected=[]
    for label,x in [('h25',replace(c,L=24)),('h31',replace(c,L=30)),('r281',replace(c,R=293)),
                    ('negative_threshold',replace(c,R=11)),('wrong_A',replace(c,A=3)),('uncertified_Z7_SDE',replace(c,kind='sde'))]:
        try:bank.plan([x],0)
        except (ValueError,KeyError):rejected.append(label)
        else:raise AssertionError('out-of-domain configuration accepted '+label)
    deterministic=bank.plan([replace(c,L=24,N=10,R=10)],0)
    p=deterministic['points'][0]
    assert p['fixed_time_upper']=='0' and p['certified_height_max'] is None and p['rule']=='deterministic current count <= N'
    # Physically alter a disposable copy. The delivered frozen sources never change.
    target=out/'tamper_fixture';target.mkdir(parents=True,exist_ok=True)
    tv=target/'research_20260914/optimization_v1'
    shutil.copytree(V,tv,dirs_exist_ok=True)
    shutil.copytree(ROOT/'proofs',target/'proofs',dirs_exist_ok=True)
    saved=gate.ROOT;gate.ROOT=tv
    cases=[]
    try:
        gate.OptimizedBank() # ensure the fixture is valid before each mutation
        changes=[('src/fused_logical.py',lambda b:b+b'\n# tampered\n'),
                 ('numerics/z7a6_up_c280_h24_meta.json',lambda b:b.replace(b'"rate": "3"',b'"rate": "3/2"')),
                 ('numerics/z7a6_up_c280_h24_meta.json',lambda b:b.replace(b'"Z": 7',b'"Z": 4')),
                 ('numerics/z7a6_up_c280_h24_meta.json',lambda b:b.replace(b'"poisson_zero_upper_hex": "0x1.97db0ccceb0afp-5"',b'"poisson_zero_upper_hex": "0x1p-2"')),
                 ('numerics/z7a6_up_c280_h24.csv',lambda b:b.split(b'\n',2)[0]+b'\n'+b.split(b'\n',2)[2]),
                 ('numerics/z7a6_up_c280_h24.csv',lambda b:b.replace(b'1,0,',b'25,0,',1))]
        for i,(name,change) in enumerate(changes):
            path=tv/name;before=path.read_bytes();after=change(before);assert before!=after
            path.write_bytes(after)
            try:
                try:gate.OptimizedBank()
                except (ValueError,KeyError):cases.append(dict(file=name,case=i,rejected=True))
                else:raise AssertionError('physical tamper accepted '+name)
            finally:path.write_bytes(before)
        gate.OptimizedBank()
    finally:gate.ROOT=saved
    return dict(nontrivial_boundary_rejections=rejected,h24_accepted=True,h25_deterministic_exception=p,physical_mutations_rejected=cases)

def regression_oracles(out):
    import variant_tests as vt
    import new_profile_tests as nt
    import structural_and_gate_tests as st
    # Redirect only report output. The implementation still imports from V.
    vt.ROOT=out/'legacy_execution';(vt.ROOT/'results').mkdir(parents=True,exist_ok=True)
    functions=[('integrated_protocol',vt.integrated_runs),('original_active_attacks',vt.mutation_runs),
               ('local_openings',vt.slot_proofs_and_sampler),('Z7_actual_shadow_field',nt.new_execution),
               ('Z7_structural',st.structural),('original_gate_regressions',st.gate)]
    results={}
    for name,fn in functions:
        result=fn();results[name]=result;(out/(name+'.json')).write_text(json.dumps(result,indent=2))
        print(name,'PASS',flush=True)
    # Verify all research imports actually resolve inside the relocated bundle.
    imports={}
    for name in ('optimized_oram','fused_logical','optimized_gate','optimized_cost','variant_tests','new_profile_tests',
                 'structural_and_gate_tests','core_state_tests','reduction_checks','certified_driver','integrated_oram','unified_cost'):
        path=Path(sys.modules[name].__file__).resolve();path.relative_to(ROOT)
        imports[name]=path.relative_to(ROOT).as_posix()
    return dict(results=results,imports_within_bundle=imports)

def audit(out,execute=True):
    out.mkdir(parents=True,exist_ok=True)
    result=dict(identities=identities(),profiles=plans(),boundaries=boundaries_and_tampering(out))
    if execute:result['regression_oracles']=regression_oracles(out)
    (out/'receipt.json').write_text(json.dumps(result,indent=2))
    return result
