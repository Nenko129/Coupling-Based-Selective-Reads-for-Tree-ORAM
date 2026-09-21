"""Predeclare a conditional CB evaluation before any target-scale measurement."""
from common import *
from run_ab_periodic import identity


def main():
    source=identity();p=PACKAGE/'results/ab_periodic_checks.json';checks=json.loads(p.read_text())
    assert checks['status']=='passed' and checks['source_hashes']==source
    specs=[]
    for seed in range(101,106):
        for workload in ('uniform','hot90'):
            for bottom,layout in ((None,'uniform'),(0,'bottom_d0')):
                for kind in ('ring','gc_ring','r0'):
                    specs.append(dict(id=f'ABPER_{layout}_{kind}_{workload}_seed{seed}',kind=kind,N=4096,B=64,L=11,X=16,plb=8,
                        llc_sets=8,llc_ways=2,profile=[5,5,7],Y=4,R=500,cached_levels=6,bottom_dummy=bottom,
                        pressure_high=48,pressure_low=32,warmup=640,requests=2560,arrival_gap=8,slots_per_request=16,
                        period_slots=10240,trace_seed=seed,oram_seed=seed+5000,workload=workload,experiment_class='ab_periodic'))
    plan=dict(periodic=True,specs=specs,source_hashes=source,runner_checks_sha256=sha(p),
        predeclared_before_measurement=True,initial_repeats=5,
        scope='conditional experimental CB protocol: authenticated recursive raw maps + LLC + prefix cache + static NS + ordinary-CB pressure policy; no DeadQ/security admission',
        geometry='4369 records / 2048 leaves = 2.13330078125; same L11/A5/R500 for all arms',
        horizon='5871 public alignment slots, 10240 warmup slots and 40960 measurement slots; one plus four complete scheduled-maintenance periods',
        parameter_policy='same H48/L32 for every arm; retained first-pilot policy, not selected for maximum saving; H24 diagnostics remain separate',
        repeat_gate='increase entire paired group to n10 if 95% t CI half width exceeds 5 percentage points or run-cost CV exceeds 10%; no direction-based selection',
        failure_policy='stop on any overflow, authentication, fixed-horizon completion or audit failure; retain all evidence and revise explicitly',
        endpoint='same offered Q and public W; inclusive dirty LLC can remain resident; no persistence-barrier or latency claim')
    path=PACKAGE/'ab_periodic_plan.json'
    if path.exists():assert json.loads(path.read_text())==plan
    else:save(path,plan)
    print(json.dumps(dict(planned=len(specs),source_hashes_bound=True,security_admission=False)))


if __name__=='__main__':main()
