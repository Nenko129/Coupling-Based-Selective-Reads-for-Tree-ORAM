"""Encrypted IR-Stash index, local-hit, conflict and authentication checks."""
from common import *
import copy,random
from collections import Counter
import heterogeneous_oram as h
import ir_stash_runtime as rt
from ir_stash import DualIndex
from audit_frontend_batches import check_bill

def inventory(b,truth,leaves):
    p=h.PRF(b.p.key);seen={}
    for (tree,node),item in list(b.io.local_buckets.items())+list(b.server.buckets.items()):
        c=b.c.at(node);pub=item.header[:h.PUBLIC]
        head=h.Header.decode(c,pub,p.decrypt(b.c.context(),b.tree.oid(node),pub,item.header[h.PUBLIC:]))
        for j,d in head.live.items():
            assert d.address not in seen and h.node(d.leaf,h.depth(node),b.c.L)==node
            if b.c.constrained:assert h.depth(node) in h.gc(b.tree.g,d.leaf,b.c.L)
            seen[d.address]=h.Record(d.uid,d.address,d.leaf,p.decrypt(b.c.context(),b.tree.oid(node,j),h.ui(head.w),item.slots[j]))
            if h.depth(node)<b.tree.cut:
                assert b.tree.index.lookup(d.address)==(node,d)
        if h.depth(node)<b.tree.cut:assert head.live==b.tree.index.buckets.get(node,{})
    for a,r in b.tree.stash.items():assert a not in seen;seen[a]=r
    assert set(seen)==set(truth)==set(leaves)
    for a,r in seen.items():assert (r.payload,r.leaf)==(truth[a],leaves[a])
    assert all(len(g)<=b.c.index_ways for g in b.tree.index.sets) or not b.c.indexed
    root,tags=b.tree._top_root();assert root==b.tree.root
    assert len(b.io.cut_roots)==2**b.tree.cut
    assert all(h.depth(n)>=b.tree.cut for _,n in b.server.buckets)
    return seen

def create(kind,indexed,seed=909):
    rt.install(dict(seed=seed,R=128,cached_levels=3,Z_by_depth=[],index_sets=2,index_ways=2,indexed=indexed))
    b=rt.Backend(kind,5,32,B=64,Z=4,A=3,S=3)
    # Deliberately collide leaves to guarantee F/S residency in a small-domain
    # functional fixture. Random light loading need not create any local hits;
    # this fixture is not a sampled workload or bandwidth observation.
    rng=random.Random(seed);leaves={a:0 for a in range(32)}
    truth={a:hashlib.shake_256(b'ir-stash-check'+a.to_bytes(8,'big')).digest(64) for a in leaves}
    for a in range(32):b.tick(None,rng.randrange(32),admit=(a,leaves[a],truth[a]))
    return b,truth,leaves,rng

def main():
    source=rt.identity();cases=[]
    for indexed in (False,True):
        for kind in ('path','deferred','sde'):
            b,truth,leaves,rng=create(kind,indexed);inventory(b,truth,leaves);hits=Counter()
            b.io.reset_meter()
            # Force both local-read and local-write paths before randomized
            # remaps disperse the collision fixture into the remote tree.
            for region in ('F','S'):
                candidates=list(b.tree.stash) if region=='F' else list(b.tree.index.snapshot())
                assert candidates,(kind,indexed,region,'fixture lacks residency')
                a=candidates[0];old=truth[a];new=bytes([31 if region=='F' else 47])*64
                state=b.tree.t,b.tree.g,b.tree.uid;wire=b.io.snapshot()['total_bytes']
                before=inventory(b,truth,leaves)
                old_bill=copy.deepcopy(b.io.snapshot());remote=copy.deepcopy(b.server.buckets)
                if region=='S':
                    node,desc=b.tree.index.lookup(a);stored=copy.deepcopy(b.io.local_buckets[0,node])
                    pub=stored.header[:h.PUBLIC];p=h.PRF(b.p.key)
                    old_head=h.Header.decode(b.c.at(node),pub,p.decrypt(b.c.context(),b.tree.oid(node),pub,stored.header[h.PUBLIC:]))
                if not indexed and region=='S':assert b.local_access(a) is None
                leaf=None if indexed else leaves[a]
                assert b.local_access(a,leaf=leaf)==(old,region)
                if region=='S':assert b.io.local_buckets[0,node]==stored
                assert b.local_access(a,new,leaf=leaf)==(old,region)
                assert b.local_access(a,leaf=leaf)==(new,region)
                truth[a]=new;after=inventory(b,truth,leaves);hits[region]+=3
                assert (b.tree.t,b.tree.g,b.tree.uid)==state and b.io.snapshot()['total_bytes']==wire
                assert b.io.snapshot()==old_bill and b.server.buckets==remote
                if region=='S':
                    fresh=b.io.local_buckets[0,node];pub=fresh.header[:h.PUBLIC]
                    new_head=h.Header.decode(b.c.at(node),pub,p.decrypt(b.c.context(),b.tree.oid(node),pub,fresh.header[h.PUBLIC:]))
                    assert (new_head.gamma,new_head.w,new_head.v)==(old_head.gamma,old_head.w+1,old_head.v+1)
                    assert new_head.count==new_head.used==old_head.count==old_head.used==0
                    assert all(x!=y for x,y in zip(stored.slots,fresh.slots))
                assert {x:(r.uid,r.leaf) for x,r in before.items()}=={x:(r.uid,r.leaf) for x,r in after.items()}
            for i in range(96):
                a=(17*i)%32;value=hashlib.shake_256(b'new'+i.to_bytes(8,'big')).digest(64) if i%2 else None
                before=inventory(b,truth,leaves);t,g,uid=b.tree.t,b.tree.g,b.tree.uid;wire=b.io.snapshot()['total_bytes']
                no_leaf=b.local_access(a,value)
                if no_leaf is None and not indexed:result=b.local_access(a,value,leaf=leaves[a])
                else:result=no_leaf
                if result is not None:
                    prior,where=result;assert prior==truth[a];hits[where]+=1
                    assert (b.tree.t,b.tree.g,b.tree.uid)==(t,g,uid) and b.io.snapshot()['total_bytes']==wire
                    if value is not None:truth[a]=value
                    after=inventory(b,truth,leaves)
                    assert {x:(r.uid,r.leaf) for x,r in before.items()}=={x:(r.uid,r.leaf) for x,r in after.items()}
                else:
                    new=rng.randrange(32)
                    prior=b.tick(a,leaves[a],replace=(new,lambda p:value if value is not None else p))
                    assert prior==truth[a];leaves[a]=new
                    if value is not None:truth[a]=value
                inventory(b,truth,leaves)
                b.tick(None,rng.randrange(32));inventory(b,truth,leaves)
            # Exercise a top write followed by a remote authenticated operation.
            candidates=b.tree.index.snapshot()
            if candidates:
                a=next(iter(candidates));old=truth[a];new=bytes([77])*64
                result=b.local_access(a,new,leaf=None if indexed else leaves[a]);assert result==(old,'S')
                truth[a]=new;inventory(b,truth,leaves)
                leaf=rng.randrange(32);assert b.tick(a,leaves[a],replace=(leaf,lambda p:p))==new;leaves[a]=leaf
                inventory(b,truth,leaves)
            check_bill(b.io.snapshot())
            assert hits['F']>=3 and hits['S']>=3
            if indexed:assert b.tree.local_metrics['placement_set_conflicts']>0
            cases.append(dict(kind=kind,indexed=indexed,hits=dict(hits),metrics=dict(b.tree.local_metrics),
                cache=b.io.cache_storage(),index=b.tree.index_representation(),billed_bytes=b.io.snapshot()['total_bytes']))
            print(json.dumps(dict(kind=kind,indexed=indexed,hits=dict(hits),conflicts=b.tree.local_metrics['placement_set_conflicts'])),flush=True)
    index=DualIndex(2,1);a=0;b=next(x for x in range(1,100) if index.which(x)==index.which(a))
    h1=h.Header(live={0:h.Desc(1,a,0,0)});h2=h.Header(live={0:h.Desc(2,b,0,0)})
    index.replace({1:h1});before=index.snapshot()
    try:index.replace({2:h2})
    except h.Reject:pass
    else:raise AssertionError('conflicting set accepted')
    assert index.snapshot()==before
    # Removing one owner and installing its replacement is an atomic batch.
    index.replace({1:h.Header(),2:h2});assert index.lookup(a) is None and index.lookup(b)==(2,h2.live[0])
    rejections=[]
    for kind in ('path','deferred','sde'):
        for op in (h.OPEN_FULL,h.WRITE):
            b,truth,leaves,rng=create(kind,True);hit=[];decryptions=b.p.decryptions
            prior_index=b.tree.index.snapshot();prior_root=b.tree.root;prior_anchors=dict(b.io.cut_roots)
            def corrupt(c,opcode,seq,stage,meta,request,response):
                if not hit and opcode==op:
                    hit.append(True);return response[:-1]+bytes([response[-1]^1])
                return response
            b.io.mutator=corrupt
            try:b.tick(None,rng.randrange(32))
            except h.Reject:pass
            else:raise AssertionError('remote corruption accepted')
            assert hit and b.tree.dead
            assert b.tree.index.snapshot()==prior_index and b.tree.root==prior_root and b.io.cut_roots==prior_anchors
            if op==h.OPEN_FULL:assert b.p.decryptions==decryptions
            wire=b.io.snapshot()['total_bytes']
            try:b.local_access(0)
            except h.Reject:pass
            else:raise AssertionError('local read after fail-stop')
            assert b.io.snapshot()['total_bytes']==wire
            rejections.append(dict(kind=kind,opcode=op))
    # Trusted-memory corruption is outside the threat model; still verify the
    # added local authentication check rejects before payload/header decrypts.
    b,truth,leaves,rng=create('sde',True);a=next(iter(b.tree.index.snapshot()));node,desc=b.tree.index.lookup(a)
    item=b.io.local_buckets[0,node];item.slots[desc.slot]=bytes([item.slots[desc.slot][0]^1])+item.slots[desc.slot][1:]
    before=b.p.decryptions
    try:b.local_access(a)
    except h.Reject:pass
    else:raise AssertionError('tampered local ciphertext accepted')
    assert b.p.decryptions==before and b.tree.dead
    assert source==rt.identity()
    save(PACKAGE/'results/ir_stash_engine_checks.json',dict(status='passed',source_hashes=source,checker_sha256=sha(__file__),
        cases=cases,remote_rejections=rejections,local_corruption_rejected_before_decrypt=True,set_replacement_atomic=True,
        zero_remote_traffic_for_local_hits=True,local_hits_keep_uid_leaf_t_g=True,
        local_write_preserves_gamma_and_increments_write_versions=True,
        remote_state_unchanged_on_local_read_write=True,index_root_anchors_commit_after_write_ack=True,
        local_payload_extra_copy=False,adaptive_security_proof=False,capacity_certificate=False,
        fixture='deterministic all-zero leaf collision, functional checks only; not a bandwidth workload',
        scope='IR-Stash behavioral encrypted backend; frontend PosMap bypass and full performance integration still pending'))
    print(json.dumps(dict(status='passed',cases=len(cases),remote_rejections=len(rejections))),flush=True)

if __name__=='__main__':main()
