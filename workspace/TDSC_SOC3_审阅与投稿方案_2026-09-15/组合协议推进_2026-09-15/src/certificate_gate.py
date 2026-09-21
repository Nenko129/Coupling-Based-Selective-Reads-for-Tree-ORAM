"""Reuse certified dyadic stop-loss bounds only under the transfer theorem contract."""
from pathlib import Path
from fractions import Fraction as F
import csv,hashlib,json,math

OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
FROZEN=ROOT/'SOC3_audit_2026-09-15'
GRIDS={(4,3):('selective_oram_final_chain_2026-09-11/certificates/ghost_up_c280_h31.csv',31),
       (7,6):('research_20260914/optimization_v1/numerics/z7a6_up_c280_h24.csv',24)}

def grid(Z,A):
    rel,maxh=GRIDS[(Z,A)];path=FROZEN/rel
    data={}
    for row in csv.DictReader(path.open(encoding='utf-8')):
        data[int(row['height']),int(row['threshold'])]=F.from_float(float.fromhex(row['total_upper_hex']))
    assert len(data)==maxh*281
    return data,maxh,path

def gate(Z,A,L,N,R,rootless,Q):
    assert N<=A*(1<<(L-1))
    if R>=N:return {'method':'deterministic population bound','lifetime_upper':'0'}
    data,maxh,path=grid(Z,A)
    assert L+1<=maxh
    offset=A-1+(Z if rootless else 0);r=R-offset
    assert 0<=r<=280
    epsilon=data[L+1,r];lifetime=Q*epsilon
    target=F(1,1<<132)
    minimum=next((threshold+offset for threshold in range(281) if Q*data[L+1,threshold]<=target),None)
    return {'method':'existing audited dyadic stop-loss grid, conditional transfer reduction',
            'Z':Z,'A':A,'L':L,'N_max':N,'R':R,'rootless':rootless,'h':L+1,'r':r,'Q_slot_bound':Q,
            'per_boundary_upper_exact':str(epsilon),'lifetime_upper_exact':str(lifetime),
            'lifetime_log2_upper_display':math.log2(float(lifetime)),
            'at_most_2^-132':lifetime<=target,'minimum_R_for_2^-132_in_grid':minimum,
            'grid':str(path),'grid_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
    rows=[]
    for Z,A in [(4,3),(7,6)]:
        for rootless in [False,True]:
            rows.append(gate(Z,A,8,273,128,rootless,1<<56))
    # A concrete large-map planning case, with all map levels included.
    counts=[1<<22]
    while counts[-1]>1:counts.append((counts[-1]+31)//32)
    total=sum(counts);L=math.ceil(math.log2(2*total/6))
    rows.append(gate(7,6,L,total,149,True,1<<56))
    rejection=[]
    for values in [(7,6,24,1000,149,True,1<<56),(7,6,23,1000,300,True,1<<56)]:
        try:gate(*values)
        except AssertionError:rejection.append({'L':values[2],'R':values[4],'rejected':True})
        else:raise AssertionError('out-of-domain gate accepted')
    payload={'numerical_grids_regenerated':False,'rows':rows,'out_of_domain_rejections':rejection,
             'large_unified_population':{'data':1<<22,'X':32,'level_populations':counts,'total':total,'L':L},
             'requires':['one admission at most per transfer slot','fixed coin-independent birth/retirement trace',
                         'fresh never-published admission labels','every A slots full bit-reversal service',
                         'immutable UID assigned at admission','fail-stop/no rollback'],
             'claim':'conditional stash bound only; not full native framework cryptographic closure'}
    (OUT/'results/certificate_reuse.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
