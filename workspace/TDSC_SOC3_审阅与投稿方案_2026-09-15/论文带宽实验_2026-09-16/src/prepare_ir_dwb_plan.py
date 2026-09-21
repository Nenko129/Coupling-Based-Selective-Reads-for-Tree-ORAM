"""Predeclare representative IR allocation/DWB/Selective factorial comparisons."""
from common import *
from run_ir_dwb import identity
from workloads import stored_trace

def main():
    specs=[]
    for seed in range(101,106):
        for workload in ('uniform','hot90'):
            stored_trace(4096,384,seed,workload)
            for layout in ('uniform','depth'):
                z=[] if layout=='uniform' else [4,4,4,4,4,4,2,2,2,3,3,4,4]
                for enabled in (False,True):
                    for kind in ('path','deferred','sde'):
                        specs.append(dict(id=f'IRDWB_{layout}_{kind}_dwb{int(enabled)}_{workload}_seed{seed}',kind=kind,N=4096,B=64,
                            X=16,profile=[4,3,3],R=480,cached_levels=6,Z_by_depth=z,plb=8,llc_sets=8,llc_ways=2,
                            layout=layout,dwb=enabled,warmup=128,requests=256,arrival_gap=8,slots_per_request=8,
                            trace_seed=seed,oram_seed=seed+900,workload=workload,experiment_class='formal_ir_dwb'))
    out=PACKAGE/'formal_ir_dwb_plan.json';assert not out.exists()
    save(out,dict(specs=specs,source_hashes=identity(),design='2 public capacity profiles x DWB on/off x Path/Deferred/SDE x uniform/hot90 x 5 paired seeds',
        interval='1 request offered every 8 public backend slots; same 2048 measurement slots for 256 requests',
        window='finite prefix after 1024 warmup slots, not steady state or a full bit-reversal period',
        packing='unified population 4369 data+map blocks at L12; same profile/rate numerical envelope as existing IR audit',
        scope='integrated static IR allocation and staged DWB; IR-Stash and compressed maps remain unresolved',
        no_latency_claim=True,predeclared_before_formal_outcomes=True))
    pilot=dict(specs[5],id='pilot_ir_dwb_depth_sde',N=256,X=16,cached_levels=4,Z_by_depth=[4,4,4,4,2,2,3,4,4],
               layout='depth',warmup=32,requests=64,trace_seed=901,oram_seed=1901,experiment_class='pilot_ir_dwb')
    save(PACKAGE/'specs'/f"{pilot['id']}.json",pilot)
    print(json.dumps(dict(specs=len(specs),plan=str(out),pilot=pilot['id'])))

if __name__=='__main__':main()
