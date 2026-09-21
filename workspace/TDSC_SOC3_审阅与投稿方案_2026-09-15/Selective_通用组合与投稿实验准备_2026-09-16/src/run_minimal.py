"""Actual encrypted, serialized frames; one independent process per row."""
from minimal_runtime import *
import argparse,time,traceback,platform
from workloads import stored_trace,payload
from meter import server_storage

def run(s):
    source=identity(); c=configuration(s);install(s)
    started=time.time();key=hashlib.sha512(('SELECTIVE-MINIMAL-v1:'+str(s['oram_seed'])+':'+s['arm']).encode()).digest()
    model=h.RecursiveORAM([c],key);model.initialize(lambda a:payload(a,0,c.B))
    setup=model.io.snapshot();seq,trace=stored_trace(c.N,s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    truth=[0]*c.N;answer=hashlib.sha256();phases={};max_stash=0
    for phase,part in [('warmup',seq[:s['warmup']]),('measurement',seq[s['warmup']:])]:
        model.io.reset_meter();wall=time.perf_counter();cpu=time.process_time();start_clock=model.trees[0].t
        for i,(a,v) in enumerate(part):
            old=model.access(a,None if v is None else payload(a,v,c.B))
            assert old==payload(a,truth[a],c.B)
            answer.update(old)
            if v is not None:truth[a]=v
            max_stash=max(max_stash,len(model.trees[0].stash))
            if (i+1)%256==0:save(HOME/'results/live'/f"{s['id']}.json",dict(id=s['id'],phase=phase,completed=i+1,total=len(part)))
        bill=model.io.snapshot();assert sum(bill['components'].values())==bill['total_bytes']
        phases[phase]=dict(bill,requests=len(part),clock_start=start_clock,clock_end=model.trees[0].t,
                          cpu_seconds=time.process_time()-cpu,harness_seconds=time.perf_counter()-wall)
    m=phases['measurement'];period=c.A*(1<<c.L)
    result=dict(status='passed',spec=s,config=dataclasses.asdict(c),effective_flags=dict(selective=c.selective,constrained=c.constrained,root_retained=not c.rootless,compact=c.compact,fused=c.fused),
        source_hashes=source,trace=trace,setup=setup,phases=phases,answer_sha256=answer.hexdigest(),
        bytes_per_request=m['total_bytes']/s['requests'],rpc_per_request=m['rpc']/s['requests'],
        expected_periodic_cost=expected_tree(c,s['cached_levels']),period_slots=period,measurement_full_periods=s['requests']/period,
        cache_representation=model.io.cache_storage(),terminal_position_map_bytes=4*c.N,server_storage=server_storage(model.server),
        max_online_boundary_stash=max_stash,elapsed_seconds=time.time()-started,
        cpu_scope='client + server + correctness oracle in one Python process; not client-only performance',
        true_client_peak_measured=False,network_latency_measured=False,native_paper_reproduction=False,
        security_scope='restricted static-layout adapter; runtime success is not a capacity/security certificate',
        environment=dict(python=sys.version,platform=platform.platform()))
    assert source==identity(),'source changed during run'
    save(HOME/'results'/s['suite']/f"{s['id']}.json",result)
    print(json.dumps(dict(id=s['id'],status='passed',bytes_per_request=result['bytes_per_request'],seconds=result['elapsed_seconds'])),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();s=json.loads(Path(a.spec).read_text(encoding='utf-8'))
    try:run(s)
    except Exception:
        save(HOME/'results/failures'/f"{s['id']}.json",dict(status='failed',spec=s,error=traceback.format_exc()));raise
