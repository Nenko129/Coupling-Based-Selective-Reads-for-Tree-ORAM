from common import *
from run_core import geometry
from workloads import stored_trace
import heterogeneous_oram as h
from cached_cost import expected_tree

def main():
    specs=[];models=[];native=[4]*10+[2]*7+[3]*3+[4]*5
    for seed in range(101,106):
        stored_trace(4096,6144,seed,'uniform')
        for B in (64,4096):
            for family in ('IR','AB'):
                profile=[4,3,3] if family=='IR' else [7,6,6];L=geometry(4096,profile[1]);cut=(10*(L+1)+(24 if family=='IR' else 23))//(25 if family=='IR' else 24)
                for variant in ('uniform','depth'):
                    for kind in (('deferred','sde') if family=='IR' else ('ring','r0')):
                        s=dict(id=f'CC_{family}_{variant}_{kind}_N4096_B{B}_seed{seed}',family=family,layout=variant,kind=kind,N=4096,B=B,
                             profile=profile,compact=True,fusion=True,R=256,map_B=512,terminal_bytes=32768,warmup=2048,requests=4096,
                             cached_levels=cut,workload='uniform',trace_seed=seed,oram_seed=seed+900,experiment_class='formal_cached_components')
                        if family=='IR':s['Z_by_depth']=[native[min(24,25*d//(L+1))] for d in range(L+1)] if variant=='depth' else [4]*(L+1)
                        else:s['S_by_depth']=[6]*(L-2)+[4]*3 if variant=='depth' else [6]*(L+1)
                        specs.append(s)
                        if seed==101:
                            c=h.Config(kind,L,4096,B=B,Z=profile[0],A=profile[1],S=profile[2],R=256,Z_by_depth=tuple(s.get('Z_by_depth',[])),S_by_depth=tuple(s.get('S_by_depth',[])))
                            models.append(dict(spec=s,**expected_tree(c,cut)))
    save(PACKAGE/'formal_cached_component_plan.json',dict(specs=specs,runs=len(specs),scope='static-component four-cell comparison with actual tree-top cache',
         native_IR_AB_reproduction=False,source_hashes={n:sha(Path(__file__).parent/n) for n in ('cached_transport.py','cached_cost.py','run_cached_component.py','heterogeneous_oram.py','heterogeneous_fusion.py')}))
    save(PACKAGE/'results/cached_component_models.json',dict(status='periodic_model_not_measurement',rows=models))
    print(json.dumps(dict(runs=len(specs),models=len(models))))
if __name__=='__main__':main()
