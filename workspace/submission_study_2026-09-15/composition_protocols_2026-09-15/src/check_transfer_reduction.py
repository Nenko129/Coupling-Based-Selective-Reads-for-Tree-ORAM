"""Independent local/shadow/global-packing checks for fixed transfer histories."""
from pathlib import Path
from itertools import product
from fractions import Fraction as F
from collections import Counter
import json

OUT=Path(__file__).resolve().parents[1]

def rev(x,L):return int(format(x,f'0{L}b')[::-1],2)
def bucket(x,d,L):return (1<<d)+(x>>(L-d))
def lcp(x,y,L):return L-(x^y).bit_length()
def eligible(g,x,L):
    bits=(g-1-rev(x,L))%(1<<L);answer={L};misses=0
    for d in reversed(range(L)):
        if (bits>>d)&1 or misses==2:answer.add(d);misses=0
        else:misses+=1
    return answer

def local_service(positions,records,ep,g,L,Z,rootless):
    ds=range(1 if rootless else 0,L+1);path={bucket(ep,d,L) for d in ds}
    pool={u for u,b in positions.items() if b==-1 or b in path}
    answer={u:b for u,b in positions.items() if u not in pool}
    for d in reversed(list(ds)):
        b=bucket(ep,d,L)
        chosen=sorted(u for u in pool if bucket(records[u]['leaf'],d,L)==b and d in eligible(g,records[u]['leaf'],L))[:Z]
        for u in chosen:answer[u]=b;pool.remove(u)
    answer.update({u:-1 for u in pool});return answer

def global_pack(records,g,L,Z,rootless):
    # Independent from the local path: route every token from exact home.
    pool=set(records);positions={}
    for d in reversed(range(1 if rootless else 0,L+1)):
        for b in range(1<<d,1<<(d+1)):
            chosen=sorted(u for u in pool if records[u]['home']>=d and
                          bucket(records[u]['leaf'],d,L)==b and d in eligible(g,records[u]['leaf'],L))[:Z]
            for u in chosen:positions[u]=b;pool.remove(u)
    positions.update({u:-1 for u in pool});return positions

def run_history(L,Z,A,rootless,leaves,history):
    actual={};shadow={};records={};current={};g=0;uid=0;checks=0;fields=[]
    for slot,(remove,insert) in enumerate(history,1):
        if remove is not None:
            u=current.pop(remove);b=actual.pop(u);leaf=records[u]['leaf']
            if b!=-1:assert b.bit_length()-1 in eligible(g,leaf,L)
            records[u]['stale']=True
        if insert is not None:
            assert insert not in current
            u=uid;uid+=1;current[insert]=u
            records[u]={'leaf':leaves[u],'home':-1,'stale':False}
            actual[u]=-1;shadow[u]=-1
        if slot%A==0:
            ep=rev(g%(1<<L),L);g+=1
            retired=[u for u,r in records.items() if r['stale'] and r['leaf']==ep]
            for u in retired:records.pop(u);shadow.pop(u)
            for r in records.values():r['home']=max(r['home'],lcp(r['leaf'],ep,L))
            shadow=local_service(shadow,records,ep,g,L,Z,rootless)
            live_records={u:records[u] for u in current.values()}
            actual=local_service(actual,live_records,ep,g,L,Z,rootless)
        assert shadow==global_pack(records,g,L,Z,rootless)
        for u,b in actual.items():
            ad=-1 if b==-1 else b.bit_length()-1
            sb=shadow[u];sd=-1 if sb==-1 else sb.bit_length()-1
            assert ad>=sd,(slot,u,ad,sd)
            if b!=-1:assert ad in eligible(g,records[u]['leaf'],L)
        assert sum(b==-1 for b in actual.values())<=sum(b==-1 for b in shadow.values())
        fresh=sum(r['home']==-1 for r in records.values())
        assert fresh<=A-1,(slot,fresh,A)
        field=Counter(bucket(r['leaf'],r['home'],L) for r in records.values() if r['home']>=0)
        fields.append(field);checks+=1
    return fields,checks

def main():
    # Retirement and next admission intentionally have DIFFERENT identities.
    history=[(None,0),(0,1),(None,2),(1,None),(None,None),(2,3),
             (None,4),(3,None),(4,None)]+[(None,None)]*7
    rows=[];total=0
    for L in [1,2,3]:
        for A in [2,3]:
            # Maximum live population is two; N <= A*2^(L-1).
            for Z in [1,2]:
                for rootless in [False,True]:
                    accum=[Counter() for _ in history];cases=0
                    for leaves in product(range(1<<L),repeat=5):
                        fields,n=run_history(L,Z,A,rootless,leaves,history)
                        for a,f in zip(accum,fields):a.update(f)
                        total+=n;cases+=1
                    maximum=max((F(v,cases) for f in accum for v in f.values()),default=F(0))
                    assert maximum<=F(A,2),(L,A,Z,rootless,maximum)
                    rows.append({'L':L,'A':A,'Z':Z,'rootless':rootless,'leaf_assignments':cases,
                                 'largest_exact_home_mean':str(maximum),'poisson_rate_bound':str(F(A,2))})
    result={'status':'passed','configs':rows,'completed_boundaries_checked':total,
            'checked':['retrievability','actual-to-shadow depth domination','local/global exact uid packing',
                       'fresh <= A-1','fixed-history exact-home marginal mean <= A/2'],
            'proof_limit':'finite histories only; theorem and frontend admissibility are separate obligations'}
    (OUT/'results').mkdir(exist_ok=True)
    (OUT/'results/transfer_reduction_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'configurations':len(rows),'boundaries':total,'status':'passed'}))

if __name__=='__main__':main()
