"""Small paired, serialized-byte experiments. Not hardware/network benchmarks."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,random,statistics,time
from frontends import FreecursiveFront,RhoFront,initial_payload

OUT=Path(__file__).resolve().parents[1]
CONFIGS=[('Path','path',(4,3,4)),('Deferred','deferred',(4,3,4)),('SDE','sde',(4,3,4)),
         ('Ring43','ring',(4,3,4)),('GC-Ring43','gc_ring',(4,3,4)),('R0-43','r0',(4,3,4)),
         ('Ring76','ring',(7,6,6)),('R0-76','r0',(7,6,6))]

def requests(N,Q,seed,workload):
    rng=random.Random(1000+seed)
    weights=[1/(a+1)**0.9 for a in range(N)]
    seq=[]
    for t in range(Q):
        a=t%N if workload=='scan' else rng.randrange(N) if workload=='uniform' else rng.choices(range(N),weights,k=1)[0]
        value=(t+10000).to_bytes(8,'big')+bytes(56) if t%5==0 else None
        seq.append((a,value))
    return seq

def run_case(family,label,kind,profile,workload,seed):
    N=256;warm=64;Q=192
    frontend=(RhoFront(kind,N=N,seed=seed,profile=profile) if family=='rho' else
              FreecursiveFront(kind,N=N,compressed=family=='free_compressed',seed=seed,profile=profile))
    seq=requests(N,warm+Q,seed,workload)
    expected={a:initial_payload(a,64) for a in range(N)}
    def execute(part):
        answers=frontend.run(part) if family=='rho' else [frontend.access(a,v) for a,v in part]
        for (a,v),old in zip(part,answers):
            assert old==expected[a],(family,label,workload,seed,a)
            if v is not None:expected[a]=v
    execute(seq[:warm])
    backends=[frontend.front,frontend.back] if family=='rho' else [frontend.backend]
    checkpoints=[b.checkpoint() for b in backends];slots=[b.tree.t for b in backends]
    metrics=Counter(frontend.metrics)
    begin=time.perf_counter();execute(seq[warm:]);seconds=time.perf_counter()-begin
    bills=[b.stats(cp) for b,cp in zip(backends,checkpoints)]
    # Trace schedule equality across backends is compared at aggregation time.
    schedules=[[(r['remove'],r['admit']) for r in b.tree.logical_calls[s:]] for b,s in zip(backends,slots)]
    schedule_hash=hashlib.sha256(json.dumps(schedules).encode()).hexdigest()
    delta=dict(Counter(frontend.metrics)-metrics)
    return {'family':family,'backend':label,'kind':kind,'Z_A_S':profile,'workload':workload,'seed':seed,
            'N_data':N,'B':64,'warmup_requests':warm,'measured_requests':Q,
            'bytes_per_request':sum(b['total_bytes'] for b in bills)/Q,
            'rpc_per_request':sum(b['rpc'] for b in bills)/Q,
            'backend_slots':[b.tree.t-s for b,s in zip(backends,slots)],
            'serialized_bills':bills,'frontend_metrics':delta,'schedule_sha256':schedule_hash,
            'memory_representation_budget':frontend.memory_payload_bound(),
            'harness_elapsed_seconds':seconds,'latency_claim':False,'correctness_checked':True}

def main():
    rows=[];folder=OUT/'results';folder.mkdir(exist_ok=True)
    cache=folder/'experiment_rows.json'
    if cache.exists():rows=json.loads(cache.read_text(encoding='utf-8'))
    done={(r['family'],r['backend'],r['workload'],r['seed']) for r in rows}
    for family in ['free_raw','free_compressed','rho']:
        for workload in ['uniform','zipf','scan']:
            for seed in [0,1,2]:
                for label,kind,profile in CONFIGS:
                    key=(family,label,workload,seed)
                    if key in done:continue
                    row=run_case(family,label,kind,profile,workload,seed);rows.append(row)
                    cache.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
                print(json.dumps({'completed':len(rows),'family':family,'workload':workload,'seed':seed}),flush=True)
    groups=defaultdict(list)
    for r in rows:groups[(r['family'],r['workload'],r['backend'])].append(r)
    means={k:statistics.mean(r['bytes_per_request'] for r in rs) for k,rs in groups.items()}
    aggregate=[]
    for family in ['free_raw','free_compressed','rho']:
        for workload in ['uniform','zipf','scan']:
            rs=[r for r in rows if r['family']==family and r['workload']==workload]
            for seed in [0,1,2]:assert len({r['schedule_sha256'] for r in rs if r['seed']==seed})==1
            values={label:means[(family,workload,label)] for label,_,_ in CONFIGS}
            pct=lambda old,new:100*(1-values[new]/values[old])
            ring=min(['Ring43','Ring76'],key=values.get);r0=min(['R0-43','R0-76'],key=values.get)
            aggregate.append({'family':family,'workload':workload,'mean_bytes_per_request':values,
                              'pure_GC_vs_Deferred_pct':pct('Deferred','SDE'),
                              'SDE_vs_Path_pct':pct('Path','SDE'),
                              'pure_GC_Ring43_pct':pct('Ring43','GC-Ring43'),
                              'R0_vs_Ring43_pct':pct('Ring43','R0-43'),
                              'R0_vs_Ring76_pct':pct('Ring76','R0-76'),
                              'two_profile_tuned_Ring':ring,'two_profile_tuned_R0':r0,
                              'two_profile_tuned_gain_pct':pct(ring,r0)})
    result={'status':'paired research prototypes, small synthetic workloads',
            'rows':len(rows),'profiles_searched':[[4,3,4],[7,6,6]],'global_optimum_claim':False,
            'aggregate':aggregate,'native_full_paper_reproductions':False,
            'all_frontend_schedules_match_across_backends':True,
            'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}}
    (folder/'experiment_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'passed','rows':len(rows)}),flush=True)

if __name__=='__main__':main()
