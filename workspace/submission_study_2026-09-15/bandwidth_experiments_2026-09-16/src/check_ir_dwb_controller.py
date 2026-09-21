"""Audit the integrated depth-cache/Transfer/LLC/DWB slot controller."""
from common import *
from collections import Counter
import ir_dwb_runtime as rt
import heterogeneous_oram as h
from ir_dwb_controller import StepwiseFront,Controller,Line
from audit_frontend_batches import check_bill
from frontends import initial_payload
from workloads import make_trace,payload

def create(kind,layout='depth',dwb=True):
    profile=[4,4,2,2,3,4,4] if layout=='depth' else []
    rt.install(dict(seed=55,R=480,cached_levels=2,Z_by_depth=profile))
    front=StepwiseFront(kind,N=64,B=64,X=8,plb=3,seed=31,profile=(4,3,4))
    return Controller(front,sets=4,ways=2,dwb=dwb)

def owners(front):
    backend=front.backend;c=backend.c;t=backend.tree
    counts=Counter(list(t.stash))
    for (tree,b),st in list(backend.server.buckets.items())+list(backend.io.local_buckets.items()):
        if c.rootless and b==1:continue
        bc=c.at(b);pub=st.header[:h.PUBLIC]
        header=h.Header.decode(bc,pub,t.P.decrypt(t.ctx,t.oid(b),pub,st.header[h.PUBLIC:]))
        counts.update(d.address for d in header.live.values())
    assert all(v==1 for v in counts.values())
    assert not(set(counts)&set(front.cache)) and set(counts)|set(front.cache)==set(range(front.total))
    assert all(h.depth(b)>=2 for tree,b in backend.server.buckets)
    assert all(h.depth(b)<2 for tree,b in backend.io.local_buckets)

def main():
    results=[];schedules={}
    trace=make_trace(64,96,333,'uniform')
    requests=[dict(id=i,address=a,value=None if v is None else payload(a,v,64)) for i,(a,v) in enumerate(trace)]
    truth={a:initial_payload(a,64) for a in range(64)};expected=[]
    for r in requests:
        expected.append((r['id'],truth[r['address']]))
        if r['value'] is not None:truth[r['address']]=r['value']
    for layout in ('uniform','depth'):
        for enabled in (False,True):
            for kind in ('path','deferred','sde','ring','gc_ring','r0'):
                c=create(kind,layout,enabled);b=c.front.backend;b.io.reset_meter();b.tree.logical_calls.reset()
                answers,metrics=c.run_window(requests,4,768)
                assert [(i,v) for i,v,t in answers]==expected
                assert metrics['public_slots']==768
                assert metrics.get('foreground_slots',0)+metrics.get('dwb_posmap_slots',0)+metrics.get('dwb_data_slots',0)+metrics.get('dummy_slots',0)==768
                bill=b.io.snapshot();check_bill(bill);schedule=b.tree.logical_calls.snapshot()
                key=enabled
                if key in schedules:assert schedules[key]==(schedule,metrics)
                else:schedules[key]=(schedule,metrics)
                owners(c.front)
                results.append(dict(layout=layout,dwb=enabled,kind=kind,metrics=metrics,bytes=bill['total_bytes'],slots=768,answer_checked=True,ownership_checked=True))
    # An unfinished DWB must survive intervening foreground eviction of a map
    # block: every slot retraverses current mappings, not stale generator locals.
    c=create('sde');f=c.front
    c.sets[0][0]=Line(0,payload(0,777,64),dirty=True)
    c.tick();assert c.metrics['dwb_posmap_slots']==1 and c.candidate is not None
    for i,a in enumerate((1,9,17,25,33,41,49,57)):
        c.tick([dict(id=i,address=a,value=None)])
    while c.work is not None or c.queue:c.tick()
    assert c.candidate is not None
    before=c.metrics['dwb_completed']
    for _ in range(8):
        c.tick()
        if c.metrics['dwb_completed']>before:break
    assert not c.sets[0][0].dirty and c.metrics['dwb_completed']==before+1
    assert f.access(0)==payload(0,777,64)
    owners(f)
    active=[]
    for kind,op in [('sde',h.OPEN_FULL),('sde',h.WRITE),('r0',h.READ_SLOTS),('r0',h.WRITE)]:
        c=create(kind);f=c.front;c.sets[0][0]=Line(0,payload(0,900,64),dirty=True)
        # Warm maps so that the fault is injected into the final data stage.
        c.tick();c.tick();assert c.metrics['dwb_posmap_slots']==2
        hit=[False]
        def mutate(config,opcode,seq,stage,meta,request,response):
            if not hit[0] and opcode==op and stage=='logical':
                hit[0]=True;return response[:-1]+bytes([response[-1]^1])
            return response
        f.backend.io.mutator=mutate
        try:c.tick()
        except h.Reject:pass
        else:raise AssertionError('tampered DWB committed')
        assert hit[0] and c.dead and f.dead and f.backend.tree.dead and c.sets[0][0].dirty
        size=f.backend.io.snapshot()['total_bytes']
        try:c.tick()
        except RuntimeError:pass
        else:raise AssertionError('controller retried after failure')
        assert f.backend.io.snapshot()['total_bytes']==size
        active.append(dict(kind=kind,opcode=op,dirty_preserved=True,no_retry=True))
    save(PACKAGE/'results/ir_dwb_controller_checks.json',dict(status='passed',cases=results,active=active,
         stale_map_after_foreground_checked=True,runtime_identity=rt.identity(),checker_sha256=sha(__file__),
         scope='static depth allocation and prefix cache plus raw recursive map, inclusive LLC and fixed public slots; not IR-Stash/native timing'))
    print(json.dumps(dict(status='passed',cases=len(results),active_failures=len(active),stale_map_checked=True)))

if __name__=='__main__':main()
