"""Actual-frame bandwidth for static IR allocation + LLC + staged DWB."""
from common import *
import argparse,dataclasses,time,traceback
import ir_dwb_runtime as rt
from ir_dwb_controller import StepwiseFront,Controller
from workloads import stored_trace,payload
from frontends import initial_payload
from meter import server_storage
from run_core import progress

def identity():
    return dict(runtime=rt.identity(),driver=sha(__file__))

def run(s):
    started=time.time();source=identity();proofpath=PACKAGE/'results/ir_dwb_controller_checks.json'
    proof=json.loads(proofpath.read_text());assert proof['status']=='passed' and proof['runtime_identity']==rt.identity()
    rt.install(dict(seed=s['oram_seed'],R=s['R'],cached_levels=s['cached_levels'],Z_by_depth=s['Z_by_depth']))
    progress(s,'initializing')
    f=StepwiseFront(s['kind'],N=s['N'],B=s['B'],X=s['X'],plb=s['plb'],seed=s['oram_seed'],profile=s['profile'])
    c=Controller(f,sets=s['llc_sets'],ways=s['llc_ways'],dwb=s['dwb']);b=f.backend
    setup=b.io.snapshot()
    period=s['period_slots'];assert period==b.c.A*(1<<b.c.L)
    assert s['warmup']*s['slots_per_request']==period
    assert s['requests']*s['slots_per_request']==4*period
    init_t=b.tree.t;pad=(-init_t)%period
    b.io.reset_meter();b.tree.logical_calls.reset();progress(s,'period_alignment',completed=0,total=pad)
    for _ in range(pad):c.tick()
    assert b.tree.t%period==0
    alignment=dict(public_slots=pad,start_t=init_t,end_t=b.tree.t,bill=b.io.snapshot(),schedule=b.tree.logical_calls.snapshot())
    seq,trace=stored_trace(s['N'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    truth={a:initial_payload(a,s['B']) for a in range(s['N'])};phases={};answer=hashlib.sha256();offset=0
    for phase,part in [('warmup',seq[:s['warmup']]),('measurement',seq[s['warmup']:])]:
        reqs=[];expected=[]
        for i,(a,v) in enumerate(part):
            data=None if v is None else payload(a,v,s['B'])
            reqs.append(dict(id=offset+i,address=a,value=data));expected.append((offset+i,truth[a]))
            if data is not None:truth[a]=data
        slots=s['slots_per_request']*len(part);b.io.reset_meter();b.tree.logical_calls.reset()
        start=c.clock;progress(s,phase,completed=0,total=slots)
        actual,metrics=c.run_window(reqs,s['arrival_gap'],slots)
        assert [(i,v) for i,v,t in actual]==expected
        for i,v,t in actual:answer.update(v)
        bill=b.io.snapshot();phases[phase]=dict(requests=len(part),public_slots=slots,bills=[bill],total_bytes=bill['total_bytes'],rpc=bill['rpc'],
            frontend_metrics=metrics,schedules=[b.tree.logical_calls.snapshot()],start_clock=start,end_clock=c.clock,
            bytes_per_public_slot=bill['total_bytes']/slots)
        assert metrics['application_completed']==len(part) and metrics['public_slots']==slots
        offset+=len(part);progress(s,phase,completed=slots,total=slots)
    assert source==identity()
    admission=json.loads((PACKAGE/'numerics/IR43_scaled_L12_c480_m128_audit.json').read_text())
    z=s['Z_by_depth'] or [s['profile'][0]]*(b.c.L+1)
    ref=[4,4,4,4,4,4,2,2,2,3,3,4,4]
    modeled=(b.c.L==12 and b.c.A==3 and b.c.N<=6144 and s['R']>=480 and len(z)==13 and all(x>=y for x,y in zip(z,ref)))
    assert (b.tree.t-phases['measurement']['public_slots'])%period==0 and b.tree.t%period==0
    m=phases['measurement']
    row=dict(status='passed',spec=s,source_hashes=source,controller_proof_sha256=sha(proofpath),trace=trace,
        configs=[dataclasses.asdict(b.c)],setup=setup,phases=phases,bytes_per_request=m['total_bytes']/s['requests'],
        rpc_per_request=m['rpc']/s['requests'],bytes_per_public_slot=m['bytes_per_public_slot'],
        server_storage=server_storage(b.server),cache_representation=b.io.cache_storage(),
        frontend_memory_representation=dict(plb=f.memory_payload_bound(),llc_payload_capacity=s['llc_sets']*s['llc_ways']*s['B'],
            logical_metadata_not_peak=True),answer_sha256=answer.hexdigest(),correctness_checked_requests=len(seq),
        max_online_boundary_stash=b.tree.max_boundary,final_clock=dict(t=b.tree.t,g=b.tree.g,uid=b.tree.uid),
        initial_data='address as uint64 big-endian followed by zeros, matching the existing Freecursive frontend',
        capacity_model_binding=dict(matches_profile_and_population=modeled,population_including_maps=f.total,
            audit_sha256=sha(PACKAGE/'numerics/IR43_scaled_L12_c480_m128_audit.json'),selective_reference_R=480,
            lifetime_log2=next(x['lifetime_log2'] for x in admission['tested'] if x['R']==480),
            protocol_closure=False,baseline_theorem_not_supplied=s['kind']!='sde'),
        alignment=alignment,periodic_extension=dict(period_slots=period,warmup_complete_periods=1,measurement_complete_periods=4,
            no_steady_state_claim=True,path_uses_reference_window=s['kind']=='path'),
        measurement='actual encrypted frames: one aligned reference period warmup and four measured periods; dirty LLC lines may remain resident',
        scope='static IR-Alloc profile + prefix cache + raw recursive map + inclusive set-LRU LLC + staged DWB; no IR-Stash/PMMAC/native CPU model',
        native_full_paper_reproduction=False,latency_claim=False,true_client_peak_measured=False,elapsed_seconds=time.time()-started)
    save(PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json",row);progress(s,'passed',elapsed_seconds=row['elapsed_seconds'])
    print(json.dumps(dict(id=s['id'],status='passed',bytes_per_request=row['bytes_per_request'],metrics=m['frontend_metrics'])),flush=True)
    return row

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();s=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    try:run(s)
    except Exception:
        save(PACKAGE/'results/failures'/f"{s['id']}.json",dict(status='failed',spec=s,error=traceback.format_exc()));raise
