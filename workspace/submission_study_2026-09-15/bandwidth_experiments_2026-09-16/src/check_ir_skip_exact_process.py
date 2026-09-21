"""Cross-check two-slot exact repair diagnostics against encrypted frames."""
from common import *
import itertools,types
from collections import Counter
from fractions import Fraction as F
import heterogeneous_oram as h
import ir_stash_runtime as rt
from ir_skip_exact_process import distribution,tv


def trial(kind,mode,queries,coins,tiecoins=None):
    rt.install(dict(seed=121,R=16,cached_levels=1,Z_by_depth=[],index_sets=2,index_ways=4,indexed=True))
    b=rt.Backend(kind,1,2,B=64,Z=1,A=2,S=1)
    if tiecoins is not None:
        tape=iter(tiecoins)
        def randomized_placement(self,pool,view,gamma,constrained):
            # With two addresses and Z1, one fair order per placement is
            # equivalent to the exact model's uniform choice at each tie.
            bit=next(tape);changes={}
            for depth in reversed(view.selected):
                node=h.node(view.leaf,depth,self.c.L)
                chosen=[r for r in sorted(pool.values(),key=lambda r:r.address^bit)
                    if h.node(r.leaf,depth,self.c.L)==node and (not constrained or depth in h.gc(gamma,r.leaf,self.c.L))][:1]
                for r in chosen:pool.pop(r.uid)
                changes[node]=self.prepare(node,view.headers[node],chosen,gamma)
            self.write(view,changes,'path' if self.c.kind=='path' else 'evict')
            self.stash={r.address:r for r in pool.values()}
        b.tree.placement=types.MethodType(randomized_placement,b.tree)
    leaves=list(coins[:2]);pads=coins[2:4];fresh=coins[4:6]
    for a in (0,1):b.tick(None,0,admit=(a,leaves[a],bytes([a])*64))
    openings=[]
    def observe(c,op,seq,stage,meta,request,response):
        if op==h.OPEN_FULL:
            ro,tree,sq,flags,body=h.parse_frame(request)
            assert (ro,tree,sq,flags)==(op,c.tree,seq,0)
            openings.append(int.from_bytes(body[:8],'big'))
        return response
    b.io.mutator=observe;observed=[]
    for i,target in enumerate(queries):
        start=len(openings)
        local=b.local_access(target,leaf=leaves[target]) if mode!='no_skip' else None
        if local is None:
            answer=b.tick(target,leaves[target],replace=(fresh[i],lambda p:p));leaves[target]=fresh[i]
        else:
            answer=local[0];b.tick(None,pads[i] if mode=='uniform_dummy' else leaves[target])
        assert answer==bytes([target])*64 and len(openings)>start and b.tree.t==3+i
        observed.append(openings[start])
    if tiecoins is not None:assert next(tape,None) is None
    return tuple(observed)


def main():
    source=rt.identity();results=[];executions=0
    for kind in ('path','deferred','sde'):
        for mode in ('no_skip','uniform_dummy','oldleaf_dummy'):
            for qs in itertools.product((0,1),repeat=2):
                counts=Counter(trial(kind,mode,qs,coins) for coins in itertools.product((0,1),repeat=6));executions+=64
                actual={q:F(n,64) for q,n in counts.items()}
                expected=distribution(kind,'uid',False,mode,qs);assert actual==expected,(kind,mode,qs,actual,expected)
                results.append(dict(kind=kind,tie='uid',mode=mode,queries=list(qs),executions=64,
                    pmf={''.join(map(str,k)):str(v) for k,v in actual.items()}))
        print(json.dumps(dict(kind=kind,tie='uid',checked=12)),flush=True)
    # The tempting randomized-tie repair has zero one-slot distance but a
    # nonzero two-slot distance. Cross-check its witness in actual encryption.
    witnesses=[]
    for kind in ('path','deferred','sde'):
        query_pairs=[(0,0),(0,1)];pmfs=[];tie_bits=4 if kind=='path' else 2
        for qs in query_pairs:
            counts=Counter()
            for coins in itertools.product((0,1),repeat=6):
                for ties in itertools.product((0,1),repeat=tie_bits):counts[trial(kind,'uniform_dummy',qs,coins,ties)]+=1;executions+=1
            denominator=64*2**tie_bits;actual={q:F(n,denominator) for q,n in counts.items()}
            expected=distribution(kind,'uniform',False,'uniform_dummy',qs);assert actual==expected
            pmfs.append(actual)
            results.append(dict(kind=kind,tie='uniform',mode='uniform_dummy',queries=list(qs),executions=denominator,
                pmf={''.join(map(str,k)):str(v) for k,v in actual.items()}))
        distance=tv(*pmfs);assert distance==F(3,16)
        witnesses.append(dict(kind=kind,queries=query_pairs,tv=str(distance)))
        print(json.dumps(dict(kind=kind,tie='uniform',two_slot_tv=str(distance))),flush=True)
    assert source==rt.identity()
    model_path=PACKAGE/'results/ir_skip_repair_exact_model.json';model=json.loads(model_path.read_text())
    assert model['model_sha256']==sha(Path(__file__).parent/'ir_skip_exact_process.py')
    save(PACKAGE/'results/ir_skip_repair_model_crosscheck.json',dict(status='projection_model_crosschecked',source_hashes=source,
        checker_sha256=sha(__file__),model_sha256=model['model_sha256'],model_receipt_sha256=sha(model_path),
        executions=executions,cases=results,randomized_tie_witnesses=witnesses,
        scope='all UID-policy two-slot traces in three padding/remap modes; selected uniform-tie repair witnesses; real encrypted remote request fields',
        scripted_uniform_tie_is_research_variant=True,native_paper_attack_claim=False,security_admission=False,
        conclusion='neither randomizing placement ties nor using the unchanged old leaf for padding establishes a repair'))
    print(json.dumps(dict(status='projection_model_crosschecked',executions=executions,cases=len(results),random_tie_two_slot_tv='3/16')),flush=True)


if __name__=='__main__':main()
