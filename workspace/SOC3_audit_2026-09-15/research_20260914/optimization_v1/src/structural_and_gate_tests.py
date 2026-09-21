"""Z7 structural interfaces and variant contract/horizon rejection tests."""
from optimized_gate import *
from optimized_oram import Config,ui
from dataclasses import replace
from collections import Counter
import random,json,sys
sys.path.append(str(BASE/'src'));sys.path.append(str(BASE/'legacy'))
from reduction_checks import state_from_field,recursion,local_step,independent_marking
from core_state_tests import pack

def structural():
    rng=random.Random(2467);counts=Counter()
    for L in range(1,5):
        for i in range(160):
            field=tuple(rng.randrange(13) for _ in range((1<<(L+1))-1));g=i%(3*(1<<L));ts=state_from_field(field,g,L);values=[]
            for rootless in (False,True):
                tree,stash=pack(ts,g,L,7,rootless)
                assert len(stash)==sum(recursion(field,g,L,7,rootless));counts['field_count_equalities']+=1
                values.append(len(stash));tagged={u:replace(t,stale=u%3==0) for u,t in ts.items()}
                newts,newtree,newstash=local_step(tagged,tree,stash,g,L,7,rootless)
                assert (newtree,newstash)==pack(newts,g+1,L,7,rootless);counts['commutations']+=1
            assert 0<=values[1]-values[0]<=7;counts['root_shifts']+=1
        A=6;N=A*(1<<(L-1));T=2*A*(1<<L)+1
        for mode in range(3):
            trace=[0 if mode==0 else t%N if mode==1 else rng.randrange(N) for t in range(T)]
            snapshots=sorted(set([1,5,6,7,T//2-1,T//2,T//2+1,T-1,T]))
            for t in snapshots:
                n,mu=independent_marking(trace,L,A,t);counts['marking_snapshots']+=1;counts['nonzero_marks']+=n
    return dict(counts)

def gate():
    bank=OptimizedBank();c=Config('r0',2,6,64,Z=7,A=6,S=6,R=12)
    bad=[replace(c,Z=4,A=4),replace(c,kind='path'),replace(c,kind='sde'),replace(c,compact=False),
         replace(c,fused=False),replace(c,S=7),replace(c,B=8192),replace(c,R=1),replace(c,tree=1)]
    rejected=0
    for x in bad:
        try:bank.plan([x],100)
        except ValueError:rejected+=1
        else:raise AssertionError('bad profile accepted')
    m=OptimizedCertifiedORAM([c],bytes(range(64)),2,bank);m.initialize();m.access(0);m.access(1)
    before=len(m.io.events)
    try:m.access(2)
    except Reject:pass
    else:raise AssertionError('horizon bypass')
    assert len(m.io.events)==before
    import optimized_gate as module
    original_sha=module.sha
    try:
        module.sha=lambda p:('0'*64 if Path(p).name=='optimized_oram.py' else original_sha(p))
        try:OptimizedBank()
        except ValueError:rejected+=1
        else:raise AssertionError('changed source identity accepted')
    finally:module.sha=original_sha
    return dict(rejected_profile_or_artifact_mutations=rejected,horizon_rejected_before_IO=True,
                numeric_points={str(k):len(v) for k,v in bank.grids.items()})

if __name__=='__main__':
    result={'structural':structural(),'gate':gate()}
    (ROOT/'results/structural_and_gate_tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
