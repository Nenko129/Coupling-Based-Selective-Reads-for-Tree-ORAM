"""Oracle checks for data-local bypass, raw recursion and fixed-clock DWB.

The small Z1 fixture forces local residency; it is deliberately not a paper
performance configuration. Only this checker can inspect server plaintext.
"""
from common import *
import random
import heterogeneous_oram as h
import ir_stash_runtime as rt
from ir_stash_frontend import StashDataFront,identity
from ir_stash_controller import LocalHitController
from audit_frontend_batches import check_bill


def owners(front):
    b=front.backend;p=h.PRF(b.p.key);seen={}
    for (tree,node),item in list(b.io.local_buckets.items())+list(b.server.buckets.items()):
        c=b.c.at(node);pub=item.header[:h.PUBLIC]
        head=h.Header.decode(c,pub,p.decrypt(b.c.context(),b.tree.oid(node),pub,item.header[h.PUBLIC:]))
        for j,d in head.live.items():
            assert d.address not in seen and h.node(d.leaf,h.depth(node),b.c.L)==node
            if b.c.constrained:assert h.depth(node) in h.gc(b.tree.g,d.leaf,b.c.L)
            seen[d.address]=(d.leaf,p.decrypt(b.c.context(),b.tree.oid(node,j),h.ui(head.w),item.slots[j]))
        if h.depth(node)<b.tree.cut:assert head.live==b.tree.index.buckets.get(node,{})
    for a,r in b.tree.stash.items():assert a not in seen;seen[a]=(r.leaf,r.payload)
    for a,e in front.cache.items():assert a not in seen;seen[a]=(e.parked_leaf,e.data)
    assert set(seen)==set(range(front.total))
    for level,count in enumerate(front.counts):
        for i in range(count):
            leaf,payload=seen[front.addr(level,i)]
            if level==len(front.counts)-1:expected=front.top[i]
            else:
                parent_i,j=divmod(i,front.X);data=seen[front.addr(level+1,parent_i)][1]
                expected=int.from_bytes(data[4*j:4*j+4],'big')
            assert leaf==expected,(level,i,leaf,expected)
    assert b.tree._top_root()[0]==b.tree.root
    assert not front.pinned and len(front.cache)<=front.capacity
    return seen


def oracle(front,control,truth):
    seen=owners(front)
    for a in range(front.N):
        line=None if control is None else control.group(a).get(a)
        assert (line.payload if line is not None else seen[a][1])==truth[a]
        if line is not None and not line.dirty:assert line.payload==seen[a][1]


def create(kind,indexed,seed=721):
    rt.install(dict(seed=seed,R=160,cached_levels=6,Z_by_depth=[],index_sets=4,index_ways=2,indexed=indexed))
    f=StashDataFront(kind=kind,N=64,B=64,X=16,plb=4,seed=seed,profile=(1,3,3))
    truth={a:a.to_bytes(8,'big')+bytes(56) for a in range(f.N)}
    return f,truth


def main():
    sources=identity();cases=[]
    engine_path=PACKAGE/'results/ir_stash_engine_checks.json'
    engine=json.loads(engine_path.read_text(encoding='utf-8'))
    assert engine['status']=='passed' and engine['source_hashes']==rt.identity()
    assert engine['checker_sha256']==sha(Path(__file__).parent/'check_ir_stash_engine.py')
    for indexed in (False,True):
        for kind in ('path','deferred','sde'):
            for enabled in (False,True):
                f,truth=create(kind,indexed);b=f.backend;oracle(f,None,truth)
                # Target an observed local data block for functional coverage.
                candidates=[a for a in sorted(b.tree.index.snapshot()) if a<f.N]
                if not candidates:candidates=[a for a in sorted(b.tree.stash) if a<f.N]
                assert candidates,'local-residency fixture';a=candidates[0]
                found=b.tree.find_local(a,leaf=owners(f)[a][0]);assert found is not None
                before_t=b.tree.t;before_seq=f.leaves.seq;before_leaf=owners(f)[a][0]
                before_maps=tuple(f.cache);events=[];new=bytes([93])*64
                for _ in range(10):
                    e=f.step(a,new)
                    events.append({k:(hashlib.sha256(v).hexdigest() if isinstance(v,bytes) else v) for k,v in e.items()})
                    if e['type']=='data':break
                else:raise AssertionError('bounded recursion failed to complete')
                assert e['previous']==truth[a] and e['transfers']==0 and e['local'] in ('F','S')
                if indexed or found[0]=='F':
                    assert b.tree.t==before_t and f.leaves.seq==before_seq and tuple(f.cache)==before_maps
                truth[a]=new;oracle(f,None,truth);assert owners(f)[a][0]==before_leaf
                assert f.metrics['data_remote_remaps']==0
                ctl=LocalHitController(f,sets=2,ways=2,dwb=enabled);rng=random.Random(22)
                expected=[];requests=[];future=dict(truth)
                for i in range(48):
                    addr=rng.randrange(12) if i%4 else rng.randrange(64)
                    value=hashlib.shake_256(b'local-controller'+i.to_bytes(8,'big')).digest(64) if i%3 else None
                    requests.append(dict(id=i,address=addr,value=value));expected.append(future[addr])
                    if value is not None:future[addr]=value
                b.io.reset_meter();start=b.tree.t;seen_answers=0
                for tick in range(48*8):
                    ctl.tick([requests[tick//8]] if tick%8==0 else [])
                    for reqid,prior,clock in ctl.returned[seen_answers:]:
                        assert reqid==seen_answers and prior==expected[reqid]
                        req=requests[reqid]
                        if req['value'] is not None:truth[req['address']]=req['value']
                        seen_answers+=1
                    if tick%24==0:oracle(f,ctl,truth)
                assert seen_answers==48 and not ctl.queue and ctl.work is None
                assert truth==future and b.tree.t-start==ctl.clock==48*8
                m=ctl.metrics
                assert m['foreground_slots']+m['dwb_data_slots']+m['dwb_posmap_slots']+m['dummy_slots']==ctl.clock
                assert m['foreground_slots']==m['foreground_data_slots']+m['foreground_posmap_slots']
                if not enabled:assert not m['dwb_completed']
                oracle(f,ctl,truth);check_bill(b.io.snapshot())
                row=dict(kind=kind,indexed=indexed,dwb=enabled,requests=48,public_slots=ctl.clock,
                    local_probe_events=events,frontend_metrics=dict(f.metrics),controller_metrics=dict(m),
                    billed_bytes=b.io.snapshot()['total_bytes'],not_performance_data=True)
                cases.append(row)
                print(json.dumps(dict(kind=kind,indexed=indexed,dwb=enabled,
                    local=m['foreground_local_completions'],dwb_local=m['dwb_local_completions'])),flush=True)
    assert any(x['controller_metrics'].get('foreground_local_completions',0)>0 for x in cases)
    assert any(x['controller_metrics'].get('dwb_local_completions',0)>0 for x in cases)
    faults=[]
    for kind in ('path','deferred','sde'):
        f,truth=create(kind,True);ctl=LocalHitController(f,sets=2,ways=2,dwb=True);hit=[]
        def corrupt(c,op,seq,stage,meta,request,response):
            if not hit and op==h.OPEN_FULL:
                hit.append(True);return response[:-1]+bytes([response[-1]^1])
            return response
        f.backend.io.mutator=corrupt
        try:ctl.tick()
        except h.Reject:pass
        else:raise AssertionError('corrupted idle opening accepted')
        assert hit and ctl.dead and f.dead and f.backend.tree.dead
        wire=f.backend.io.snapshot()['total_bytes']
        try:ctl.tick([dict(id=0,address=0,value=None)])
        except RuntimeError:pass
        else:raise AssertionError('request after controller fail-stop accepted')
        assert f.backend.io.snapshot()['total_bytes']==wire
        faults.append(kind)
    assert sources==identity()
    save(PACKAGE/'results/ir_stash_frontend_checks.json',dict(status='passed',source_hashes=sources,
        checker_sha256=sha(__file__),engine_checks_sha256=sha(engine_path),cases=cases,controller_fault_cases=faults,
        independent_owner_map_and_payload_oracle=True,one_transfer_every_public_slot=True,
        data_local_hit_preserves_leaf=True,full_native_IR=False,all_map_local_bypass=False,
        compressed_map=False,adaptive_security_proof=False,capacity_certificate=False,
        scope='data-local IR-Stash bridge, raw maps and conventional exclusive PLB, fixed-clock LLC/DWB; functional fixture only'))
    print(json.dumps(dict(status='passed',cases=len(cases),faults=len(faults))),flush=True)


if __name__=='__main__':main()
