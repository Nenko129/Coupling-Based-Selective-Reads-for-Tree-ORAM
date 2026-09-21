"""Supplemental encrypted runs with one public maintenance-period tail.

This is a new experiment, not a retry/replacement of the original 75 outcomes.
Both counter widths and all backends execute and pay for the same fixed tail.
"""
from common import *
import argparse,dataclasses,time,traceback
import ir_dwb_runtime as rt
from dwb_compressed_frontend import StagedCompressedFront
from ir_compressed_controller import CompressedController,identity as runtime_identity
from run_ir_compressed_periodic import evidence,delta
from workloads import stored_trace,payload
from frontends import initial_payload
from meter import server_storage
from run_core import progress


def identity():
    return dict(runtime=runtime_identity(),driver=sha(__file__),
        preserved_helpers=sha(Path(__file__).with_name('run_ir_compressed_periodic.py')))


def run_window(c,requests,expected,s,phase,context):
    b=c.front.backend;f=c.front;Q=len(requests);W=Q*s['slots_per_request'];tail=s['tail_periods']*s['period_slots']
    assert not c.queue and c.work is None
    b.io.reset_meter();b.tree.logical_calls.reset();before=c.metrics.copy();map_before=f.metrics.copy()
    start=c.clock;start_t=b.tree.t;start_returned=len(c.returned);reset_start=f.reset_snapshot();clearance=None;verified=0
    answer=hashlib.sha256();prefix=None
    context.update(phase=phase,phase_start_clock=start,phase_start_returned=start_returned,
        phase_requests=Q,requested_slots=W+tail,verified_requests=0,verified_answer_sha256=answer.hexdigest())
    for i in range(W+tail):
        j=i//s['arrival_gap']
        c.tick([requests[j]] if i%s['arrival_gap']==0 and j<Q else [])
        while verified<len(c.returned)-start_returned:
            idx,value,clock=c.returned[start_returned+verified]
            assert (idx,value)==expected[verified],'incorrect completed application answer'
            answer.update(value);verified+=1
        context.update(verified_requests=verified,verified_answer_sha256=answer.hexdigest())
        if verified==Q and clearance is None:clearance=i+1
        if i+1==W:
            prefix=dict(public_slots=W,completed=verified,answer_sha256=answer.hexdigest(),bill=b.io.snapshot(),
                schedule=b.tree.logical_calls.snapshot(),reset=f.reset_snapshot(),queued=len(c.queue),foreground=bool(c.work))
        if (i+1)%4096==0:progress(s,phase,completed=i+1,total=W+tail)
    m=dict(c.metrics-before)
    m.update(unfinished_foreground=int(c.work is not None)+len(c.queue),
        dirty_resident=sum(line.dirty for group in c.sets for line in group.values()),dwb_pending=c.candidate is not None,
        group_reset_pending=f.pending_reset is not None,
        group_reset_slots=sum(m.get(k,0) for k in ('foreground_group_reset_slots','dwb_group_reset_slots','maintenance_reset_slots')))
    invoice=b.io.snapshot()
    row=dict(requests=Q,completed=verified,public_slots=W+tail,active_arrival_window_slots=W,guard_slots=tail,
        bills=[invoice],total_bytes=invoice['total_bytes'],rpc=invoice['rpc'],frontend_metrics=m,map_metrics=delta(f.metrics,map_before),
        reset_start=reset_start,reset_end=f.reset_snapshot(),schedules=[b.tree.logical_calls.snapshot()],
        start_clock=start,end_clock=c.clock,start_t=start_t,end_t=b.tree.t,bytes_per_public_slot=invoice['total_bytes']/(W+tail),
        answer_sha256=answer.hexdigest(),original_cut=prefix,clearance_slot=clearance,
        tail_slots_to_clear=None if clearance is None else max(0,clearance-W),
        guard_bytes=invoice['total_bytes']-prefix['bill']['total_bytes'],guard_rpc=invoice['rpc']-prefix['bill']['rpc'])
    context['completed_phase_observation']=row
    assert verified==Q and m['unfinished_foreground']==0,'guarded fixed horizon did not complete every request'
    return row,[v for idx,v,t in c.returned[start_returned:]]


def execute(s,context):
    started=time.time();source=identity();proofs=evidence()
    assert s['map_mode']=='compressed' and s['kind'] in ('path','deferred','sde') and s['tail_periods']==1
    rt.install(dict(seed=s['oram_seed'],R=s['R'],cached_levels=s['cached_levels'],Z_by_depth=s['Z_by_depth']))
    context['phase']='initializing';progress(s,'initializing')
    f=StagedCompressedFront(s['kind'],N=s['N'],B=s['B'],X=s['X'],beta=s['beta'],plb=s['plb'],seed=s['oram_seed'],profile=s['profile'])
    c=CompressedController(f,sets=s['llc_sets'],ways=s['llc_ways'],dwb=s['dwb']);b=f.backend
    context.update(controller=c,backend=b);setup=b.io.snapshot();period=s['period_slots']
    assert b.tree.t==f.total and period==b.c.A*(1<<b.c.L)
    assert s['warmup']*s['slots_per_request']==period and s['requests']*s['slots_per_request']==4*period
    init_t=b.tree.t;pad=(-init_t)%period;b.io.reset_meter();b.tree.logical_calls.reset();context['phase']='alignment'
    for _ in range(pad):c.tick()
    alignment=dict(public_slots=pad,start_t=init_t,end_t=b.tree.t,bill=b.io.snapshot(),schedule=b.tree.logical_calls.snapshot())
    assert b.tree.t%period==0 and f.pending_reset is None
    seq,trace=stored_trace(s['N'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    truth={a:initial_payload(a,s['B']) for a in range(s['N'])};phases={};answer=hashlib.sha256();offset=0
    for phase,part in [('warmup',seq[:s['warmup']]),('measurement',seq[s['warmup']:])]:
        reqs=[];expected=[]
        for i,(a,v) in enumerate(part):
            value=None if v is None else payload(a,v,s['B'])
            reqs.append(dict(id=offset+i,address=a,value=value));expected.append((offset+i,truth[a]))
            if value is not None:truth[a]=value
        progress(s,phase,completed=0,total=len(part)*s['slots_per_request']+period)
        row,values=run_window(c,reqs,expected,s,phase,context);phases[phase]=row
        for value in values:answer.update(value)
        offset+=len(part);context.pop('completed_phase_observation',None)
    assert source==identity() and proofs==evidence();m=phases['measurement']
    row=dict(status='passed',spec=s,source_hashes=source,proof_hashes=proofs,trace=trace,configs=[dataclasses.asdict(b.c)],
        setup=setup,alignment=alignment,phases=phases,bytes_per_request=m['total_bytes']/s['requests'],
        rpc_per_request=m['rpc']/s['requests'],bytes_per_public_slot=m['bytes_per_public_slot'],
        server_storage=server_storage(b.server),cache_representation=b.io.cache_storage(),
        frontend_memory_representation=dict(plb=f.memory_payload_bound(),llc_payload_capacity=s['llc_sets']*s['llc_ways']*s['B'],logical_metadata_not_peak=True),
        answer_sha256=answer.hexdigest(),correctness_checked_requests=len(seq),map_counts=f.counts,
        max_online_boundary_stash=b.tree.max_boundary,final_clock=dict(t=b.tree.t,g=b.tree.g,uid=b.tree.uid),
        periodic_extension=dict(period_slots=period,warmup_complete_periods=2,measurement_complete_periods=5,
            public_tail_periods_per_phase=1,no_steady_state_claim=True,path_uses_reference_window=s['kind']=='path'),
        endpoint_policy='all public tail slots billed; dirty LLC and private reset may remain; no adaptive drain or durability barrier',
        original_75_outcomes_replaced=False,native_full_paper_reproduction=False,adaptive_security_proof=False,
        latency_claim=False,true_client_peak_measured=False,elapsed_seconds=time.time()-started)
    out=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json";assert not out.exists();save(out,row)
    progress(s,'passed',elapsed_seconds=row['elapsed_seconds'])
    print(json.dumps(dict(id=s['id'],status='passed',bytes_per_request=row['bytes_per_request'],
        group_reset_slots=m['frontend_metrics']['group_reset_slots'],guard_bytes=m['guard_bytes'])),flush=True)
    return row


def run(s):
    context={}
    try:return execute(s,context)
    except Exception:
        failure=dict(status='failed',spec=s,source_hashes=identity(),error=traceback.format_exc(),phase=context.get('phase'),
            context={k:v for k,v in context.items() if k not in ('controller','backend')})
        if 'backend' in context:
            b=context['backend'];c=context['controller']
            failure.update(partial_bill=b.io.snapshot(),schedule=b.tree.logical_calls.snapshot(),clock=c.clock,t=b.tree.t,
                completed_this_phase=len(c.returned)-context.get('phase_start_returned',0),reset=c.front.reset_snapshot(),
                controller_metrics=dict(c.metrics),map_metrics=dict(c.front.metrics),queued_requests=len(c.queue),foreground_pending=c.work is not None)
        save(PACKAGE/'results/failures'/f"{s['id']}.json",failure);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args()
    run(json.loads(Path(a.spec).read_text(encoding='utf-8')))
