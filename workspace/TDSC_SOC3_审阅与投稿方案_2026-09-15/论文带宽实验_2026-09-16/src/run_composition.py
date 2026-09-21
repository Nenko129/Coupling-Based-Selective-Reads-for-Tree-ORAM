"""Larger paired actual-frame experiments, preserving the restricted contracts."""
from common import *
import argparse,time,dataclasses,traceback
from collections import Counter
import composition_runtime as runtime
from workloads import stored_trace,payload
from meter import server_storage
from run_core import progress

def run(spec):
    source=runtime.identity();started=time.time();runtime.install(spec['oram_seed'],spec.get('R',256))
    ff=runtime.frontends;family=spec['family'];N=spec['N'];B=spec['B'];profile=spec['profile']
    progress(spec,'initializing')
    if family=='rho':
        front=ff.RhoFront(spec['kind'],N=N,B=B,llc=spec['llc'],rho=spec['rho'],n=3,seed=spec['oram_seed'],profile=profile)
        backends=[front.front,front.back]
    else:
        compressed=family=='free_compressed'
        front=ff.FreecursiveFront(spec['kind'],N=N,B=B,compressed=compressed,plb=spec['plb'],seed=spec['oram_seed'],profile=profile)
        backends=[front.backend]
    setup=[b.io.snapshot() for b in backends];setup_seconds=time.time()-started
    seq,trace=stored_trace(N,spec['warmup']+spec['requests'],spec['trace_seed'],spec['workload']);truth=[0]*N
    answer_hash=hashlib.sha256();phases={}
    def execute(part):
        requests=[(a,None if v is None else payload(a,v,B)) for a,v in part]
        answers=front.run(requests) if family=='rho' else [front.access(a,v) for a,v in requests]
        assert len(answers)==len(part)
        for (a,v),old in zip(part,answers):
            expected=ff.initial_payload(a,B) if truth[a]==0 else payload(a,truth[a],B)
            assert old==expected,('wrong composition value',family,a,v)
            answer_hash.update(old)
            if v is not None:truth[a]=v
    for phase,part in [('warmup',seq[:spec['warmup']]),('measurement',seq[spec['warmup']:])]:
        for b in backends:b.io.reset_meter();b.tree.logical_calls.reset()
        metrics=Counter(front.metrics);begin=time.time();progress(spec,phase,completed=0,total=len(part))
        # rho must process one continuous batch: chunking would add public pads.
        execute(part)
        bills=[b.io.snapshot() for b in backends]
        phases[phase]=dict(requests=len(part),bills=bills,total_bytes=sum(b['total_bytes'] for b in bills),rpc=sum(b['rpc'] for b in bills),
                           schedules=[b.tree.logical_calls.snapshot() for b in backends],frontend_metrics=dict(Counter(front.metrics)-metrics),
                           harness_seconds=time.time()-begin)
        progress(spec,phase,completed=len(part),total=len(part))
    memory=front.memory_payload_bound()
    if family=='rho':
        memory['back_stash_reserved_bytes']=front.back.c.R*B
        memory['front_stash_reserved_bytes']=front.front.c.R*B
    result=dict(status='passed',spec=spec,trace=trace,source_hashes=source,setup=setup,setup_seconds=setup_seconds,phases=phases,
         configs=[dataclasses.asdict(b.c) for b in backends],bytes_per_request=phases['measurement']['total_bytes']/spec['requests'],
         rpc_per_request=phases['measurement']['rpc']/spec['requests'],server_storage=[server_storage(b.server) for b in backends],
         final_stash_blocks=[len(b.tree.stash) for b in backends],correctness_checked_requests=len(seq),answer_sha256=answer_hash.hexdigest(),
         frontend_memory_representation=memory,elapsed_seconds=time.time()-started,
         native_full_paper_reproduction=False,latency_claim=False,true_client_peak_measured=False,
         scope=('rho-inspired address-LRU two-tree frontend; full backend flat trusted PosMap; public frame length allowed to leak; no ECC/compact/set-assoc/native async'
                if family=='rho' else 'Freecursive-style unified recursive map tree + address-LRU PLB + group counters; no native PMMAC/hardware controller'))
    assert source==runtime.identity(),'composition runtime changed during run'
    save(PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json",result)
    progress(spec,'passed',elapsed_seconds=result['elapsed_seconds'])
    print(json.dumps(dict(id=spec['id'],status='passed',bytes_per_request=result['bytes_per_request'],seconds=result['elapsed_seconds'])),flush=True)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();spec=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    try:run(spec)
    except Exception:
        save(PACKAGE/'results/failures'/f"{spec['id']}.json",dict(spec=spec,status='failed',error=traceback.format_exc()));progress(spec,'failed');raise
if __name__=='__main__':main()
