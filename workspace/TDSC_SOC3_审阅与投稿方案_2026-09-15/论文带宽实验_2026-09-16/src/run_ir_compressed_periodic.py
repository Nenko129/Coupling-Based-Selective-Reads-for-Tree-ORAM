"""Period-aligned actual frames for compressed maps, static IR and staged DWB."""
from common import *
import argparse,dataclasses,time,traceback
from collections import Counter
import ir_dwb_runtime as rt
from dwb_compressed_frontend import StagedCompressedFront
from ir_compressed_controller import CompressedController,identity as runtime_identity
from workloads import stored_trace,payload
from frontends import initial_payload
from meter import server_storage
from run_core import progress

def identity():
    return dict(runtime=runtime_identity(),frozen_transfer=sha(COMPOSITION/'transfer_backend.py'),driver=sha(__file__))

def evidence():
    paths=[PACKAGE/'results'/n for n in ('ir_compressed_stage_checks.json','ir_compressed_controller_checks.json')]
    stage,controller=[json.loads(p.read_text()) for p in paths]
    for p,checker in zip((stage,controller),('check_ir_compressed_stages.py','check_ir_compressed_controller.py')):
        assert p['status']=='passed' and p['source_hashes']==runtime_identity()
        assert p['checker_sha256']==sha(Path(__file__).parent/checker)
    assert controller['stage_checks_sha256']==sha(paths[0])
    assert controller['ownership_oracle_sha256']==sha(Path(__file__).with_name('check_ir_compressed_stages.py'))
    return {p.name:sha(p) for p in paths}

def delta(after,before):
    return {k:after.get(k,0)-before.get(k,0) for k in sorted(set(after)|set(before)) if after.get(k,0)!=before.get(k,0)}

def execute(s,context):
    started=time.time();source=identity();proofs=evidence()
    assert s['map_mode']=='compressed' and s['kind'] in ('path','deferred','sde')
    rt.install(dict(seed=s['oram_seed'],R=s['R'],cached_levels=s['cached_levels'],Z_by_depth=s['Z_by_depth']))
    progress(s,'initializing');context['phase']='initializing'
    f=StagedCompressedFront(s['kind'],N=s['N'],B=s['B'],X=s['X'],beta=s['beta'],plb=s['plb'],seed=s['oram_seed'],profile=s['profile'])
    c=CompressedController(f,sets=s['llc_sets'],ways=s['llc_ways'],dwb=s['dwb']);b=f.backend
    context.update(controller=c,backend=b);setup=b.io.snapshot();period=s['period_slots']
    assert b.tree.t==f.total and period==b.c.A*(1<<b.c.L)
    assert s['warmup']*s['slots_per_request']==period and s['requests']*s['slots_per_request']==4*period
    init_t=b.tree.t;pad=(-init_t)%period
    b.io.reset_meter();b.tree.logical_calls.reset();context['phase']='alignment';progress(s,'alignment')
    for _ in range(pad):c.tick()
    alignment=dict(public_slots=pad,start_t=init_t,end_t=b.tree.t,bill=b.io.snapshot(),schedule=b.tree.logical_calls.snapshot())
    assert b.tree.t%period==0 and f.pending_reset is None
    seq,trace=stored_trace(s['N'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    truth={a:initial_payload(a,s['B']) for a in range(s['N'])};phases={};answer=hashlib.sha256();offset=0
    for phase,part in [('warmup',seq[:s['warmup']]),('measurement',seq[s['warmup']:])]:
        reqs=[];expected=[]
        for i,(a,v) in enumerate(part):
            data=None if v is None else payload(a,v,s['B'])
            reqs.append(dict(id=offset+i,address=a,value=data));expected.append((offset+i,truth[a]))
            if data is not None:truth[a]=data
        W=len(part)*s['slots_per_request'];b.io.reset_meter();b.tree.logical_calls.reset()
        start=c.clock;start_t=b.tree.t;before=f.metrics.copy();reset_start=f.reset_snapshot()
        context.update(phase=phase,phase_start_clock=start,phase_start_returned=len(c.returned),phase_requests=len(part),requested_slots=W)
        progress(s,phase,completed=0,total=W)
        actual,metrics=c.run_window(reqs,s['arrival_gap'],W)
        assert [(i,v) for i,v,t in actual]==expected
        for i,v,t in actual:answer.update(v)
        invoice=b.io.snapshot()
        phases[phase]=dict(requests=len(part),public_slots=W,bills=[invoice],total_bytes=invoice['total_bytes'],rpc=invoice['rpc'],
            frontend_metrics=metrics,map_metrics=delta(f.metrics,before),reset_start=reset_start,reset_end=f.reset_snapshot(),
            schedules=[b.tree.logical_calls.snapshot()],start_clock=start,end_clock=c.clock,start_t=start_t,end_t=b.tree.t,
            bytes_per_public_slot=invoice['total_bytes']/W)
        offset+=len(part);progress(s,phase,completed=W,total=W)
    assert source==identity() and proofs==evidence()
    cap=PACKAGE/'numerics/IR43_scaled_L12_c480_m128_audit.json';admission=json.loads(cap.read_text())
    z=s['Z_by_depth'] or [s['profile'][0]]*(b.c.L+1);ref=[4,4,4,4,4,4,2,2,2,3,3,4,4]
    modeled=(b.c.L==12 and b.c.A==3 and b.c.N<=6144 and s['R']>=480 and len(z)==13 and all(x>=y for x,y in zip(z,ref)))
    m=phases['measurement']
    row=dict(status='passed',spec=s,source_hashes=source,proof_hashes=proofs,trace=trace,configs=[dataclasses.asdict(b.c)],
        setup=setup,alignment=alignment,phases=phases,bytes_per_request=m['total_bytes']/s['requests'],
        rpc_per_request=m['rpc']/s['requests'],bytes_per_public_slot=m['bytes_per_public_slot'],
        server_storage=server_storage(b.server),cache_representation=b.io.cache_storage(),
        frontend_memory_representation=dict(plb=f.memory_payload_bound(),llc_payload_capacity=s['llc_sets']*s['llc_ways']*s['B'],logical_metadata_not_peak=True),
        answer_sha256=answer.hexdigest(),correctness_checked_requests=len(seq),map_counts=f.counts,
        max_online_boundary_stash=b.tree.max_boundary,final_clock=dict(t=b.tree.t,g=b.tree.g,uid=b.tree.uid),
        capacity_model_binding=dict(matches_profile_and_population=modeled,population_including_maps=f.total,audit_sha256=sha(cap),
            selective_reference_R=480,lifetime_log2=next(x['lifetime_log2'] for x in admission['tested'] if x['R']==480),
            protocol_closure=False,baseline_theorem_not_supplied=s['kind']!='sde'),
        periodic_extension=dict(period_slots=period,warmup_complete_periods=1,measurement_complete_periods=4,no_steady_state_claim=True,path_uses_reference_window=s['kind']=='path'),
        endpoint_policy='dirty LLC and pending private reset may remain; no unbilled draining or durability barrier',
        scope='static IR allocation, prefix cache, compressed recursive map, inclusive set-LRU LLC and fixed-slot DWB; no IR-Stash/PMMAC',
        native_full_paper_reproduction=False,latency_claim=False,true_client_peak_measured=False,elapsed_seconds=time.time()-started)
    out=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
    save(out,row);progress(s,'passed',elapsed_seconds=row['elapsed_seconds'])
    print(json.dumps(dict(id=s['id'],status='passed',bytes_per_request=row['bytes_per_request'],reset_slots=m['frontend_metrics']['group_reset_slots'])),flush=True)
    return row

def run(s):
    context={}
    try:return execute(s,context)
    except Exception:
        failure=dict(status='failed',spec=s,source_hashes=identity(),error=traceback.format_exc(),
                     phase=context.get('phase'),context={k:v for k,v in context.items() if k not in ('backend','controller')})
        if 'backend' in context:
            b=context['backend'];c=context['controller']
            failure.update(partial_bill=b.io.snapshot(),schedule=b.tree.logical_calls.snapshot(),clock=c.clock,t=b.tree.t,
                completed_this_phase=len(c.returned)-context.get('phase_start_returned',0),reset=c.front.reset_snapshot(),
                controller_metrics=dict(c.metrics),map_metrics=dict(c.front.metrics),
                queued_requests=len(c.queue),foreground_pending=c.work is not None)
        save(PACKAGE/'results/failures'/f"{s['id']}.json",failure);raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    run(json.loads(Path(args.spec).read_text(encoding='utf-8')))

