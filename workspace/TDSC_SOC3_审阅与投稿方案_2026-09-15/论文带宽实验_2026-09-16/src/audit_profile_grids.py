"""Numerical admission is not inferred from a self-consistent summary."""
from common import *
from fractions import Fraction as F
import csv,math

NUM=PACKAGE/'numerics'
def grid(path):
    rows={}
    for r in csv.DictReader(path.open()):
        key=int(r['height']),int(r['threshold']);known=F.from_float(float.fromhex(r['known_upper_hex']));unknown=F.from_float(float.fromhex(r['unknown_moment_hex']))
        total=F.from_float(float.fromhex(r['total_upper_hex']));assert known>=0 and unknown>=0 and total>=known+unknown
        assert key not in rows;rows[key]=total
    return rows

def main():
    receipt=json.loads((NUM/'completed_jobs.json').read_text());assert receipt['all_jobs_complete']
    profiles={};details=[]
    for job in receipt['jobs']:
        prefix=PACKAGE/job['prefix'];path=prefix.with_suffix('.csv');assert sha(path)==job['grid_sha256']
        meta=json.loads(prefix.with_name(prefix.name+'_meta.json').read_text());specpath=NUM/'profiles'/f"{job['profile']}.json";spec=json.loads(specpath.read_text())
        assert meta['Z_root_to_leaf']==spec['Z_root_to_leaf']
        assert list(map(F,meta['rate_root_to_leaf']))==list(map(F,spec['lambda_root_to_leaf']))
        assert meta['seed_upper_root_to_leaf']==[spec['seeds'][x]['upper_hex'] for x in spec['lambda_root_to_leaf']]
        values=grid(path);H=job['height'];C=job['cap'];assert set(values)=={(h,r) for h in range(1,H+1) for r in range(C+1)}
        assert all(values[h,r]>=values[h,r+1] for h in range(1,H+1) for r in range(C))
        profiles.setdefault(job['profile'],[]).append(values)
        details.append(dict(profile=job['profile'],mode=job['mode'],complete=True,nonnegative_outward=True,monotone=True,profile_seed_bound=True))
    admissions=[]
    for name,grids in profiles.items():
        H=max(h for h,r in grids[0]);C=max(r for h,r in grids[0]);Q=1<<56;target=F(1,1<<132)
        rootless=name=='uniform76_h12';A=6 if rootless else 3;Z0=7 if rootless else 4;offset=A-1+(Z0 if rootless else 0)
        value=lambda r:max(g[H,r] for g in grids)
        minimum=next((r+offset for r in range(C+1) if Q*value(r)<=target),None)
        observed=[]
        for r in (128,186,200,240,254,268,280):
            x=value(r);observed.append(dict(threshold=r,log2_upper=math.log2(float(x)) if x else None))
        x=Q*value(256-offset)
        admissions.append(dict(profile=name,height=H,cap=C,offset=offset,Q=Q,R_tested=256,
              R256_lifetime_bound_exact=str(x),R256_lifetime_log2=math.log2(float(x)) if x else None,
              R256_meets_2m132=x<=target,minimum_R_within_grid=minimum,diagnostic_thresholds=observed))
    refs={'uniform43_h13':ROOT/'SOC3_audit_2026-09-15/selective_oram_final_chain_2026-09-11/certificates/ghost_up_c280_h31.csv',
          'uniform76_h12':FROZEN.parent/'numerics/z7a6_up_c280_h24.csv'}
    regression=[]
    for name,path in refs.items():
        a=profiles[name][0];b=grid(path);different=[k for k,v in a.items() if v!=b[k]]
        regression.append(dict(profile=name,points=len(a),bit_exact_equal_to_frozen_up=len(different)==0,
             differing_points=len(different),max_relative_difference=float(max((abs(a[k]-b[k])/max(a[k],b[k]) for k in a if a[k] or b[k]),default=F(0)))))
    save(NUM/'profile_grid_audit.json',dict(status='numerical_structure_audited',details=details,admission=admissions,uniform_regressions=regression,
         independent_third_party_audit=False,protocol_closure=False,interpretation='failed upper-bound admission is not a lower bound on actual overflow'))
    print(json.dumps(dict(admission=[{k:r[k] for k in ('profile','R256_meets_2m132','minimum_R_within_grid','R256_lifetime_log2')} for r in admissions],uniform_regressions=regression)))
if __name__=='__main__':main()
