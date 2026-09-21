"""Encrypted witnesses for two source-alignment choices, separate from workers."""
from common import *
import itertools,types
from collections import Counter
from fractions import Fraction as F
import heterogeneous_oram as h
import ir_stash_runtime as rt
from ir_stash import StashTree
from ir_initialization_alignment import CASES,distribution
from ir_skip_exact_process import tv


def trial(policy,queries,coins,order,ties):
    rt.install(dict(seed=271,R=16,cached_levels=1,Z_by_depth=[],index_sets=2,index_ways=4,indexed=True))
    b=rt.Backend('path',1,2,B=64,Z=1,A=2,S=1);b.tree.hold_address=None;calls=0
    def placement(self,pool,view,gamma,constrained):
        nonlocal calls
        held={u:r for u,r in list(pool.items()) if r.address==self.hold_address}
        for u in held:pool.pop(u)
        if policy['tie']=='uid':StashTree.placement(self,pool,view,gamma,constrained)
        else:
            # Init excludes the newly admitted target, so there is at most
            # one other block. Integrate its irrelevant tie coins analytically.
            if calls<2:assert len(pool)<=1;bit=0
            else:bit=ties[calls-2]
            changes={}
            for depth in reversed(view.selected):
                node=h.node(view.leaf,depth,self.c.L)
                chosen=[r for r in sorted(pool.values(),key=lambda r:r.address^bit)
                    if h.node(r.leaf,depth,self.c.L)==node][:1]
                for r in chosen:pool.pop(r.uid)
                changes[node]=self.prepare(node,view.headers[node],chosen,gamma)
            self.write(view,changes,'path');self.stash={r.address:r for r in pool.values()}
        for r in held.values():assert r.address not in self.stash;self.stash[r.address]=r
        calls+=1
    b.tree.placement=types.MethodType(placement,b.tree)
    leaves=[None,None]
    for j,a in enumerate(order):
        b.tree.hold_address=a;leaves[a]=coins[j];b.tick(None,0,admit=(a,leaves[a],bytes([a])*64))
    openings=[]
    def observe(c,op,seq,stage,meta,request,response):
        if op==h.OPEN_FULL:
            ro,tree,sq,flags,body=h.parse_frame(request);assert (ro,tree,sq,flags)==(op,c.tree,seq,0)
            openings.append(int.from_bytes(body[:8],'big'))
        return response
    b.io.mutator=observe;trace=[]
    for i,a in enumerate(queries):
        start=len(openings);local=b.local_access(a,leaf=leaves[a]) if policy['mode']!='no_skip' else None
        if local is None:
            b.tree.hold_address=a;answer=b.tick(a,leaves[a],replace=(coins[4+i],lambda p:p));leaves[a]=coins[4+i]
        else:
            b.tree.hold_address=a if policy['hold']=='all' else None
            answer=local[0];b.tick(None,coins[2+i] if policy['mode']=='uniform_dummy' else leaves[a])
        assert answer==bytes([a])*64 and len(openings)==start+1 and b.tree.t==b.tree.g==3+i
        trace.append(openings[start])
    assert calls==4
    return tuple(trace)


def main():
    mp=PACKAGE/'results/ir_initialization_alignment_model.json';model=json.loads(mp.read_text())
    assert model['model_sha256']==sha(Path(__file__).parent/'ir_initialization_alignment.py')
    source=rt.identity();results=[];executions=0
    for policy in CASES:
        row=next(r for r in model['rows'] if r['policy']==policy and r['requests']==2)
        queries=[tuple(row['left']),tuple(row['right'])] if 'left' in row else [(0,0),(0,1)]
        orders=[(0,1),(1,0)] if policy['secret_order'] else [(0,1)]
        pmfs=[];case_results=[]
        for qs in queries:
            counts=Counter();count=0
            for order in orders:
                for coins in itertools.product((0,1),repeat=6):
                    for ties in (list(itertools.product((0,1),repeat=2)) if policy['tie']=='uniform' else [(0,0)]):
                        counts[trial(policy,qs,coins,order,ties)]+=1;count+=1
            actual={k:F(v,count) for k,v in counts.items()};expected=distribution(policy,qs)
            assert actual==expected,(policy,qs,actual,expected)
            executions+=count;pmfs.append(actual);case_results.append(dict(queries=list(qs),executions=count,
                pmf={''.join(map(str,k)):str(v) for k,v in actual.items()}))
        d=tv(*pmfs);assert d==F(row['max_tv'])
        results.append(dict(policy=policy,cases=case_results,tv=str(d)))
        print(json.dumps(dict(policy=policy['name'],two_request_tv=str(d),executions=sum(c['executions'] for c in case_results))),flush=True)
    assert source==rt.identity() and executions==2176
    save(PACKAGE/'results/ir_initialization_alignment_crosscheck.json',dict(status='projection_crosschecked',results=results,executions=executions,
        checker_sha256=sha(__file__),source_hashes=source,model_receipt_sha256=sha(mp),model_sha256=model['model_sha256'],
        security_admission=False,native_paper_attack_claim=False,full_native_state_machine=False,
        scope='six Path-only policies, two-request witnesses, real encrypted frames; secret initialization order and immediate target exclusion',
        all_initialization_prefixes_checked=False,irrelevant_initialization_tie_coins_integrated=True))
    print(json.dumps(dict(status='projection_crosschecked',executions=executions,security_admission=False)),flush=True)


if __name__=='__main__':main()
