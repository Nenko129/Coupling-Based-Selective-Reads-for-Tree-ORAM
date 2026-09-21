"""Exact small-domain audit of local-hit skipping plus uniform dummy padding.

This checks our Transfer adaptation, not the original IR-ORAM artifact. Read
only the first leaf in an actual serialized remote opening for the distinguisher.
"""
from common import *
import itertools
from collections import Counter
from fractions import Fraction as F
import heterogeneous_oram as h
import ir_stash_runtime as rt


def trial(kind,skip,target,labels,pad,fresh,seed):
    rt.install(dict(seed=seed,R=16,cached_levels=1,Z_by_depth=[],index_sets=2,index_ways=4,indexed=True))
    b=rt.Backend(kind,1,2,B=64,Z=1,A=2,S=1)
    prefix=[]
    def observe_prefix(c,op,seq,stage,meta,request,response):
        if op==h.OPEN_FULL:
            po,tree,sq,flags,body=h.parse_frame(request)
            assert (po,tree,sq,flags)==(op,c.tree,seq,0)
            prefix.append(int.from_bytes(body[:8],'big'))
        return response
    b.io.mutator=observe_prefix
    for a in (0,1):b.tick(None,0,admit=(a,labels[a],bytes([a])*64))
    assert prefix and set(prefix)=={0}
    assert b.tree.t==2 and b.tree.g==(2 if kind=='path' else 1)
    assert b.tree.local_metrics['placement_set_conflicts']==0
    openings=[]
    def observe(c,op,seq,stage,meta,request,response):
        if op==h.OPEN_FULL:
            po,tree,sq,flags,body=h.parse_frame(request)
            assert (po,tree,sq,flags)==(op,c.tree,seq,0)
            openings.append(int.from_bytes(body[:8],'big'))
        return response
    b.io.mutator=observe;b.io.reset_meter()
    result=b.local_access(target,leaf=labels[target]) if skip else None
    if result is None:
        answer=b.tick(target,labels[target],replace=(fresh,lambda p:p))
    else:
        answer=result[0];b.tick(None,pad)
    assert answer==bytes([target])*64 and openings and b.tree.t==3
    assert b.io.snapshot()['rpc']>0 and not b.tree.dead
    return openings[0],dict(prefix=prefix,local=result is not None,location=None if result is None else result[1])


def main():
    source=rt.identity();results=[];raw=[]
    for seed in (121,122):
        for kind in ('path','deferred','sde'):
            for skip in (False,True):
                distributions=[]
                for target in (0,1):
                    counts=Counter()
                    for a,b,pad,fresh in itertools.product((0,1),repeat=4):
                        leaf,detail=trial(kind,skip,target,(a,b),pad,fresh,seed);counts[leaf]+=1
                        raw.append(dict(seed=seed,kind=kind,skip=skip,target=target,labels=[a,b],padding_leaf=pad,
                            fresh_leaf=fresh,observed_remote_leaf=leaf,**detail))
                    assert sum(counts.values())==16
                    distributions.append({j:F(counts[j],16) for j in (0,1)})
                tv=sum(abs(distributions[0][j]-distributions[1][j]) for j in (0,1))/2
                if skip:
                    assert distributions==[{0:F(3,4),1:F(1,4)},{0:F(5,8),1:F(3,8)}] and tv==F(1,8)
                else:assert distributions==[{0:F(1,2),1:F(1,2)}]*2 and tv==0
                results.append(dict(seed=seed,kind=kind,skip=skip,pmf=[{str(j):str(v) for j,v in d.items()} for d in distributions],
                    total_variation=str(tv),equal_one_transfer_count=True,not_an_original_paper_attack=True))
    assert source==rt.identity()
    save(PACKAGE/'results/ir_stash_transcript_counterexample.json',dict(status='counterexample_confirmed',source_hashes=source,
        checker_sha256=sha(__file__),cases=results,executions=len(raw),raw=raw,
        scope='our L1/N2/Z1/A2 Transfer adaptation after a fixed visible initialization prefix, flat trusted leaf lookup; not a native IR system experiment',
        observed_field='leaf from first actual below-cut OPEN_FULL request body, parsed from serialized frame',
        randomness='exhaustive independent initial leaves, padding leaf and fresh remap leaf; unused tape coordinates integrated out; two crypto keys',
        canonical_placement='UID-ordered greedy policy of this artifact; permutation coins do not change logical location',
        interpretation='fixed slot count plus independent uniform padding is insufficient for this local-hit adaptation',
        security_admission=False,capacity_certificate=False,native_paper_attack_claim=False,
        action='hold all performance/security claims for the new local-hit variants until a repair and transcript proof are supplied; earlier no-skip results unaffected'))
    print(json.dumps(dict(status='counterexample_confirmed',executions=len(raw),conditional_tv='1/8',no_skip_tv='0',families=3)),flush=True)


if __name__=='__main__':main()
