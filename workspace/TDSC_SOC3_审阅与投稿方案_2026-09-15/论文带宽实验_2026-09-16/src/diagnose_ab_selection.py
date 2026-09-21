"""Retain incomplete fixed horizons and compare two explicit CB policies.

No run is retried or promoted to a performance sample. Same N/L/R, leaf seed,
loading cadence, offered requests, pressure thresholds, and public slots.
"""
from common import *
import traceback
from collections import Counter
import ab_cb_runtime as original
import ab_dummy_first_runtime as revised
import ab_paced_frontend as paced
from ab_cb_controller import PressureController
from audit_ab_cb import bill


def main():
    shared=dict(N=4096,B=64,L=11,X=16,plb=8,cached_levels=6,R=500,Y=4,seed=5101,
        profile=[5,5,7],high=48,low=32,llc_sets=8,llc_ways=2,Q=4096,gap=8,W=65536,bottom_dummy=0,kind='ring')
    specs=[dict(shared,policy=p) for p in ('uniform_unused','dummy_first')]
    sources=dict(original=original.identity(),revised=revised.identity(),checker=sha(__file__))
    plan=dict(specs=specs,source_hashes=sources,performance_sample=False,prior_failure_preserved=True)
    path=PACKAGE/'ab_selection_diagnostic_plan.json'
    if path.exists():assert json.loads(path.read_text())==plan
    else:save(path,plan)
    rows=[]
    for s in specs:
        target=PACKAGE/'results/ab_selection_diagnostic'/f"{s['policy']}.json"
        if target.exists():
            r=json.loads(target.read_text());assert r['spec']==s and r['source_hashes']==sources;rows.append(r);continue
        rt=original if s['policy']=='uniform_unused' else revised
        rt.install(dict(seed=s['seed'],R=s['R'],cached_levels=s['cached_levels'],Y=s['Y'],bottom_dummy=s['bottom_dummy']))
        paced.Backend=rt.Backend
        f=paced.PacedGeometryStepwiseFront(s['kind'],N=s['N'],B=s['B'],X=s['X'],L=s['L'],plb=s['plb'],seed=s['seed'],profile=s['profile'])
        b=f.backend;initial=dict(t=b.tree.t,stash=len(b.tree.stash),peak=b.tree.max_boundary,bill=b.io.snapshot());bill(initial['bill'])
        c=PressureController(f,sets=s['llc_sets'],ways=s['llc_ways'],high=s['high'],low=s['low'])
        b.io.reset_meter();b.tree.logical_calls.reset();snapshots=[];error=None
        try:
            for i in range(s['W']):
                a=i//s['gap'];arrivals=[dict(id=a,address=a,value=None)] if i%s['gap']==0 and a<s['Q'] else []
                c.tick(arrivals)
                if (i+1)%8192==0:
                    snap=dict(clock=c.clock,completed=len(c.returned),queued=len(c.queue),stash=len(b.tree.stash),
                        background_slots=c.metrics.get('background_slots',0),draining=c.draining)
                    snapshots.append(snap);print(json.dumps(dict(policy=s['policy'],**snap)),flush=True)
                    save(PACKAGE/'results/ab_selection_diagnostic_progress.json',dict(policy=s['policy'],spec=s,snapshots=snapshots))
        except Exception:error=traceback.format_exc()
        actual=[(i,p) for i,p,t in c.returned]
        assert actual==[(a,a.to_bytes(8,'big')+bytes(s['B']-8)) for a in range(len(actual))]
        invoice=b.io.snapshot();bill(invoice)
        complete=len(actual)==s['Q'] and not c.queue and c.work is None and error is None
        r=dict(status='completed' if complete else 'execution_failed' if error else 'incomplete_horizon',spec=s,source_hashes=sources,
            initialization=initial,validation_bill=invoice,checked_answers=len(actual),queued=len(c.queue),work_pending=c.work is not None,
            clock=c.clock,final_t=b.tree.t,final_stash=len(b.tree.stash),max_boundary_stash=b.tree.max_boundary,
            metrics=dict(c.metrics),boundary_stash_histogram=dict(c.occupancies),snapshots=snapshots,
            schedule=b.tree.logical_calls.snapshot(),error=error,performance_sample=False,capacity_certificate=False)
        save(target,r);rows.append(r)
        print(json.dumps(dict(policy=s['policy'],status=r['status'],answers=len(actual),max_stash=b.tree.max_boundary)),flush=True)
    assert sources==dict(original=original.identity(),revised=revised.identity(),checker=sha(__file__))
    save(PACKAGE/'results/ab_selection_diagnostic.json',dict(status='diagnostic_completed',cases=rows,plan_sha256=sha(path)))


if __name__=='__main__':main()
