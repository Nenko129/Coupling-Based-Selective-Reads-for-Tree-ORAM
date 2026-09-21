"""All-level raw-map ownership, local bypass and serial public-slot checks."""
from common import *
import random
import heterogeneous_oram as h
import ir_stash_runtime as rt
from ir_stash_raw_maps import StashRawMapsFront,LocalMap,identity
from ir_stash_controller import LocalHitController
from check_ir_stash_frontend import owners,oracle
from audit_frontend_batches import check_bill


def create(kind,indexed,deep):
    rt.install(dict(seed=721,R=400,cached_levels=3 if deep else 6,Z_by_depth=[],index_sets=4,index_ways=2,indexed=indexed))
    f=StashRawMapsFront(kind=kind,N=96 if deep else 64,B=64,X=2 if deep else 16,plb=4,seed=721,profile=(1,3,3))
    truth={a:a.to_bytes(8,'big')+bytes(56) for a in range(f.N)}
    return f,truth


def resolve_map(f,level,i):
    g=f._ensure_staged(level,i);events=[]
    try:
        while True:events.append(next(g))
    except StopIteration as done:return done.value,events
    finally:g.close()


def main():
    sources=identity();cases=[]
    prior_path=PACKAGE/'results/ir_stash_frontend_checks.json';prior=json.loads(prior_path.read_text())
    assert prior['status']=='passed' and prior['source_hashes']==sources['data_bridge']
    assert prior['checker_sha256']==sha(Path(__file__).parent/'check_ir_stash_frontend.py')
    local_handle_cases=0
    for deep in (False,True):
        for indexed in (False,True):
            for kind in ('path','deferred','sde'):
                for enabled in (False,True):
                    f,truth=create(kind,indexed,deep);b=f.backend;oracle(f,None,truth)
                    seen=owners(f)
                    maps=[a for a in range(f.N,f.total) if b.tree.find_local(a,leaf=seen[a][0]) is not None]
                    if maps:
                        a=maps[0];level=max(j for j,v in enumerate(f.offsets) if v<=a);i=a-f.offsets[level]
                        t=b.tree.t;old_leaf=seen[a][0];old_seq=f.leaves.seq
                        ref,events=resolve_map(f,level,i)
                        if isinstance(ref,LocalMap):
                            value=ref.data;ref.data=value;assert ref.data==value
                            assert owners(f)[a][0]==old_leaf
                            local_handle_cases+=1
                        if indexed:
                            assert isinstance(ref,LocalMap) and not events and b.tree.t==t and f.leaves.seq==old_seq
                        oracle(f,None,truth)
                    ctl=LocalHitController(f,sets=2,ways=2,dwb=enabled);rng=random.Random(22)
                    expected=[];requests=[];future=dict(truth)
                    for i in range(48):
                        addr=rng.randrange(12) if i%4 else rng.randrange(f.N)
                        value=hashlib.shake_256(b'all-map-controller'+i.to_bytes(8,'big')).digest(64) if i%3 else None
                        requests.append(dict(id=i,address=addr,value=value));expected.append(future[addr])
                        if value is not None:future[addr]=value
                    b.io.reset_meter();start=b.tree.t;seen_answers=0;gap=12 if deep else 8
                    for tick in range(48*gap):
                        ctl.tick([requests[tick//gap]] if tick%gap==0 else [])
                        for reqid,previous,clock in ctl.returned[seen_answers:]:
                            assert reqid==seen_answers and previous==expected[reqid]
                            req=requests[reqid]
                            if req['value'] is not None:truth[req['address']]=req['value']
                            seen_answers+=1
                        if tick%24==0:oracle(f,ctl,truth)
                    assert seen_answers==48 and not ctl.queue and ctl.work is None and truth==future
                    assert b.tree.t-start==ctl.clock==48*gap
                    m=ctl.metrics
                    assert m['foreground_slots']+m['dwb_data_slots']+m['dwb_posmap_slots']+m['dummy_slots']==ctl.clock
                    assert m['foreground_slots']==m['foreground_data_slots']+m['foreground_posmap_slots']
                    assert all(not isinstance(entry,LocalMap) for entry in f.cache.values())
                    oracle(f,ctl,truth);check_bill(b.io.snapshot())
                    local_maps=sum(v for k,v in f.metrics.items() if k.startswith('map_local_'))
                    row=dict(kind=kind,indexed=indexed,dwb=enabled,deep=deep,N=f.N,counts=f.counts,L=f.L,
                        requests=48,slots=ctl.clock,frontend_metrics=dict(f.metrics),controller_metrics=dict(m),
                        local_map_hits=local_maps,not_performance_data=True)
                    cases.append(row)
                    print(json.dumps(dict(kind=kind,indexed=indexed,dwb=enabled,deep=deep,map_hits=local_maps)),flush=True)
    assert local_handle_cases>0 and all(x['local_map_hits']>0 for x in cases)
    # A previously valid borrowed reference cannot access stale placement after
    # the next Transfer. The guard fires before any new I/O or decryptions.
    f,truth=create('sde',True,True);seen=owners(f)
    a=next(a for a in range(f.N,f.total) if f.backend.tree.find_local(a) is not None)
    level=max(j for j,v in enumerate(f.offsets) if v<=a);ref,events=resolve_map(f,level,a-f.offsets[level])
    assert isinstance(ref,LocalMap) and not events
    f.dummy();before=f.backend.io.snapshot();decryptions=f.backend.p.decryptions
    try:ref.data
    except h.Reject:pass
    else:raise AssertionError('stale local map handle accepted')
    assert before==f.backend.io.snapshot() and decryptions==f.backend.p.decryptions
    faults=[]
    for kind in ('path','deferred','sde'):
        for opcode in (h.OPEN_FULL,h.WRITE):
            f,truth=create(kind,True,True);seen=owners(f);b=f.backend
            candidates=[a for a in range(f.N) if b.tree.find_local(a,leaf=seen[a][0]) is None and
                b.tree.find_local(f.addr(1,a//f.X),leaf=seen[f.addr(1,a//f.X)][0]) is None]
            assert candidates,'need remote data + map fixture';a=candidates[0];hits=[]
            def corrupt(c,op,seq,stage,meta,request,response):
                if not hits and op==opcode:
                    hits.append(True);return response[:-1]+bytes([response[-1]^1])
                return response
            b.io.mutator=corrupt
            try:f.step(a)
            except h.Reject:pass
            else:raise AssertionError('remote map fault not caught')
            assert hits and f.dead and b.tree.dead
            before=b.io.snapshot()
            try:f.step(a)
            except h.Reject:pass
            else:raise AssertionError('map operation after failure accepted')
            assert before==b.io.snapshot();faults.append(dict(kind=kind,opcode=opcode))
    assert sources==identity()
    save(PACKAGE/'results/ir_stash_raw_maps_checks.json',dict(status='passed',source_hashes=sources,checker_sha256=sha(__file__),
        data_bridge_checks_sha256=sha(prior_path),oracle_source_sha256=sha(Path(__file__).parent/'check_ir_stash_frontend.py'),
        cases=cases,local_handle_cases=local_handle_cases,remote_map_fault_cases=faults,stale_handle_guard=True,
        all_raw_map_levels=True,compressed_reset=False,full_native_IR=False,adaptive_security_proof=False,
        capacity_certificate=False,scope='all-level raw map local bypass; independent ownership and payload oracle; functional fixture, not bandwidth data'))
    print(json.dumps(dict(status='passed',cases=len(cases),map_faults=len(faults),local_handle_cases=local_handle_cases)),flush=True)


if __name__=='__main__':main()
