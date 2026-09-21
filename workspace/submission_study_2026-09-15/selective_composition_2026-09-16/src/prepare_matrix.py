"""Predeclared minimal suite; no combinations across all literature baselines."""
from minimal_runtime import *

def component(family,arm,layout,B,seed,pilot=False):
    N=128 if pilot else 4096;L=geometry(N,3);period=3*(1<<L)
    s=dict(family=family,arm=arm,layout=layout,N=N,B=B,profile=[4,3,3],R=480 if family=='IR' else 256,
           compact=False,fusion=False,root_retained=True,cached_levels=2 if pilot else 6,terminal_bytes=32768,
           warmup=period,requests=period if pilot else 2*period,workload='uniform',trace_seed=seed,oram_seed=seed+900,
           suite='pilot' if pilot else 'formal',driver='run_minimal.py')
    if family=='IR':s['Z_by_depth']=([4,4,2,2,3,3,4,4] if pilot else [4,4,4,4,4,4,2,2,2,3,3,4,4]) if layout=='depth' else [4]*(L+1)
    else:s['S_by_depth']=([3,3,2,2,2,3,4,4] if pilot else [3,3,3,3,3,3,2,2,2,3,4,4,4]) if layout=='depth' else [3]*(L+1)
    s['id']=f"MIN_{s['suite']}_{family}_{layout}_{arm}_B{B}_seed{seed}";return s

def frontend(family,kind,B,seed,pilot=False):
    s=dict(family=family,arm='selective' if kind=='sde' else 'base',kind=kind,layout='host',N=128 if pilot else 4096,B=B,
           profile=[4,3,4],R=256,compact=False,fusion=False,root_retained=True,plb=8,llc=8 if pilot else 32,rho=16 if pilot else 128,
           warmup=128 if pilot else 2048,requests=256 if pilot else 4096,trace_seed=seed,oram_seed=seed+900,workload='uniform',
           suite='pilot' if pilot else 'formal',driver='run_frontend_minimal.py',experiment_class='selective_minimal_frontend_v1')
    s['id']=f"MIN_{s['suite']}_{family}_{kind}_B{B}_seed{seed}";return s

def main():
    pilot=[];formal=[]
    for family in ('IR','AB'):
        for B in (64,4096):
            for arm in ('base','full_probe','selective'):pilot.append(component(family,arm,'depth',B,101,True))
            for seed in range(101,106):
                for arm in ('base','full_probe','selective'):formal.append(component(family,arm,'depth',B,seed))
        for seed in range(101,106):
            for arm in ('base','selective'):formal.append(component(family,arm,'uniform',64,seed))
    for family in ('free_compressed','rho'):
        for kind in ('deferred','sde'):pilot.append(frontend(family,kind,64,101,True))
        for B in (64,4096):
            for seed in range(101,106):
                for kind in ('deferred','sde'):formal.append(frontend(family,kind,B,seed))
    for name,rows in [('pilot',pilot),('formal',formal)]:
        for s in rows:save(HOME/'specs'/name/f"{s['id']}.json",s)
        save(HOME/f'{name}_plan.json',dict(specs=rows,rows=len(rows),
            stopping_rule='5 independent paired seeds; retain all failures; add 5 pairs if paired CI half-width >5 percentage points or either CV >10%',
            scope='minimal interface/static-layout composition, not native complete-paper reproduction',
            resume='existing receipts must match spec AND frozen source hashes'))
    print(json.dumps(dict(pilot=len(pilot),formal=len(formal))))
if __name__=='__main__':main()
