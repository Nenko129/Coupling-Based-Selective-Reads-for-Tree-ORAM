"""Exact Path-only diagnostics for secret initialization order and target holds.

Aligns two specific source-paper choices; not a complete native IR model.
The shared observed initialization prefix consists of two path-0 admissions.
"""
from common import *
from collections import defaultdict
from fractions import Fraction as F
from functools import lru_cache
import itertools
import ir_skip_exact_process as m

CASES=[
    dict(name='known_order_remote_hold',secret_order=False,tie='uid',hold='remote',mode='uniform_dummy'),
    dict(name='secret_order_remote_hold',secret_order=True,tie='uid',hold='remote',mode='uniform_dummy'),
    dict(name='secret_order_random_ties',secret_order=True,tie='uniform',hold='remote',mode='uniform_dummy'),
    dict(name='secret_order_hold_local_too',secret_order=True,tie='uid',hold='all',mode='uniform_dummy'),
    dict(name='secret_order_oldleaf_padding',secret_order=True,tie='uid',hold='remote',mode='oldleaf_dummy'),
    dict(name='full_remap_control',secret_order=True,tie='uid',hold='remote',mode='no_skip'),
]


def initial(policy):
    states=defaultdict(F)
    for state,p in m.initial('path',policy['tie'],True):
        rs,uid,t,g=state
        m.plus(states,state,p/2 if policy['secret_order'] else p)
        if policy['secret_order']:m.plus(states,(tuple(reversed(rs)),uid,t,g),p/2)
    assert sum(states.values())==1
    return dict(states)


@lru_cache(None)
def step(state,a,tie,hold,mode):
    rs,uid,t,g=state;u,old,pos=rs[a];local=pos in (-1,1);out=defaultdict(F)
    if not local or mode=='no_skip':
        for fresh in (0,1):
            updated=list(rs);updated[a]=(uid+1,fresh,-1)
            for nxt,p in m.finish(tuple(updated),uid+1,t,g,'path',old,tie,a):m.plus(out,(nxt,old),p/2)
    else:
        pads=(0,1) if mode=='uniform_dummy' else (old,)
        for pad in pads:
            for nxt,p in m.finish(rs,uid,t,g,'path',pad,tie,a if hold=='all' else -1):m.plus(out,(nxt,pad),p/F(len(pads)))
    assert sum(out.values())==1
    return tuple(out.items())


def distribution(policy,queries):
    states={(s,()):p for s,p in initial(policy).items()}
    for a in queries:
        follow=defaultdict(F)
        for (state,trace),mass in states.items():
            for (nxt,leaf),p in step(state,a,policy['tie'],policy['hold'],policy['mode']):m.plus(follow,(nxt,trace+(leaf,)),mass*p)
        states=follow
    out=defaultdict(F)
    for (state,trace),mass in states.items():m.plus(out,trace,mass)
    assert sum(out.values())==1
    return dict(out)


def main():
    rows=[]
    for case in CASES:
        for n in range(1,5):
            qs=list(itertools.product((0,1),repeat=n));ds={q:distribution(case,q) for q in qs};maximum=F(0);witness=None
            for a,b in itertools.combinations(qs,2):
                d=m.tv(ds[a],ds[b])
                if d>maximum:maximum=d;witness=(a,b)
            row=dict(policy=case,requests=n,max_tv=str(maximum))
            if witness:
                a,b=witness;row.update(left=list(a),right=list(b),left_pmf={''.join(map(str,k)):str(v) for k,v in ds[a].items()},
                    right_pmf={''.join(map(str,k)):str(v) for k,v in ds[b].items()})
            rows.append(row)
        print(json.dumps(dict(policy=case['name'],max_tv=[r['max_tv'] for r in rows[-4:]])),flush=True)
    assert all(r['max_tv']=='0' for r in rows if r['policy']['mode']=='no_skip')
    prior=json.loads((PACKAGE/'results/ir_skip_repair_exact_model.json').read_text())
    for row in rows:
        if row['policy']['name']=='known_order_remote_hold':
            old=next(r for r in prior['rows'] if (r['kind'],r['tie'],r['hold_target'],r['mode'],r['requests'])==('path','uid',True,'uniform_dummy',row['requests']))
            assert row['max_tv']==old['max_tv']
    save(PACKAGE/'results/ir_initialization_alignment_model.json',dict(status='model_evaluated',rows=rows,
        model_sha256=sha(__file__),base_model_sha256=sha(Path(m.__file__)),prior_receipt_sha256=sha(PACKAGE/'results/ir_skip_repair_exact_model.json'),
        scope='Path L1/N2/Z1, two uniform-secret initialization orderings; fixed observed path-0 admission prefix; first-leaf projection',
        initialized_blocks=2,initialization_path_prefix=[0,0],prefix_probability_if_independent_uniform_paths='1/4',
        holds_current_remote_target=True,all_hold_is_additional_research_policy=True,
        zero_distance_is_not_proof=True,full_native_state_machine=False,encrypted_crosscheck_pending=True,security_admission=False))


if __name__=='__main__':main()
