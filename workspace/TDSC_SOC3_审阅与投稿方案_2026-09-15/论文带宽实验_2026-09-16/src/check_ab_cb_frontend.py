"""CB recursive ownership, fixed-slot pressure and compressed-map checks."""
from common import *
from collections import Counter
import ab_cb_runtime as rt
from ab_cb_controller import PressureController,StepwiseFront
from ab_geometry_frontend import GeometryFront,GeometryStepwiseFront
import cb_oram as h
from audit_frontend_batches import check_bill
from workloads import make_trace,payload


def setup(kind,layout,compressed=False,pressure=False):
    rt.install(dict(seed=909,R=128,cached_levels=2,Y=4,bottom_dummy=0 if layout=='bottom_d0' else None))
    if compressed:
        f=GeometryFront(kind,N=64,B=64,X=8,beta=3,compressed=True,plb=3,seed=909,profile=(5,5,7))
        return f
    f=GeometryStepwiseFront(kind,N=64,B=64,X=8,plb=3,seed=909,profile=(5,5,7))
    return PressureController(f,sets=4,ways=2,high=16 if pressure else None,low=12 if pressure else None)


def ownership(f):
    b=f.backend;t=b.tree;c=b.c;seen={r.address for r in t.stash.values()};uids={r.uid for r in t.stash.values()}
    assert len(seen)==len(uids)==len(t.stash)
    for (tree,bucket),stored in list(b.server.buckets.items())+list(b.io.local_buckets.items()):
        if c.rootless and bucket==1:continue
        bc=c.at(bucket);pub=stored.header[:h.PUBLIC]
        head=h.Header.decode(bc,pub,t.P.decrypt(t.ctx,t.oid(bucket),pub,stored.header[h.PUBLIC:]))
        for d in head.live.values():
            assert d.address not in seen and d.uid not in uids;seen.add(d.address);uids.add(d.uid)
    assert not(seen&set(f.cache)) and seen|set(f.cache)==set(range(f.total))
    assert not f.memory_payload_bound()['full_private_posmap_present']
    assert all(h.depth(bucket)>=2 for tree,bucket in b.server.buckets)
    assert all(h.depth(bucket)<2 for tree,bucket in b.io.local_buckets)


def main():
    source=rt.identity();cases=[];schedules={};pressure_seen=False
    trace=make_trace(64,128,442,'hot90');truth={a:rt.frontends.initial_payload(a,64) for a in range(64)}
    requests=[];expected=[]
    for i,(a,v) in enumerate(trace):
        data=None if v is None else payload(a,v,64);requests.append(dict(id=i,address=a,value=data));expected.append((i,truth[a]))
        if data is not None:truth[a]=data
    for kind in ('ring','gc_ring','r0'):
        for layout in ('uniform','bottom_d0'):
            for pressure in (False,True):
                c=setup(kind,layout,pressure=pressure);f=c.front;b=f.backend;b.io.reset_meter();b.tree.logical_calls.reset()
                answers,metrics=c.run_window(requests,8,2048)
                assert [(i,p) for i,p,t in answers]==expected
                bill=b.io.snapshot();check_bill(bill);ownership(f)
                useful=b.tree.logical_calls.useful.snapshot()
                if schedules:assert useful==next(iter(schedules.values()))
                schedules[kind,layout,pressure]=useful
                pressure_seen|=metrics.get('background_slots',0)>0
                assert b.tree.logical_calls.snapshot()['slots']==2048 and sum(c.occupancies.values())==2048
                cases.append(dict(kind=kind,layout=layout,pressure=pressure,metrics=metrics,
                    bytes=bill['total_bytes'],useful_schedule=useful,max_boundary=b.tree.max_boundary))
    assert pressure_seen,'pressure threshold was not exercised'
    compressed=[]
    for kind in ('ring','gc_ring','r0'):
        for layout in ('uniform','bottom_d0'):
            f=setup(kind,layout,compressed=True);b=f.backend;truth={a:rt.frontends.initial_payload(a,64) for a in range(64)}
            b.io.reset_meter()
            for i in range(128):
                a=0 if i%3 else (i*19)%64;data=payload(a,i+1,64)
                assert f.access(a,data)==truth[a];truth[a]=data
            ownership(f);check_bill(b.io.snapshot())
            assert f.metrics['group_resets']>0
            compressed.append(dict(kind=kind,layout=layout,group_resets=f.metrics['group_resets'],
                group_backend_slots=f.metrics['group_backend_slots'],bytes=b.io.snapshot()['total_bytes']))
    geometry_cases=[]
    for kind in ('ring','gc_ring','r0'):
        rt.install(dict(seed=909,R=128,cached_levels=2,Y=4,bottom_dummy=0))
        f=GeometryFront(kind,N=256,B=64,X=16,compressed=False,plb=4,seed=909,profile=(5,5,7),L=7)
        assert f.L==f.backend.c.L==7 and f.total==256+16+1 and f.total>1.5*(1<<f.L)
        for i in range(128):
            a=(i*29)%256;assert f.access(a)==rt.frontends.initial_payload(a,64)
        ownership(f);check_bill(f.backend.io.snapshot())
        geometry_cases.append(dict(kind=kind,L=f.L,population=f.total,leaf_load=f.total/(1<<f.L),max_stash=f.backend.tree.max_boundary))
    active=[]
    for op in (h.READ_SLOTS,h.WRITE):
        c=setup('r0','bottom_d0',pressure=True);b=c.front.backend
        # Force the pressure path without editing the authenticated stash.
        c.high=1;c.low=0;fired=[False]
        def mutate(config,opcode,seq,stage,meta,request,response):
            if not fired[0] and opcode==op:
                fired[0]=True;return response[:-1]+bytes([response[-1]^1])
            return response
        b.io.mutator=mutate
        try:c.tick()
        except (h.Reject,rt.cache.h.Reject):pass
        else:raise AssertionError('background corruption accepted')
        assert fired[0] and c.dead and c.front.dead and b.tree.dead
        before=b.io.wire_seq
        try:c.tick()
        except RuntimeError:pass
        else:raise AssertionError('continued after failure')
        assert b.io.wire_seq==before;active.append(op)
    # A legal full D=0 bucket has no pure dummy before any consumption.
    cfg=rt.TransferConfig(kind='ring',L=2,N=5,B=64,Z=5,A=5,S=4,Y=4,R=128)
    head=h.Header(live={j:h.Desc(j+1,j,0,j) for j in range(5)})
    assert cfg.n==5 and not [j for j in range(cfg.n) if j not in head.live]
    assert source==rt.identity()
    save(PACKAGE/'results/ab_cb_frontend_checks.json',dict(status='passed',source_hashes=source,
        controller_cases=cases,compressed_cases=compressed,geometry_cases=geometry_cases,active_failures=active,strict_dummy_empty_witness=True,
        same_useful_schedule=True,pressure_exercised=True,checker_sha256=sha(__file__),
        scope='recursive maps and fixed-clock pressure using ordinary CB dummy Transfers; no DeadQ or native strict-dummy policy',
        capacity_certificate=False,adaptive_security_proof=False))
    print(json.dumps(dict(status='passed',controller_cases=len(cases),compressed_cases=len(compressed),geometry_cases=len(geometry_cases),active_failures=len(active))))


if __name__=='__main__':main()
