"""Bind the new static IR configuration to the existing heterogeneous grid.

Rechecks exact arithmetic and grid completeness; does not rerun or independently
re-prove the Poisson DP kernel or the protocol reduction.
"""
from pathlib import Path
import sys,json,csv
from fractions import Fraction as F
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minimal_runtime import *

def main():
    n=EVAL/'numerics';audit=json.loads((n/'IR43_scaled_L12_c480_m128_audit.json').read_text(encoding='utf-8'))
    pf=n/'profiles/IR43_scaled_L12.json';profile=json.loads(pf.read_text(encoding='utf-8'))
    assert sha(pf)==audit['identity']['profile_spec_sha256']
    assert sha(n/'profiles/IR43_scaled_L12.txt')==audit['identity']['profile_sha256']
    assert sha(n/'ghost_profile.cpp')==audit['identity']['kernel_sha256']
    zs=(4,4,4,4,4,4,2,2,2,3,3,4,4)
    assert tuple(profile['Z_root_to_leaf'])==zs and profile['lambda_root_to_leaf']==['3/2']*13
    x=F(3,2);term=F(1);series=F(1)
    for k in range(1,161):term*=x/k;series+=term
    tail=(term*x/161)/(1-x/162);lower=1/(series+tail);upper=1/series
    seed=profile['seeds']['3/2'];assert F.from_float(float.fromhex(seed['lower_hex']))<=lower<=upper<=F.from_float(float.fromhex(seed['upper_hex']))
    grids=[]
    for job in audit['jobs']:
        prefix=EVAL/job['prefix'];files=[Path(str(prefix)+s) for s in ('.csv','_meta.json','.log')]
        for f,key in zip(files,('grid_sha256','meta_sha256','log_sha256')):assert sha(f)==job[key]
        meta=json.loads(files[1].read_text(encoding='utf-8'));assert tuple(meta['Z_root_to_leaf'])==zs
        assert meta['height']==13 and meta['cap']==480 and meta['poisson_cutoff']==128
        assert meta['rate_root_to_leaf']==[1.5]*13 and meta['seed_upper_root_to_leaf']==[seed['upper_hex']]*13
        assert meta['rounding_self_test'] and not meta['renormalized'] and not meta['positive_states_discarded']
        rows={}
        with files[0].open(encoding='utf-8') as stream:
            for r in csv.DictReader(stream):
                coord=int(r['height']),int(r['threshold']);assert coord not in rows
                known=F.from_float(float.fromhex(r['known_upper_hex']));unknown=F.from_float(float.fromhex(r['unknown_moment_hex']))
                total=F.from_float(float.fromhex(r['total_upper_hex']));assert 0<=known+unknown<=total
                rows[coord]=total
        assert set(rows)=={(h,r) for h in range(1,14) for r in range(481)}
        assert all(rows[h,r]>=rows[h,r+1] for h in range(1,14) for r in range(480))
        grids.append(dict(mode=job['mode'],rows=len(rows),point=str(rows[13,478]),files={str(f.relative_to(common.ROOT)):sha(f) for f in files}))
    bound=(1<<56)*max(F(r['point']) for r in grids)
    claimed=next(r for r in audit['tested'] if r['R']==480)
    assert bound==F(claimed['lifetime_bound_exact']) and bound<=F(1,1<<132)
    matches=0
    for s in json.loads((HOME/'formal_plan.json').read_text(encoding='utf-8'))['specs']:
        if s['family']=='IR' and s['layout']=='depth':
            c=configuration(s);assert c.Z_by_depth==zs and c.L==12 and c.N==4096 and c.A==3 and c.R==480 and not c.rootless
            matches+=1
    save(HOME/'results/capacity_binding.json',dict(status='passed',new_specs_bound=matches,grids=grids,lifetime_bound_exact=str(bound),
        threshold=478,offset=2,Q=1<<56,target='2^-132',profile_sha256=sha(pf),audit_sha256=sha(n/'IR43_scaled_L12_c480_m128_audit.json'),
        scope='static IR profile/seed/grid/point rebinding and exact arithmetic; not new DP computation or independent third-party protocol certification'))
    print(json.dumps(dict(status='passed',specs=matches,points=sum(g['rows'] for g in grids),lifetime_log2=claimed['lifetime_log2'])))
if __name__=='__main__':main()
