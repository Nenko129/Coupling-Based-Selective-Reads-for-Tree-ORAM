"""Predeclare representative slices and one-factor sensitivities, not a Cartesian product."""
from common import *
from workloads import stored_trace
from run_core import configs_for
from optimized_cost import expected_tree,sum_rows
from optimized_gate import OptimizedBank
from prepare_fair_tuning import object_storage
import dataclasses

CORE_FIELDS=('kind','N','B','profile','map_B','terminal_bytes','compact','fusion','R','warmup','requests','trace_seed','oram_seed','workload')
FRONT_FIELDS=('family','kind','N','B','profile','plb','llc','rho','R','warmup','requests','trace_seed','oram_seed','workload')

def write_plan(name,items,**extra):
    p=PACKAGE/name;assert not p.exists();save(p,dict(items=items,**extra));return p

def main():
    bank=OptimizedBank();corebase=json.loads((PACKAGE/'formal_core_plan.json').read_text())['specs']
    aliases=[];slices=[];models=[]
    for N,B in ((4096,4096),(16384,64),(16384,256),(16384,1024),(16384,4096),(65536,4096)):
        for seed in range(101,106):
            stored_trace(N,6144,seed,'uniform')
            for kind in ('path','deferred','sde','ring','r0'):
                s=dict(id=f'B4_{kind}_N{N}_B{B}_seed{seed}',kind=kind,N=N,B=B,profile=[4,3,3],map_B=512,
                       terminal_bytes=32768,compact=True,fusion=True,R=256,warmup=2048,requests=4096,
                       trace_seed=seed,oram_seed=seed+900,workload='uniform',study='size_slice',experiment_class='formal_slices')
                equivalent=next((x for x in corebase if all(x[k]==s[k] for k in CORE_FIELDS)),None)
                if equivalent:aliases.append(dict(spec=s,folder='formal_core',source_id=equivalent['id']))
                else:slices.append(dict(spec=s,entry='core'))
                if seed==101:
                    cs=configs_for(s);gate=None;error=None
                    try:gate=bank.plan(cs,1<<56)
                    except (ValueError,KeyError) as e:error=str(e)
                    models.append(dict(spec=s,configs=[dataclasses.asdict(c) for c in cs],periodic=sum_rows([expected_tree(c) for c in cs]),
                        serialized_server_bytes=object_storage(cs),selective_gate=gate,gate_gap=error))
    write_plan('formal_slices_plan.json',slices,aliases=aliases,observations=150,source_hashes=source_identity(),
               design='N slice at B4096; B slice at N16384; five paired seeds; no full N by B product')
    save(PACKAGE/'results/slice_periodic_models.json',dict(evidence='model, not measurement',rows=models))
    calibration=[]
    cases=[(k,[4,3,3]) for k in ('path','deferred','sde','ring','gc_ring','r0')]+[(k,[7,6,6]) for k in ('ring','r0')]
    for seed in range(101,106):
        for kind,profile in cases:
            s=dict(id=f'CAL_{kind}_{profile[0]}{profile[1]}_seed{seed}',kind=kind,N=256,B=64,profile=profile,map_B=512,
                   terminal_bytes=32768,compact=True,fusion=True,R=256,trace_seed=seed,oram_seed=seed+900,workload='uniform',
                   study='complete_period_calibration',experiment_class='formal_calibration')
            c=configs_for(s)[0];period=c.A*(1<<c.L)
            s.update(warmup=2*period-(s['N']%period),requests=4*period,period_slots=period)
            stored_trace(s['N'],s['warmup']+s['requests'],seed,'uniform');calibration.append(dict(spec=s,entry='core'))
    write_plan('formal_calibration_plan.json',calibration,design='single tree; align after at least one full period; measure four full periods',
               source_hashes=source_identity(),no_steady_state_claim=True)
    window_audit=json.loads((PACKAGE/'datasets/window_audit.json').read_text());assert window_audit['status']=='passed'
    public=[]
    for w in window_audit['checks']:
        seed=w['seed'];tracepath=PACKAGE/w['prepared_file'];assert sha(tracepath)==w['prepared_sha256']
        for family in ('free_compressed','rho'):
            for kind in ('deferred','sde','ring','r0'):
                s=dict(id=f'PUB_{w["name"]}_{family}_{kind}_seed{seed}',family=family,kind=kind,N=16384,B=64,
                       profile=[4,3,4],plb=8,llc=32,rho=128,R=256,warmup=2048,requests=4096,trace_seed=seed,oram_seed=seed+900,
                       workload=w['name']+'_startkey',trace_file=w['prepared_file'],trace_file_sha256=w['prepared_sha256'],
                       study='public_temporal_locality',experiment_class='formal_public')
                public.append(dict(spec=s,entry='composition'))
    write_plan('formal_public_plan.json',public,source_window_audit_sha256=sha(PACKAGE/'datasets/window_audit.json'),
               statistical_unit='five preselected adjacent window/seed pairs; show paired mean and range, not an iid workload-population CI',
               design='trace locality evaluated where caches matter: Freecursive and rho components; source commands are not split into device blocks')
    sensitivities=[];conditions=[]
    # Exactly one factor changes relative to the existing N4096/B64 controls.
    for plb in (4,32):conditions.append(('free_compressed','hot90',64,dict(plb=plb),f'plb{plb}'))
    conditions.append(('free_compressed','hot90',64,dict(beta=4,X=32),'beta4'))
    for family in ('free_raw','free_compressed'):
        conditions.append((family,'uniform',4096,dict(X=1024 if family=='free_raw' else 2048),'B4096'))
    for llc in (8,128):conditions.append(('rho','hot90',64,dict(llc=llc),f'llc{llc}'))
    for rho in (32,512):conditions.append(('rho','zipf09',64,dict(rho=rho),f'rho{rho}'))
    for n in (1,5):conditions.append(('rho','uniform',64,dict(frame_ratio=n),f'ratio{n}'))
    for family,workload,B,changes,label in conditions:
        for seed in range(101,106):
            stored_trace(4096,6144,seed,workload)
            for kind in ('deferred','sde','ring','r0'):
                s=dict(id=f'SENS_{family}_{label}_{kind}_seed{seed}',family=family,kind=kind,N=4096,B=B,profile=[4,3,4],
                       plb=8,llc=32,rho=128,R=256,warmup=2048,requests=4096,trace_seed=seed,oram_seed=seed+900,
                       workload=workload,study='frontend_sensitivity',condition=label,experiment_class='formal_frontend_sensitivity')
                s.update(changes);sensitivities.append(dict(spec=s,entry='composition'))
    write_plan('formal_frontend_sensitivity_plan.json',sensitivities,conditions=[dict(family=f,workload=w,B=b,changes=c,label=l) for f,w,b,c,l in conditions],
               design='11 one-factor configurations; default controls reused from completed formal_composition/formal_rho_fixed, no Cartesian product',
               block_packing='B4096 raw X1024 versus compressed X2048, beta14; B64 keeps X16/X32',
               source_hashes=source_identity())
    print(json.dumps(dict(size_new=len(slices),size_aliases=len(aliases),calibration=len(calibration),public=len(public),sensitivity=len(sensitivities))))
if __name__=='__main__':main()
