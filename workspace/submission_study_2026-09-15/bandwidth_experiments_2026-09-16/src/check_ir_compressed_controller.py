"""Integrated encrypted IR allocation/cache/LLC/compressed-map/DWB checks."""
from common import *
import ir_dwb_runtime as rt
import heterogeneous_oram as h
from dwb_compressed_frontend import StagedCompressedFront,Reject
from ir_compressed_controller import CompressedController,Line,identity
from workloads import make_trace,payload
from frontends import initial_payload
from check_ir_compressed_stages import inventory
from audit_frontend_batches import check_bill


def create(kind,layout='depth',dwb=True,beta=2):
    rt.install(dict(seed=55,R=480,cached_levels=2,Z_by_depth=[4,4,2,2,3,4,4] if layout=='depth' else []))
    front=StagedCompressedFront(kind,N=64,B=64,X=8,beta=beta,plb=3,seed=31,profile=(4,3,4))
    return CompressedController(front,sets=4,ways=2,dwb=dwb)


def main():
    source=identity();proof_path=PACKAGE/'results/ir_compressed_stage_checks.json';proof=json.loads(proof_path.read_text())
    assert proof['status']=='passed' and proof['source_hashes']==source
    trace=make_trace(64,96,333,'uniform');requests=[];truth={a:initial_payload(a,64) for a in range(64)};expected=[]
    for i,(a,v) in enumerate(trace):
        data=None if v is None else payload(a,v,64);requests.append(dict(id=i,address=a,value=data));expected.append((i,truth[a]))
        if data is not None:truth[a]=data
    cases=[];schedules={}
    for layout in ('uniform','depth'):
        for enabled in (False,True):
            for kind in ('path','deferred','sde','ring','gc_ring','r0'):
                c=create(kind,layout,enabled);f=c.front;b=f.backend;b.io.reset_meter();b.tree.logical_calls.reset()
                answers,metrics=c.run_window(requests,8,3072)
                assert [(i,p) for i,p,t in answers]==expected
                assert metrics['group_reset_slots']==f.metrics['group_backend_slots']>0
                assert metrics.get('maintenance_reset_slots',0)>0
                invoice=b.io.snapshot();check_bill(invoice);schedule=b.tree.logical_calls.snapshot()
                assert schedule['slots']==3072 and metrics['application_completed']==96
                if enabled in schedules:assert schedules[enabled]==(schedule,metrics),(layout,kind,enabled)
                else:schedules[enabled]=(schedule,metrics)
                actual=inventory(f);resident={a:line for group in c.sets for a,line in group.items()}
                for a,value in truth.items():
                    if a in resident:
                        assert resident[a].payload==value
                        if not resident[a].dirty:assert actual[a].payload==value
                    else:assert actual[a].payload==value
                cases.append(dict(kind=kind,layout=layout,dwb=enabled,metrics=metrics,bytes=invoice['total_bytes'],
                    rpc=invoice['rpc'],schedule=schedule,reset_snapshot=f.reset_snapshot(),
                    answer_sha256=hashlib.sha256(b''.join(v for i,v,t in answers)).hexdigest()))
                print(json.dumps(dict(kind=kind,layout=layout,dwb=enabled,reset_slots=metrics['group_reset_slots'])),flush=True)
    # During a partially completed DWB group reset, a foreground LLC hit changes
    # the dirty value. Cancel only that writeback intent, retain/reset its group,
    # then commit the newest value through a newly selected candidate.
    c=create('sde',beta=1);f=c.front;f.access(0)
    old=payload(0,777,64);new=payload(0,778,64);c.sets[0][0]=Line(0,old,dirty=True)
    c.tick();assert f.pending_reset is not None and c.candidate is not None
    assert f.pending_reset.cursor==1
    c.tick([dict(id=700,address=0,value=new)])
    assert c.returned[-1][:2]==(700,old) and c.candidate is None and c.sets[0][0].dirty
    assert f.pending_reset is not None and f.pending_reset.cursor==2
    inventory(f)
    for _ in range(32):
        if not c.sets[0][0].dirty:break
        c.tick();inventory(f)
    assert not c.sets[0][0].dirty and f.access(0)==new
    assert c.metrics['dwb_cancelled_candidate_changed']==1 and c.metrics['dwb_completed']==1
    # Queued foreground misses preempt a partially completed reset; maps can be
    # evicted after the mandatory reset ends, and later DWB retraverses them.
    c=create('r0',beta=1);f=c.front;f.access(0);c.sets[0][0]=Line(0,old,dirty=True);c.tick()
    assert f.pending_reset is not None
    reqs=[dict(id=i,address=a,value=None) for i,a in enumerate((1,9,17,25,33,41,49,57))]
    for r in reqs:c.tick([r]);inventory(f)
    for _ in range(512):
        if c.work is None and not c.queue and c.candidate is None and f.pending_reset is None:break
        c.tick()
    assert [(i,p) for i,p,t in c.returned]==[(r['id'],initial_payload(r['address'],64)) for r in reqs]
    assert not c.queue and c.work is None;inventory(f)
    active=[]
    for kind,op in (('sde',h.OPEN_FULL),('sde',h.WRITE),('r0',h.READ_SLOTS),('r0',h.WRITE)):
        c=create(kind,beta=1);f=c.front;f.access(0);c.sets[0][0]=Line(0,old,dirty=True)
        for _ in range(8):c.tick()
        assert f.pending_reset is None and c.candidate is not None and c.sets[0][0].dirty
        hit=[]
        def mutate(config,opcode,seq,stage,meta,request,response):
            if not hit and opcode==op and stage=='logical':
                hit.append(True);return response[:-1]+bytes([response[-1]^1])
            return response
        f.backend.io.mutator=mutate
        try:c.tick()
        except (Reject,h.Reject):pass
        else:raise AssertionError('compressed DWB controller accepted corruption')
        assert hit and c.dead and f.dead and f.backend.tree.dead and c.sets[0][0].dirty
        before=f.backend.io.snapshot()['total_bytes']
        try:c.tick()
        except RuntimeError:pass
        else:raise AssertionError('compressed controller continued after failure')
        assert f.backend.io.snapshot()['total_bytes']==before;active.append(dict(kind=kind,opcode=op))
    assert source==identity()
    save(PACKAGE/'results/ir_compressed_controller_checks.json',dict(status='passed',source_hashes=source,cases=cases,
        stage_checks_sha256=sha(proof_path),checker_sha256=sha(__file__),ownership_oracle_sha256=sha(Path(__file__).with_name('check_ir_compressed_stages.py')),
        active_rejections=active,version_change_mid_reset=True,foreground_map_eviction_after_reset=True,
        same_public_and_useful_schedules=True,capacity_certificate=False,adaptive_security_proof=False,
        scope='raw data with compressed recursive map, static depth allocation, real prefix cache, inclusive LLC and fixed-slot DWB; no IR-Stash'))
    print(json.dumps(dict(status='passed',cases=len(cases),active_rejections=len(active))),flush=True)


if __name__=='__main__':main()
