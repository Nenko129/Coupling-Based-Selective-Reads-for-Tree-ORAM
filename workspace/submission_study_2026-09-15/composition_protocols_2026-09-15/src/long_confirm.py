"""One-seed longer uniform traces to examine short-warmup sensitivity."""
from pathlib import Path
from collections import Counter
import hashlib,json,time
from frontends import FreecursiveFront,RhoFront,initial_payload
from run_experiments import requests

OUT=Path(__file__).resolve().parents[1]
rows=[]
for family in ['free_compressed','rho']:
    for label,kind in [('Deferred','deferred'),('SDE','sde'),('Ring43','ring'),('R0-43','r0')]:
        N=256;warm=1536;Q=3072
        f=FreecursiveFront(kind,N=N,seed=41) if family=='free_compressed' else RhoFront(kind,N=N,seed=41)
        seq=requests(N,warm+Q,41,'uniform');expected={a:initial_payload(a,64) for a in range(N)}
        def execute(part):
            answers=f.run(part) if family=='rho' else [f.access(a,v) for a,v in part]
            for (a,v),answer in zip(part,answers):
                assert answer==expected[a]
                if v is not None:expected[a]=v
        execute(seq[:warm])
        backends=[f.front,f.back] if family=='rho' else [f.backend]
        starts=[b.checkpoint() for b in backends];slots=[b.tree.t for b in backends]
        # At least one complete scheduled-service period before measurement.
        target=backends[-1];assert target.tree.t>=target.c.A*(1<<target.c.L)
        begin=time.perf_counter();execute(seq[warm:]);elapsed=time.perf_counter()-begin
        bills=[b.stats(s) for b,s in zip(backends,starts)]
        sched=[[(r['remove'],r['admit']) for r in b.tree.logical_calls[k:]] for b,k in zip(backends,slots)]
        rows.append({'family':family,'backend':label,'seed':41,'workload':'uniform','N':N,'B':64,
                     'warmup_requests':warm,'measured_requests':Q,'Z_A_S':[4,3,4],
                     'bytes_per_request':sum(b['total_bytes'] for b in bills)/Q,
                     'rpc_per_request':sum(b['rpc'] for b in bills)/Q,
                     'serialized_bills':bills,'harness_elapsed_seconds':elapsed,
                     'backend_slots_measured':[b.tree.t-k for b,k in zip(backends,slots)],
                     'schedule_sha256':hashlib.sha256(json.dumps(sched).encode()).hexdigest()})
        (OUT/'results/long_trace_rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'completed':len(rows),'family':family,'backend':label}),flush=True)
summary=[]
for family in ['free_compressed','rho']:
    rs=[r for r in rows if r['family']==family];assert len({r['schedule_sha256'] for r in rs})==1
    vals={r['backend']:r['bytes_per_request'] for r in rs}
    summary.append({'family':family,'bytes_per_request':vals,
                    'SDE_vs_Deferred_pct':100*(1-vals['SDE']/vals['Deferred']),
                    'R0_vs_Ring43_pct':100*(1-vals['R0-43']/vals['Ring43'])})
(OUT/'results/long_trace_summary.json').write_text(json.dumps({'scope':'one-seed warmup sensitivity check; not confidence intervals',
          'rows':len(rows),'summary':summary},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary),flush=True)
