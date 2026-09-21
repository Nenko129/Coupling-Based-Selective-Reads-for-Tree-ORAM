"""Raw recursive-map/LLC regression for the separately named CB policy."""
from common import *
import ab_dummy_first_runtime as rt
import ab_paced_frontend as paced
from ab_cb_controller import PressureController
from workloads import make_trace,payload
from audit_ab_cb import bill
from check_ab_cb_frontend import ownership


def main():
    source=rt.identity();engine_path=PACKAGE/'results/ab_dummy_first_checks.json'
    engine=json.loads(engine_path.read_text());assert engine['status']=='passed' and engine['source_hashes']==source
    trace=make_trace(64,128,442,'hot90');truth={a:rt.frontends.initial_payload(a,64) for a in range(64)}
    requests=[];expected=[];cases=[];schedules=[];pressure_seen=False
    for i,(a,v) in enumerate(trace):
        data=None if v is None else payload(a,v,64);requests.append(dict(id=i,address=a,value=data));expected.append((i,truth[a]))
        if data is not None:truth[a]=data
    for kind in ('ring','gc_ring','r0'):
        for bottom in (None,0):
            for pressure in (False,True):
                rt.install(dict(seed=909,R=128,cached_levels=2,Y=4,bottom_dummy=bottom))
                f=paced.PacedGeometryStepwiseFront(kind,N=64,B=64,X=8,plb=3,seed=909,profile=(5,5,7),L=5)
                c=PressureController(f,sets=4,ways=2,high=2 if pressure else None,low=1 if pressure else None);b=f.backend
                initial=b.io.snapshot();bill(initial);b.io.reset_meter();b.tree.logical_calls.reset()
                answers,metrics=c.run_window(requests,8,2048)
                assert [(i,p) for i,p,t in answers]==expected;ownership(f);invoice=b.io.snapshot();bill(invoice)
                useful=b.tree.logical_calls.useful.snapshot();schedules.append(useful)
                pressure_seen|=metrics.get('background_slots',0)>0
                cases.append(dict(kind=kind,bottom_dummy=bottom,pressure=pressure,metrics=metrics,bytes=invoice['total_bytes'],
                    initial_clock=365,final_clock=b.tree.t,max_boundary=b.tree.max_boundary,useful_schedule=useful,
                    answer_sha256=hashlib.sha256(b''.join(p for i,p,t in answers)).hexdigest()))
                assert b.tree.t==365+2048 and b.tree.logical_calls.snapshot()['slots']==sum(c.occupancies.values())==2048
    assert pressure_seen and all(s==schedules[0] for s in schedules)
    assert all(x['answer_sha256']==cases[0]['answer_sha256'] for x in cases) and source==rt.identity()
    save(PACKAGE/'results/ab_dummy_first_frontend_checks.json',dict(status='passed',source_hashes=source,cases=cases,
        engine_checks_sha256=sha(engine_path),checker_sha256=sha(__file__),
        ownership_oracle_sha256=sha(Path(__file__).with_name('check_ab_cb_frontend.py')),
        pressure_exercised=pressure_seen,compressed_map_checked=False,capacity_certificate=False,adaptive_security_proof=False))
    print(json.dumps(dict(status='passed',cases=len(cases),pressure_exercised=pressure_seen)),flush=True)


if __name__=='__main__':main()
