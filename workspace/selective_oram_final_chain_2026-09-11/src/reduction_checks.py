#!/usr/bin/env python3
"""Finite independent checks of the NEW explicit reduction proof interfaces.
These checks test definitions and boundary cases; the proof text, not the count
of tests, supplies the arbitrary-depth/trace claim.
"""
from pathlib import Path
import sys,random,itertools,json
from fractions import Fraction
from collections import Counter
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'legacy'))
from core_state_tests import Token,pack,Shadow,mask,rev,node,lcp
ROOT=Path(__file__).resolve().parents[1]


def record_bit(g,ell,d,L):return ((g-1-rev(ell,L))%(1<<L)>>d)&1

def state_from_field(field,g,L):
    toks={};u=0
    for b,count in enumerate(field,1):
        d=b.bit_length()-1;prefix=b-(1<<d)
        candidates=[ell for ell in range(1<<L) if node(ell,d,L)==b and (d==L or record_bit(g,ell,d,L))]
        assert candidates
        for i in range(count):u+=1;toks[u]=Token(u,u,candidates[i%len(candidates)],0,d,False)
    return toks

def recursion(field,g,L,Z,rootless=False):
    states={}
    for b in range((1<<(L+1))-1,0,-1):
        d=b.bit_length()-1;p=field[b-1];cap=0 if rootless and b==1 else Z
        if d==L:states[b]=(max(p-cap,0),0,0);continue
        ell_left=((b-(1<<d))*2)<<(L-d-1)
        right=2*b if record_bit(g,ell_left,d,L) else 2*b+1
        left=(right^1);r=states[right];l=states[left]
        states[b]=(max(sum(r)+l[2]+p-cap,0),l[0],l[1])
    return states[1]


def local_step(tokens,tree,stash,g,L,Z,rootless):
    ep=rev(g%(1<<L),L)
    removed={u for u,t in tokens.items() if t.stale and t.leaf==ep}
    ts={u:replace(t,home=max(t.home,lcp(t.leaf,ep,L))) for u,t in tokens.items() if u not in removed}
    pool=set(stash)-removed;out=dict(tree);path=[node(ep,d,L) for d in range(L+1)]
    for b in path:pool.update(u for u in out[b] if u not in removed);out[b]=()
    for d in range(L,-1,-1):
        b=path[d];cap=0 if rootless and b==1 else Z
        legal=[u for u in sorted(pool) if node(ts[u].leaf,d,L)==b and d in mask(g+1,ts[u].leaf,L)]
        out[b]=tuple(legal[:cap]);pool.difference_update(out[b])
    return ts,out,tuple(sorted(pool))


def static_and_commutation():
    rng=random.Random(70173);static=comm=priority=rootshift=0
    configurations=[]
    for L,Z in [(1,1),(1,4),(2,1),(2,4),(3,1),(3,4),(4,4)]:
        if L==1:fields=list(itertools.product(range(7),repeat=3))
        elif L==2 and Z==1:fields=list(itertools.product(range(3),repeat=7))
        else:fields=[tuple(rng.randrange(Z+5) for _ in range((1<<(L+1))-1)) for _ in range(350)]
        for i,f in enumerate(fields):
            g=i%(3*(1<<L));ts=state_from_field(f,g,L)
            values=[]
            for rootless in (False,True):
                tree,stash=pack(ts,g,L,Z,rootless);expected=sum(recursion(f,g,L,Z,rootless))
                assert len(stash)==expected;static+=1;values.append(expected)
                # Changing immutable priorities cannot change the three-class count.
                order=list(ts);rng.shuffle(order)
                permuted={v:replace(ts[u],uid=v) for u,v in zip(ts,order)}
                assert len(pack(permuted,g,L,Z,rootless)[1])==expected;priority+=1
                tagged={u:replace(t,stale=(u%3==0)) for u,t in ts.items()}
                newts,newtree,newstash=local_step(tagged,tree,stash,g,L,Z,rootless)
                assert (newtree,newstash)==pack(newts,g+1,L,Z,rootless);comm+=1
            assert 0<=values[1]-values[0]<=Z;rootshift+=1
        configurations.append({'L':L,'Z':Z,'fields':len(fields)})
    return dict(static_class_equalities=static,priority_count_equalities=priority,phase_local_commutations=comm,
                root_capacity_shifts=rootshift,configurations=configurations)


def independent_marking(trace,L,A,t):
    g=t//A;births={};expiry={}
    for i,a in enumerate(trace[:t],1):
        if a in births:expiry[births[a]]=i
        births[a]=i
    mu=Counter();definitions=0
    for i in range(1,t+1):
        birth=(i-1)//A;end=(expiry[i]-1)//A if i in expiry else None
        for ell in range(1<<L):
            if end is not None and any(rev(k%(1<<L),L)==ell for k in range(end,g)):continue
            if birth>=g:continue # forced-stash fresh token, separately <=A-1
            h=max(lcp(ell,rev(k%(1<<L),L),L) for k in range(birth,g))
            mu[node(ell,h,L)]+=Fraction(1,1<<L);definitions+=1
    assert all(x<=Fraction(A,2) for x in mu.values()),(trace,L,A,t,mu)
    return definitions,mu


def load_and_history():
    histories=0;definitions=0;snapshots=0;rng=random.Random(6202)
    for L in range(1,5):
        A=3;N=A*(1<<(L-1));T=6*(1<<L)+9
        for mode in range(3):
            trace=[0 if mode==0 else t%N if mode==1 else rng.randrange(N) for t in range(T)]
            for t in range(1,T+1):
                d,mu=independent_marking(trace,L,A,t);definitions+=d;snapshots+=1
            histories+=1
    return dict(fixed_histories=histories,time_snapshots=snapshots,nonzero_independent_mark_cases=definitions,
                every_bucket_mean_at_most_A_over_2=True,
                quantifier='Logical address history fixed independently of ORAM randomness; not conditioning on an adaptively selected trace.')


def main():
    out={'static':static_and_commutation(),'marking':load_and_history(),
         'status':'Finite regressions of the separately written reduction proof, not a proof assistant certificate.'}
    (ROOT/'results/reduction_checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
