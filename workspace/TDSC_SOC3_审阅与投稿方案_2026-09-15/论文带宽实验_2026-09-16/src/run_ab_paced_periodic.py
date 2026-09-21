"""Actual-frame AB-CB integration evaluation; scope explicitly excludes DeadQ."""
from common import *
import argparse,dataclasses,time,traceback
from collections import Counter
import ab_cb_runtime as rt
import ab_paced_frontend as bootstrap
from ab_paced_frontend import PacedGeometryStepwiseFront as GeometryStepwiseFront
from ab_cb_controller import PressureController
from workloads import stored_trace,payload
from run_core import progress
from meter import server_storage


def identity():return dict(runtime=rt.identity(),driver=sha(__file__),bootstrap_frontend=sha(bootstrap.__file__))


def run(s):
    started=time.time();source=identity();proofpath=PACKAGE/'results/ab_cb_frontend_checks.json'
    proof=json.loads(proofpath.read_text());assert proof['status']=='passed' and proof['source_hashes']==rt.identity()
    rt.install(dict(seed=s['oram_seed'],R=s['R'],cached_levels=s['cached_levels'],Y=s['Y'],bottom_dummy=s['bottom_dummy']))
    bootstrap.Backend=rt.Backend
    assert s['initialization_stride']==s['profile'][1]
    progress(s,'initializing')
    f=GeometryStepwiseFront(s['kind'],N=s['N'],B=s['B'],X=s['X'],L=s['L'],plb=s['plb'],seed=s['oram_seed'],profile=s['profile'])
    c=PressureController(f,sets=s['llc_sets'],ways=s['llc_ways'],high=s['pressure_high'],low=s['pressure_low']);b=f.backend
    setup=b.io.snapshot();setup_peak=b.tree.max_boundary
    assert b.tree.t==f.total*s['initialization_stride'] and b.tree.births==f.total
    initialization=dict(stride=s['initialization_stride'],initial_clock=b.tree.t,admitted_records=b.tree.births,
        schedule=b.tree.logical_calls.snapshot(),useful_schedule=b.tree.logical_calls.useful.snapshot())
    period=s['period_slots'];assert period==b.c.A*(1<<b.c.L)
    assert s['warmup']*s['slots_per_request']==period
    assert s['requests']*s['slots_per_request']==4*period
    init_t=b.tree.t;pad=(-init_t)%period
    b.io.reset_meter();b.tree.logical_calls.reset();before=Counter(b.tree.cb_metrics);occupancy=Counter(c.occupancies)
    for _ in range(pad):c.tick()
    assert b.tree.t%period==0
    alignment=dict(public_slots=pad,start_t=init_t,end_t=b.tree.t,bill=b.io.snapshot(),schedule=b.tree.logical_calls.snapshot(),
        cb_metrics=dict(Counter(b.tree.cb_metrics)-before),boundary_stash_histogram=dict(Counter(c.occupancies)-occupancy))
    seq,trace=stored_trace(s['N'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    truth={a:rt.frontends.initial_payload(a,s['B']) for a in range(s['N'])};phases={};answers=hashlib.sha256();offset=0
    for phase,part in [('warmup',seq[:s['warmup']]),('measurement',seq[s['warmup']:])]:
        expected=[];requests=[]
        for i,(a,v) in enumerate(part):
            data=None if v is None else payload(a,v,s['B']);requests.append(dict(id=offset+i,address=a,value=data))
            expected.append((offset+i,truth[a]))
            if data is not None:truth[a]=data
        W=len(part)*s['slots_per_request'];start=c.clock;b.io.reset_meter();b.tree.logical_calls.reset()
        before=Counter(b.tree.cb_metrics);occupancy=Counter(c.occupancies)
        progress(s,phase,completed=0,total=W)
        actual,metrics=c.run_window(requests,s['arrival_gap'],W)
        assert [(i,p) for i,p,t in actual]==expected
        for i,p,t in actual:answers.update(p)
        bill=b.io.snapshot();hist=dict(Counter(c.occupancies)-occupancy)
        assert sum(hist.values())==W
        phases[phase]=dict(requests=len(part),public_slots=W,start_clock=start,end_clock=c.clock,
            bills=[bill],total_bytes=bill['total_bytes'],rpc=bill['rpc'],frontend_metrics=metrics,
            cb_metrics=dict(Counter(b.tree.cb_metrics)-before),boundary_stash_histogram=hist,
            schedules=[b.tree.logical_calls.snapshot()],useful_schedule=b.tree.logical_calls.useful.snapshot())
        assert (init_t+start)%period==0 and (init_t+c.clock)%period==0
        offset+=len(part);progress(s,phase,completed=W,total=W)
    assert source==identity()
    m=phases['measurement'];row=dict(status='passed',spec=s,source_hashes=source,frontend_proof_sha256=sha(proofpath),trace=trace,
        configs=[dataclasses.asdict(b.c)],population_including_maps=f.total,leaf_load=f.total/(1<<b.c.L),
        setup=setup,setup_peak_boundary_stash=setup_peak,alignment=alignment,initialization=initialization,
        periodic_extension=dict(period_slots=period,warmup_complete_periods=1,measurement_complete_periods=4,no_steady_state_claim=True),
        phases=phases,bytes_per_request=m['total_bytes']/s['requests'],
        bytes_per_public_slot=m['total_bytes']/m['public_slots'],rpc_per_request=m['rpc']/s['requests'],
        server_storage=server_storage(b.server),cache_representation=b.io.cache_storage(),
        frontend_memory_representation=dict(plb=f.memory_payload_bound(),llc_payload_capacity=s['llc_sets']*s['llc_ways']*s['B'],logical_metadata_not_peak=True),
        final_clock=dict(t=b.tree.t,g=b.tree.g,uid=b.tree.uid),max_boundary_stash=b.tree.max_boundary,
        answer_sha256=answers.hexdigest(),correctness_checked_requests=len(seq),elapsed_seconds=time.time()-started,
        measurement='one aligned period warmup, four periods measurement; same offered application requests and fixed public slots; dirty LLC remains resident',
        scope='authenticated CB + static bottom dummy allocation + prefix cache + raw recursive map + inclusive LLC; pressure slots use ordinary CB dummy reads',
        background_policy='ordinary CB dummy Transfer, which can promote green records; not the native strict-dummy wording',
        native_full_paper_reproduction=False,deadq_implemented=False,capacity_certificate=False,adaptive_security_proof=False,
        latency_claim=False,true_client_peak_measured=False)
    save(PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json",row);progress(s,'passed',elapsed_seconds=row['elapsed_seconds'])
    print(json.dumps(dict(id=s['id'],status='passed',bytes_per_request=row['bytes_per_request'],metrics=m['frontend_metrics'],max_stash=row['max_boundary_stash'])),flush=True)
    return row


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();s=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    try:run(s)
    except Exception:
        save(PACKAGE/'results/failures'/f"{s['id']}.json",dict(status='failed',spec=s,source_hashes=identity(),error=traceback.format_exc()));progress(s,'failed');raise
