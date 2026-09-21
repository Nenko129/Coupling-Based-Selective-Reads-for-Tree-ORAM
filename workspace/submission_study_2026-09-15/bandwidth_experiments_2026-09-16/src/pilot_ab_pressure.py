"""Predeclare and execute pressure-policy diagnostics, separate from formal runs."""
from common import *
import traceback
from run_ab_cb import run,identity
from audit_ab_cb import inputs,audit_record


def main():
    specs=[]
    for high,low in ((None,None),(24,16)):
        for bottom,layout in ((None,'uniform'),(0,'bottom_d0')):
            for kind in ('ring','gc_ring','r0'):
                label='off' if high is None else str(high)
                specs.append(dict(id=f'pilot_ABPRESS_{layout}_{kind}_H{label}',kind=kind,N=512,B=64,L=8,X=16,plb=4,
                    llc_sets=8,llc_ways=2,profile=[5,5,7],Y=4,R=500,cached_levels=3,bottom_dummy=bottom,
                    pressure_high=high,pressure_low=low,warmup=64,requests=128,arrival_gap=8,slots_per_request=16,
                    trace_seed=901,oram_seed=1901,workload='uniform',experiment_class='pilot_ab_pressure'))
    path=PACKAGE/'pilot_ab_pressure_plan.json';plan=dict(specs=specs,source_hashes=identity(),predeclared_before_pilot=True,
        selection='H24/L16 is a declared stress policy after observing no H48 measurement episodes in the first pilot; not an optimized parameter',
        scope='finite-prefix diagnostic; pressure off versus on, same R500/trace/horizon; no statistical or security admission',
        failure_policy='retain failure and stop; do not extend a failed fixed horizon or silently omit a backend')
    if path.exists():assert json.loads(path.read_text())==plan
    else:save(path,plan)
    _,kwargs=inputs(path.name);receipts=[]
    for s in specs:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        try:
            if not p.exists():run(s)
            # Audit the canonical serialized receipt; the driver's in-memory
            # dataclass representation still contains tuples.
            r=json.loads(p.read_text())
            audit_record(r,s,**kwargs);receipts.append(dict(id=s['id'],sha256=sha(p)))
        except Exception:
            save(PACKAGE/'results/ab_pressure_pilot_failure.json',dict(status='failed',spec=s,error=traceback.format_exc(),completed=receipts));raise
    save(PACKAGE/'results/ab_pressure_pilot_completion.json',dict(status='passed',receipts=receipts,plan_sha256=sha(path),source_hashes=identity()))


if __name__=='__main__':main()
