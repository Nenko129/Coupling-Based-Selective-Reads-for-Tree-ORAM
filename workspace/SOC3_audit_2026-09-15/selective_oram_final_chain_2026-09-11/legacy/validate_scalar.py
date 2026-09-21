#!/usr/bin/env python3
"""Independent exact-rational small-state checks of the scalar enclosure.
Exact enumeration uses the dyadic upper seed but exact rational Poisson ratios.
It checks EVERY retained total and accumulated unknown budgets at h<=4, C=8.
This is a regression check, not a substitute for the enclosure proof.
"""
from fractions import Fraction as F
from collections import defaultdict
from pathlib import Path
import csv,json,subprocess
ROOT=Path(__file__).resolve().parent

def exact_small(C=8,H=4,M=8):
    seed=json.loads((ROOT/'poisson_seed.json').read_text())
    pz=F.from_float(float.fromhex(seed['upper_hex']))
    poi=[pz]
    for k in range(1,M+2):poi.append(poi[-1]*F(3,2)/k)
    tau=poi[M+1]*F(M+2)/(F(M+2)-F(3,2))
    mtail=F(3,2)*poi[M]*F(M+1)/(F(M+1)-F(3,2))
    p={(0,0,0):F(1)}; bp=bm=F(0);answer=[]
    for h in range(1,H+1):
        mean=sum(sum(v)*q for v,q in p.items())+bm
        nxt=defaultdict(F); ep=em=F(0)
        # Deliberately enumerate left triple, right triple, and arrival independently.
        for lv,lp in p.items():
            for rv,rp in p.items():
                for k in range(M+1):
                    u=(max(0,sum(rv)+lv[2]+k-4),lv[0],lv[1])
                    w=lp*rp*poi[k]
                    if sum(u)<=C:nxt[u]+=w
                    else:ep+=w;em+=sum(u)*w
        bp,bm=2*bp+tau+ep,2*bm+2*(mean+F(3,2))*bp+2*mean*tau+mtail+em
        p=dict(nxt)
        answer.append(dict(h=h,bp=bp,bm=bm,sl=[sum(max(0,sum(v)-r)*q for v,q in p.items()) for r in range(C+1)]))
    return answer

def main():
    exact=exact_small(); checks=0
    for mode in ['up','next']:
        prefix=ROOT/f'validation_{mode}'
        subprocess.run([str(ROOT/'ghost_scalar'),'8','4','8','1',mode,str(prefix)],check=True,capture_output=True)
        rows=list(csv.DictReader(open(str(prefix)+'.csv')))
        levels=list(csv.DictReader(open(str(prefix)+'_levels.csv')))
        for e in exact:
            lev=levels[e['h']-1]
            assert F.from_float(float.fromhex(lev['unknown_prob_hex']))>=e['bp'];checks+=1
            assert F.from_float(float.fromhex(lev['unknown_moment_hex']))>=e['bm'];checks+=1
            for r in range(9):
                row=rows[(e['h']-1)*9+r]
                assert F.from_float(float.fromhex(row['known_upper_hex']))>=e['sl'][r];checks+=1
                assert F.from_float(float.fromhex(row['total_upper_hex']))>=e['sl'][r]+e['bm'];checks+=1
    # Bit-for-bit deterministic output probabilities across thread counts.
    p1,p4=ROOT/'validation_threads1',ROOT/'validation_threads4'
    for prefix,th in [(p1,'1'),(p4,'4')]:
        subprocess.run([str(ROOT/'ghost_scalar'),'32','8','32',th,'up',str(prefix)],check=True,capture_output=True)
    assert p1.with_suffix('.csv').read_bytes()==p4.with_suffix('.csv').read_bytes();checks+=1
    data=dict(exact_rational_inequalities=checks-1,thread_count_bitwise_match=True,
        exact_cap=8,exact_height=4,exact_poisson_cutoff=8,arithmetic_modes=['FE_UPWARD','nearest-plus-NextUp'],
        limitations='Both C++ modes share the recurrence implementation; exact Python enumeration independently validates a small finite domain.')
    (ROOT/'scalar_validation_results.json').write_text(json.dumps(data,indent=2))
    print(json.dumps(data,indent=2))
if __name__=='__main__':main()
