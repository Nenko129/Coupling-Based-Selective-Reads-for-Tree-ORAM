"""Predeclare the paired mechanism matrix, before examining formal outcomes."""
from common import *
from workloads import stored_trace

def main():
    specs=[]
    for seed in range(101,106):
        for workload in ('uniform','hot90'):
            stored_trace(16384,6144,seed,workload)
            for kind in ('path','deferred','sde','ring','gc_ring','r0'):
                specs.append(dict(id=f'B1_{kind}_{workload}_N16384_B4096_seed{seed}',kind=kind,N=16384,B=4096,
                                  profile=[4,3,3],map_B=512,terminal_bytes=32768,compact=True,fusion=True,R=256,
                                  warmup=2048,requests=4096,trace_seed=seed,oram_seed=seed+900,workload=workload,experiment_class='formal_core'))
    result=dict(specs=specs,stage='B1',independent_runs=60,requests_per_run=4096,warmup_per_run=2048,
                parameter_choice='fixed, not selected from measurement outcomes',
                update_from_20260915='common fusion enabled for all Ring variants; unfused versions are retained in B2 factorial ablation',
                paired_effects=[['path','sde'],['deferred','sde'],['ring','gc_ring'],['ring','r0'],['gc_ring','r0']],
                statistical_unit='independent run, same input trace paired across schemes',
                seed_policy='trace seed 101..105, ORAM key seed 1001..1005, independent PRF contexts',
                source_hashes=source_identity())
    save(PACKAGE/'formal_core_plan.json',result)
    print(json.dumps(dict(configurations=12,runs=len(specs),measured_requests=sum(s['requests'] for s in specs))))
if __name__=='__main__':main()
