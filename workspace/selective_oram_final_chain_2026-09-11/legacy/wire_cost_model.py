#!/usr/bin/env python3
"""Analytical communication model, NOT a latency/throughput benchmark.
Finite-Binomial expectations use 100-digit Decimal with a negligible omitted
nonnegative tail, not a machine-verified interval certificate. The PRF profile
requires client tag uploads. Tree-top caching, XOR and frame/transport costs are
NOT modeled; the baselines are explicitly not globally optimized.
"""
from decimal import Decimal,localcontext
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
import math,json

@lru_cache(None)
def cover_probs(L:int):
    q=[Fraction(1),Fraction(0),Fraction(0)];probs=[Fraction(1)]
    for _ in range(L):
        choose=(q[0]+q[1])/2+q[2]
        probs.append(choose);q=[choose,q[0]/2,q[1]/2]
    return tuple(reversed(probs))

@lru_cache(None)
def er_expectation(n:int,p:Fraction,S:int):
    if p==1:return Decimal(max(0,(n-1)//S))
    with localcontext() as c:
        c.prec=100;dp=Decimal(p.numerator)/Decimal(p.denominator)
        pm=(1-dp)**n;value=Decimal(0);K=min(n,160)
        for k in range(K+1):
            value+=pm*max(0,(k-1)//S)
            if k<K:pm=pm*Decimal(n-k)/Decimal(k+1)*dp/(1-dp)
        return +value

def sde_cost(L,B=4096,Z=4,A=3,H=364,h=64):
    W=B+16;n=L+1;k=float(sum(cover_probs(L)))
    maintenance=2*n*(Z*W+H)+(3*L+2)*h
    return dict(cover=k,data_blocks=Z*k+2*Z*n/A,
        wire=k*(Z*W+2*H)+(3*L+2)*h+maintenance/A,
        deferred_wire=n*(Z*W+2*H)+(3*L+2)*h+maintenance/A,
        standard_path_wire=maintenance)

def ring_cost(L,S,selective,rootless,B=4096,Z=4,A=3,H=364,h=64):
    W=B+16;nslot=Z+S;ell=(nslot-1).bit_length()
    local_changed=nslot+sum((nslot+(1<<i)-1)//(1<<i) for i in range(1,ell+1))
    levels=list(range(1 if rootless else 0,L+1));q=len(levels)
    probs=cover_probs(L) if selective else (Fraction(1),)*(L+1)
    k=float(sum(probs[d] for d in levels))
    # Strict header-first, followed by a final metadata/tag update.
    logical=k*(W+2*H)+(3*L+(1 if rootless else 2)+k*(ell+1))*h
    maintenance=q*((2*Z+S)*W+2*H)+(2*L+1+q*(S+local_changed+2))*h
    early_wire=0.;early_blocks=0.;expected_reshuffles=0.
    for d in levels:
        rate=float(er_expectation(A*(1<<d),probs[d]/(1<<d),S))/A
        expected_reshuffles+=rate
        # Reuse the authenticated header/path skeleton within this logical access.
        early_wire+=rate*((2*Z+S)*W+H+(S+local_changed+d+2)*h)
        early_blocks+=rate*(2*Z+S)
    return dict(S=S,cover=k,expected_reshuffles_per_op=expected_reshuffles,
        data_blocks=k+q*(2*Z+S)/A+early_blocks,
        wire=logical+maintenance/A+early_wire,local_changed_tags=local_changed)

def run():
    checks={
        'ring_full_S5':ring_cost(23,5,False,False)['data_blocks'],
        'GC_S3':ring_cost(23,3,True,False)['data_blocks'],
        'R0_S3':ring_cost(23,3,True,True)['data_blocks']}
    known={'ring_full_S5':135.84918176044874,'GC_S3':110.90283997905934,'R0_S3':106.66474477502390}
    for k in known:assert abs(checks[k]-known[k])<1e-9,(k,checks[k],known[k])
    tables=[]
    for B in [128,1024,4096]:
        levels=[]
        # L13 is the second tree for the B=4096, 4-byte-entry example. For other
        # B these rows are only per-tree sensitivity, not a derived recursion.
        for L in [23,13]:
            path=sde_cost(L,B);ring=[ring_cost(L,S,False,False,B) for S in range(1,13)]
            gc=[ring_cost(L,S,True,False,B) for S in range(1,13)]
            r0=[ring_cost(L,S,True,True,B) for S in range(1,13)]
            levels.append(dict(L=L,path=path,ring_sweep=ring,gc_sweep=gc,r0_sweep=r0,
                best_ring_by_model=min(ring,key=lambda x:x['wire']),best_r0_by_model=min(r0,key=lambda x:x['wire'])))
        tables.append(dict(payload_bytes=B,levels=levels))
    main=tables[-1]['levels'];total_path=sum(x['path']['standard_path_wire'] for x in main)
    total_sde=sum(x['path']['wire'] for x in main)
    total_ring=sum(x['best_ring_by_model']['wire'] for x in main)
    total_r0=sum(next(v['wire'] for v in x['r0_sweep'] if v['S']==3) for x in main)
    out=dict(model='Client-computed PRF authentication tags; no top caching/XOR/network framing; analytical expectation, not benchmark.',
        finite_binomial_validation=checks,sensitivity=tables,
        two_tree_4096_profile=dict(standard_path_wire=total_path,SDE_wire=total_sde,
            Ring_wire_with_per_tree_S_sweep=total_ring,R0_S3_wire=total_r0,
            warning='Do not present these baselines or percentages as globally optimized or empirical. Keyed tags require uploads included here.'))
    (Path(__file__).resolve().parent/'wire_model_results.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out['finite_binomial_validation'],indent=2))
    print(json.dumps(out['two_tree_4096_profile'],indent=2))
if __name__=='__main__':run()
