"""Exact L1/N2 process for studying repairs of the local-skip adaptation.

Not a capacity certificate or native-paper model. Probabilities are rational;
only the first remote leaf per public slot is retained as a transcript projection.
"""
from common import *
from collections import defaultdict
from fractions import Fraction as F
from functools import lru_cache
import itertools
import heterogeneous_oram as h

# State: ((uid, leaf, location) for each address), uid counter, time, gamma.
# Locations: -1=F, 1=cached root, 2/3=remote leaf buckets.


def plus(out,key,value):
    if value:out[key]+=value


def validate(state,kind):
    records,uid,t,g=state
    assert len({r[0] for r in records})==len(records)
    for u,leaf,pos in records:
        assert 0<u<=uid and leaf in (0,1) and pos in (-1,1,2+leaf)
        if pos==1 and kind=='sde':assert 0 in h.gc(g,leaf,1)
    assert all(sum(r[2]==p for r in records)<=1 for p in (1,2,3))


@lru_cache(None)
def place(records,leaf,gamma,constrained,tie,exclude):
    pool=tuple(i for i,r in enumerate(records) if r[2] in (-1,1,2+leaf))
    base=tuple((u,l,-1 if i in pool else p) for i,(u,l,p) in enumerate(records))
    branches={(base,pool):F(1)}
    for depth in (1,0):
        following=defaultdict(F)
        for (rs,left),mass in branches.items():
            candidates=[i for i in left if i!=exclude and (depth==0 or rs[i][1]==leaf)
                        and (not constrained or depth in h.gc(gamma,rs[i][1],1))]
            if not candidates:plus(following,(rs,left),mass);continue
            choices=candidates if tie=='uniform' else [min(candidates,key=lambda i:rs[i][0])]
            for a in choices:
                updated=list(rs);u,l,_=rs[a];updated[a]=(u,l,1 if depth==0 else 2+leaf)
                plus(following,(tuple(updated),tuple(i for i in left if i!=a)),mass/F(len(choices)))
        branches=following
    out=defaultdict(F)
    for (rs,left),mass in branches.items():plus(out,rs,mass)
    assert sum(out.values())==1
    return tuple(out.items())


def finish(rs,uid,t,g,kind,leaf,tie,exclude):
    if kind=='path':
        for updated,p in place(rs,leaf,g+1,False,tie,exclude):
            state=(updated,uid,t+1,g+1);validate(state,kind);yield state,p
    elif (t+1)%2==0:
        endpoint=g%2
        for updated,p in place(rs,endpoint,g+1,kind=='sde',tie,-1):
            state=(updated,uid,t+1,g+1);validate(state,kind);yield state,p
    else:
        state=(rs,uid,t+1,g);validate(state,kind);yield state,F(1)


@lru_cache(None)
def initial(kind,tie,hold_target):
    states={((),0,0,0):F(1)}
    for a in (0,1):
        following=defaultdict(F)
        for (rs,uid,t,g),mass in states.items():
            for leaf in (0,1):
                new=rs+((uid+1,leaf,-1),)
                for state,p in finish(new,uid+1,t,g,kind,0,tie,a if hold_target and kind=='path' else -1):
                    plus(following,state,mass*p/2)
        states=following
    assert sum(states.values())==1
    return tuple(states.items())


@lru_cache(None)
def step(state,target,kind,tie,hold_target,mode):
    rs,uid,t,g=state;u,old,pos=rs[target];local=pos in (-1,1)
    out=defaultdict(F)
    if mode=='no_skip' or not local:
        for fresh in (0,1):
            new=list(rs);new[target]=(uid+1,fresh,-1)
            for nxt,p in finish(tuple(new),uid+1,t,g,kind,old,tie,target if hold_target and kind=='path' else -1):
                plus(out,(nxt,old),p/2)
    else:
        pads=(0,1) if mode=='uniform_dummy' else (old,)
        assert mode in ('uniform_dummy','oldleaf_dummy')
        for pad in pads:
            for nxt,p in finish(rs,uid,t,g,kind,pad,tie,-1):plus(out,(nxt,pad),p/F(len(pads)))
    assert sum(out.values())==1
    return tuple(out.items())


def distribution(kind,tie,hold_target,mode,queries):
    states={(s,()):p for s,p in initial(kind,tie,hold_target)}
    for target in queries:
        following=defaultdict(F)
        for (state,trace),mass in states.items():
            for (nxt,leaf),p in step(state,target,kind,tie,hold_target,mode):plus(following,(nxt,trace+(leaf,)),mass*p)
        states=following
    out=defaultdict(F)
    for (state,trace),mass in states.items():plus(out,trace,mass)
    assert sum(out.values())==1
    return dict(out)


def tv(a,b):return sum(abs(a.get(k,F(0))-b.get(k,F(0))) for k in a.keys()|b.keys())/2


def scan():
    rows=[]
    for kind in ('path','deferred','sde'):
        for hold in ((False,True) if kind=='path' else (False,)):
            for tie in ('uid','uniform'):
                for mode in ('no_skip','uniform_dummy','oldleaf_dummy'):
                    for n in range(1,5):
                        qs=list(itertools.product((0,1),repeat=n))
                        ds={q:distribution(kind,tie,hold,mode,q) for q in qs}
                        maximum=F(0);witness=None
                        for left,right in itertools.combinations(qs,2):
                            distance=tv(ds[left],ds[right])
                            if distance>maximum:maximum=distance;witness=(left,right)
                        row=dict(kind=kind,hold_target=hold,tie=tie,mode=mode,requests=n,max_tv=str(maximum))
                        if witness:
                            left,right=witness;row.update(left=list(left),right=list(right),
                                left_pmf={''.join(map(str,k)):str(v) for k,v in ds[left].items()},
                                right_pmf={''.join(map(str,k)):str(v) for k,v in ds[right].items()})
                        rows.append(row)
                    print(json.dumps(dict(kind=kind,hold=hold,tie=tie,mode=mode,tv=[r['max_tv'] for r in rows[-4:]])),flush=True)
    # Reproduce the known one-slot result before accepting repair diagnostics.
    for kind in ('path','deferred','sde'):
        assert distribution(kind,'uid',False,'uniform_dummy',(0,))=={(0,):F(3,4),(1,):F(1,4)}
        assert distribution(kind,'uid',False,'uniform_dummy',(1,))=={(0,):F(5,8),(1,):F(3,8)}
    save(PACKAGE/'results/ir_skip_repair_exact_model.json',dict(status='exact_model_evaluated',model_sha256=sha(__file__),
        gc_source_sha256=sha(Path(h.__file__)),rows=rows,scope='L1/N2/Z1/A2 and first-leaf transcript projection; repair diagnostics only',
        security_admission=False,zero_distance_not_security_proof=True,encrypted_multistep_crosscheck_pending=True,
        probability='exact Fraction, independent leaf and uniform tie coins integrated at each step',
        repair_policy='hold_target excludes only the current remote requested/admitted block from its immediate Path write; not a native paper reproduction'))


if __name__=='__main__':scan()
