"""Authenticated CB functional tests and exact local permutation checks.

This supplies implementation evidence, not a green-aware capacity certificate or
a complete adaptive transcript proof. Test-only plaintext/position inventories
are external oracles and never used by the execution path.
"""
from common import *
import copy,random
from collections import Counter
from itertools import combinations
from fractions import Fraction
import cb_oram as h
from cb_transfer import TransferConfig,TransferTree
from cb_fusion import eligible_slots
from fast_prf import make_fast_prf
import cached_transport as cache
from audit_frontend_batches import check_bill


def identity():
    names=('cb_oram.py','cb_transfer.py','cb_fusion.py','cached_transport.py','fast_prf.py','heterogeneous_oram.py')
    return {n:sha(Path(__file__).parent/n) for n in names}


def create(kind,C,S,Y,cut,heterogeneous=False):
    c=TransferConfig(kind=kind,L=6,N=64,B=64,Z=C,A=5,S=S,Y=Y,R=500,
        S_by_depth=(7,7,7,7,4,4,4) if heterogeneous else ())
    cache.install({0:cut});server=cache.RemoteServer([c]);io=cache.CachedTransport(server)
    t=TransferTree(c,make_fast_prf(h)(b'C'*64),io);t.initialize()
    leaves={a:(13*a+7)%64 for a in range(64)};truth={a:a.to_bytes(8,'big')+bytes(56) for a in range(64)}
    for a in range(64):t.transfer(None,(a*23)%64,admit=(a,leaves[a],truth[a]))
    return t,io,server,leaves,truth


def inventory(t,io,server,truth,leaves):
    c=t.c;out=dict(t.stash);uids={r.uid for r in out.values()}
    for (tree,b),stored in list(server.buckets.items())+list(io.local_buckets.items()):
        if c.rootless and b==1:continue
        bc=c.at(b);pub=stored.header[:h.PUBLIC]
        header=h.Header.decode(bc,pub,t.P.decrypt(t.ctx,t.oid(b),pub,stored.header[h.PUBLIC:]))
        assert header.count==header.used.bit_count()<=bc.S and 0<=header.green<=bc.Y
        for j,d in header.live.items():
            assert d.address not in out and d.uid not in uids
            data=t.P.decrypt(t.ctx,t.oid(b,j),h.ui(header.w),stored.slots[j])
            assert h.node(d.leaf,h.depth(b),c.L)==b
            if c.selective:assert h.depth(b) in h.gc(header.gamma,d.leaf,c.L)
            out[d.address]=h.Record(d.uid,d.address,d.leaf,data);uids.add(d.uid)
    assert set(out)==set(truth)
    assert all((r.payload,r.leaf)==(truth[a],leaves[a]) for a,r in out.items())
    return out


def local_exact():
    cases=0;zero=0;maxchoices=0
    # Condition on a fixed public used set. Remaining hidden real slots are
    # exchangeable. Sum exact rational probabilities, without float tolerance.
    for C in range(1,6):
        for D in range(4):
            for Y in range(C+1):
                S=D+Y
                if S==0:continue
                c=TransferConfig(kind='ring',L=5,N=16,B=64,Z=C,A=1,S=S,Y=Y,R=64)
                for t in range(S+1):
                    unused=tuple(range(t,c.n));U=len(unused);cover=min(C,U)
                    for r in range(min(C,U)+1):
                        for G in range(min(Y,t,C-r)+1):
                            placements=list(combinations(unused,r));one=Counter();target=Counter();covers=Counter()
                            for live in placements:
                                hd=h.Header(count=t,used=(1<<t)-1,green=G,
                                    live={j:h.Desc(k+1,k,0,j) for k,j in enumerate(live)})
                                if t<S:
                                    pool=eligible_slots(c,hd,c.N+999);assert pool
                                    for j in pool:one[j]+=Fraction(1,len(placements)*len(pool))
                                    if r:
                                        # Average over all possible locations of the target's label.
                                        for j in live:
                                            hh=copy.deepcopy(hd);hh.live[j]=h.Desc(99,15,0,j)
                                            assert eligible_slots(c,hh,15)==(j,)
                                            target[j]+=Fraction(1,len(placements)*r)
                                dummy=[j for j in unused if j not in live];k=cover-r
                                assert 0<=k<=len(dummy)
                                all_extra=list(combinations(dummy,k))
                                for rank,extra in enumerate(all_extra):
                                    assert h.choose_rank(dummy,k,rank)==extra
                                    covers[tuple(sorted(live+extra))]+=Fraction(1,len(placements)*len(all_extra))
                            if t<S:
                                assert set(one)==set(unused) and set(one.values())=={Fraction(1,U)}
                                if r:assert set(target)==set(unused) and set(target.values())=={Fraction(1,U)}
                            assert len(covers)==__import__('math').comb(U,cover)
                            assert set(covers.values())=={Fraction(1,len(covers))}
                            cases+=1;zero+=int(cover==0);maxchoices=max(maxchoices,len(covers))
    return dict(cases=cases,zero_cover_cases=zero,max_distinct_cover_sets=maxchoices,
        statement='single-step ideal-uniform slot and cover marginals under an exchangeable hidden layout, not an adaptive global simulator')


def main():
    before=identity();cases=[];rng=random.Random(887)
    trace=[(rng.randrange(64),rng.randrange(64),rng.randrange(2)) for _ in range(160)]
    for kind in ('ring','gc_ring','r0'):
        for C,S,Y,heterogeneous in ((5,3,0,False),(5,7,4,False),(5,5,5,False),(5,7,4,True)):
            for cut in (0,2):
                t,io,server,leaves,truth=create(kind,C,S,Y,cut,heterogeneous);io.reset_meter()
                for i,(a,leaf,write) in enumerate(trace):
                    data=hashlib.sha256(str(i).encode()).digest()*2 if write else truth[a]
                    prior=t.transfer(a,leaves[a],replace=(leaf,lambda p,v=data:v));assert prior==truth[a]
                    leaves[a]=leaf;truth[a]=data
                    if i%40==0:inventory(t,io,server,truth,leaves)
                # Repeated dummy paths deliberately drive count to threshold and
                # exercise the n-count < C and zero-cover cases.
                for i in range(80):t.transfer(None,0)
                inventory(t,io,server,truth,leaves);bill=io.snapshot();check_bill(bill)
                assert (t.cb_metrics['green_promotions']>0)==(Y>0)
                if Y==C:assert t.cb_metrics['zero_cover_buckets']>0
                cases.append(dict(kind=kind,C=C,S=S,Y=Y,physical_dummy=S-Y,cut=cut,S_by_depth=list(t.c.S_by_depth),
                    checked_transfers=240,bytes=bill['total_bytes'],metrics=dict(t.cb_metrics),max_boundary=t.max_boundary))
    failures=[]
    for op in (h.OPEN_HEAD,h.READ_SLOTS,h.WRITE):
        t,io,server,leaves,truth=create('r0',5,5,5,2);fired=[False];decryptions_at_fault=[None]
        green_before=t.cb_metrics['green_promotions']
        def mutate(c,opcode,seq,stage,meta,request,response):
            if not fired[0] and opcode==op and stage=='logical':
                fired[0]=True;decryptions_at_fault[0]=t.P.decryptions
                return response[:-1]+bytes([response[-1]^1])
            return response
        io.mutator=mutate
        try:t.transfer(0,leaves[0],replace=(17,lambda p:p))
        except (h.Reject,cache.h.Reject):pass
        else:raise AssertionError('CB corruption accepted')
        assert fired[0] and t.dead;seq=io.wire_seq
        assert t.P.decryptions==decryptions_at_fault[0] and t.cb_metrics['green_promotions']==green_before
        try:t.transfer(None,0)
        except h.Reject:pass
        else:raise AssertionError('CB retried after fail-stop')
        assert io.wire_seq==seq;failures.append(op)
    exact=local_exact();assert identity()==before
    save(PACKAGE/'results/cb_engine_checks.json',dict(status='passed',runtime_identity=before,cases=cases,active_rejections=failures,
        local_exact=exact,checker_sha256=sha(__file__),full_native_AB=False,capacity_certificate=False,
        background_eviction_policy_implemented=False,deadq_implemented=False))
    print(json.dumps(dict(status='passed',cases=len(cases),active_failures=len(failures),local_exact=exact)))


if __name__=='__main__':main()
