"""Actual encrypted frame experiments; resumable per-run receipts."""
from common import *
import argparse,dataclasses,hashlib,json,math,platform,time,traceback
from collections import Counter
import optimized_oram as ref
from optimized_oram import Config,RecursiveORAM
from optimized_cost import expected_tree,sum_rows
from meter import StreamingTransport,server_storage
from workloads import stored_trace,payload

def geometry(N,A):
    L=1
    while N>A*(1<<(L-1)):L+=1
    return L

def configs_for(spec):
    rows=[];N=spec['N'];B=spec['B'];Z,A,S=spec.get('profile',[4,3,3]);j=0
    while True:
        rows.append(Config(spec['kind'],geometry(N,A),N,B,Z,A,S,spec.get('R',256),j,spec.get('compact',True),spec.get('fusion',True)))
        if N*4<=spec.get('terminal_bytes',32768):break
        B=spec.get('map_B',512);N=(N+B//4-1)//(B//4);j+=1
    return rows

def progress(spec,stage,**fields):
    save(PACKAGE/'results/live'/f"{spec['id']}.json",dict(id=spec['id'],pid=os.getpid(),stage=stage,time=time.time(),**fields))

def run(spec):
    started=time.time();identity=source_identity();cs=configs_for(spec)
    progress(spec,'initializing',configs=[dataclasses.asdict(c) for c in cs])
    ref.Transport=StreamingTransport
    key=hashlib.sha512(b'SOC3-EVAL-KEY'+str(spec['oram_seed']).encode()).digest()
    model=RecursiveORAM(cs,key)
    model.initialize(lambda a:payload(a,0,spec['B']))
    setup=model.io.snapshot();setup_seconds=time.time()-started
    seq,trace=stored_trace(spec['N'],spec['warmup']+spec['requests'],spec['trace_seed'],spec['workload'])
    truth=[0]*spec['N'];answer_hash=hashlib.sha256();phases={};windows=[];max_stash=[0]*len(cs)
    previous_slot=[t.t for t in model.trees]
    for phase,part in [('warmup',seq[:spec['warmup']]),('measurement',seq[spec['warmup']:])]:
        model.io.reset_meter();start=time.time();window_start=0;window_rpc=0;phase_slots=[t.t for t in model.trees]
        for i,(a,v) in enumerate(part):
            value=None if v is None else payload(a,v,spec['B'])
            answer=model.access(a,value)
            assert answer==payload(a,truth[a],spec['B']),('wrong value',a,truth[a],v)
            answer_hash.update(answer)
            if v is not None:truth[a]=v
            for j,t in enumerate(model.trees):max_stash[j]=max(max_stash[j],len(t.stash))
            if (i+1)%128==0 or i+1==len(part):
                s=model.io.snapshot()
                if phase=='measurement':
                    windows.append(dict(through_request=i+1,bytes=s['total_bytes']-window_start,rpc=s['rpc']-window_rpc))
                    window_start=s['total_bytes'];window_rpc=s['rpc']
                progress(spec,phase,completed=i+1,total=len(part),elapsed_seconds=time.time()-start)
        phases[phase]=dict(**model.io.snapshot(),requests=len(part),harness_seconds=time.time()-start,
                           backend_requests=[t.t-n for t,n in zip(model.trees,phase_slots)])
    theory=sum_rows([expected_tree(c) for c in cs])
    measured=phases['measurement']
    record=dict(status='passed',experiment_class=spec.get('experiment_class','pilot'),spec=spec,configs=[dataclasses.asdict(c) for c in cs],
                source_hashes=identity,trace=trace,environment=dict(platform=platform.platform(),python=sys.version,cpu=platform.processor()),
                setup=dict(**setup,harness_seconds=setup_seconds),phases=phases,measurement_windows=windows,
                bytes_per_request=measured['total_bytes']/spec['requests'],rpc_per_request=measured['rpc']/spec['requests'],
                expected_periodic_cost=theory,server_storage=server_storage(model.server),
                terminal_position_map_bytes=4*len(model.terminal_pos),final_stash_blocks=[len(t.stash) for t in model.trees],max_online_boundary_stash=max_stash,
                final_clock=[dict(t=t.t,g=t.g,uid=t.uid) for t in model.trees],correctness_checked_requests=len(seq),
                answer_sha256=answer_hash.hexdigest(),elapsed_seconds=time.time()-started,
                measurement='actual encrypted serialized in-process application frames; excludes TCP/TLS',
                security_admission='pending per-configuration theorem/crypto/lifetime ledger; run success is not a certificate',
                true_client_peak_measured=False,latency_claim=False)
    assert identity==source_identity(),'source changed during run'
    out=PACKAGE/'results'/spec.get('experiment_class','pilot')/f"{spec['id']}.json"
    save(out,record);progress(spec,'passed',receipt=str(out.relative_to(PACKAGE)),elapsed_seconds=record['elapsed_seconds'])
    print(json.dumps(dict(id=spec['id'],status='passed',bytes_per_request=record['bytes_per_request'],seconds=record['elapsed_seconds'])),flush=True)
    return record

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spec',required=True);args=parser.parse_args()
    spec=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    try:run(spec)
    except Exception:
        failure=dict(status='failed',spec=spec,error=traceback.format_exc(),source_hashes=source_identity())
        save(PACKAGE/'results/failures'/f"{spec['id']}.json",failure);progress(spec,'failed',error=failure['error']);raise
if __name__=='__main__':main()
