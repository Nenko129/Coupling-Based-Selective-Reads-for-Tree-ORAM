"""Target-scale public loading followed by all-record reads through the controller."""
from common import *
import traceback
import ab_cb_runtime as rt
import ab_paced_frontend as paced
from ab_cb_controller import PressureController
from audit_ab_cb import bill
from meter import server_storage


def identity():return dict(runtime=rt.identity(),frontend=sha(Path(__file__).parent/'ab_paced_frontend.py'),checker=sha(__file__))


def main():
    source=identity();rows=[]
    specs=[dict(kind=k,bottom_dummy=b,layout=l,N=4096,B=64,L=11,X=16,plb=8,cached_levels=6,R=500,Y=4,
        seed=5101,profile=[5,5,7],high=48,low=32,llc_sets=8,llc_ways=2,Q=4096,gap=8,W=65536)
        for b,l in ((None,'uniform'),(0,'bottom_d0')) for k in ('ring','gc_ring','r0')]
    planpath=PACKAGE/'ab_paced_controlled_check_plan.json';plan=dict(specs=specs,source_hashes=source,
        scope='initialization plus correctness under the specified public slot controller; not performance samples or a stash tail bound',
        all_original_data_records_checked=True,prior_uncontrolled_failure_preserved=True)
    if planpath.exists():assert json.loads(planpath.read_text())==plan
    else:save(planpath,plan)
    for s in specs:
        path=PACKAGE/'results/ab_paced_controlled'/f"{s['layout']}_{s['kind']}.json"
        if path.exists():
            r=json.loads(path.read_text());assert r['status']=='passed' and r['spec']==s and r['source_hashes']==source;rows.append(r);continue
        phase='initializing';initial=None
        try:
            rt.install(dict(seed=s['seed'],R=s['R'],cached_levels=s['cached_levels'],Y=s['Y'],bottom_dummy=s['bottom_dummy']));paced.Backend=rt.Backend
            f=paced.PacedGeometryStepwiseFront(s['kind'],N=s['N'],B=s['B'],X=s['X'],L=s['L'],plb=s['plb'],seed=s['seed'],profile=s['profile']);b=f.backend
            assert f.total==4369 and b.tree.t==f.total*5 and b.tree.births==f.total
            initial=dict(t=b.tree.t,bill=b.io.snapshot(),boundary_stash_peak=b.tree.max_boundary,final_stash=len(b.tree.stash))
            bill(initial['bill']);phase='controlled_all_record_read'
            c=PressureController(f,sets=s['llc_sets'],ways=s['llc_ways'],high=s['high'],low=s['low']);b.io.reset_meter()
            requests=[dict(id=a,address=a,value=None) for a in range(s['Q'])]
            actual,metrics=c.run_window(requests,s['gap'],s['W'])
            assert [(i,p) for i,p,t in actual]==[(a,a.to_bytes(8,'big')+bytes(s['B']-8)) for a in range(s['Q'])]
            validation=b.io.snapshot();bill(validation)
            assert c.clock==s['W'] and b.tree.t==initial['t']+s['W'] and sum(c.occupancies.values())==s['W']
            r=dict(status='passed',spec=s,source_hashes=source,initialization=initial,validation_bill=validation,
                checked_data_records=len(actual),metrics=metrics,boundary_stash_histogram=dict(c.occupancies),
                max_boundary_stash=b.tree.max_boundary,final_t=b.tree.t,server_storage=server_storage(b.server),cache=b.io.cache_storage(),
                capacity_certificate=False,performance_estimate=False)
            save(path,r);rows.append(r)
            save(PACKAGE/'results/ab_paced_controlled_progress.json',dict(status='partial',cases=rows,expected=6,source_hashes=source))
            print(json.dumps(dict(kind=s['kind'],layout=s['layout'],status='passed',initial_peak=initial['boundary_stash_peak'],
                max_stash=b.tree.max_boundary,background_slots=metrics.get('background_slots',0))),flush=True)
        except Exception:
            save(PACKAGE/'results/ab_paced_controlled_failure.json',dict(status='failed',spec=s,phase=phase,initialization=initial,
                error=traceback.format_exc(),source_hashes=source));raise
    assert source==identity()
    save(PACKAGE/'results/ab_paced_controlled_checks.json',dict(status='passed',source_hashes=source,cases=rows,plan_sha256=sha(planpath),
        measured_performance=False,capacity_certificate=False))


if __name__=='__main__':main()
