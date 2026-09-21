"""A complete six-cell pilot at the explicitly declared A5-compatible load."""
from common import *
from run_ab_cb import run,identity


def main():
    specs=[]
    for layout in ('uniform','bottom_d0'):
        for kind in ('ring','gc_ring','r0'):
            specs.append(dict(id=f'pilot_ABCB_{layout}_{kind}',kind=kind,N=512,B=64,L=8,X=16,plb=4,
                llc_sets=8,llc_ways=2,profile=[5,5,7],Y=4,R=500,cached_levels=3,bottom_dummy=0 if layout=='bottom_d0' else None,
                pressure_high=48,pressure_low=32,warmup=64,requests=128,arrival_gap=8,slots_per_request=16,
                trace_seed=901,oram_seed=1901,workload='uniform',experiment_class='pilot_ab_cb'))
    planpath=PACKAGE/'pilot_ab_cb_plan.json';plan=dict(specs=specs,source_hashes=identity(),predeclared_before_pilot=True,
        geometry='547 data+map records / 256 leaves = 2.13671875, below A/2=2.5; not the old 1.5-rate geometry',
        horizon='16 slots per application request with arrival gap 8; same trailing public padding for all cells',
        scope='pipeline pilot only; no formal performance estimate or new security certificate')
    if planpath.exists():assert json.loads(planpath.read_text())==plan
    else:save(planpath,plan)
    rows=[]
    for s in specs:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        r=json.loads(p.read_text()) if p.exists() else run(s)
        assert r['spec']==s and r['source_hashes']==plan['source_hashes'];rows.append(dict(id=s['id'],bytes_per_request=r['bytes_per_request']))
    save(PACKAGE/'results/ab_cb_pilot_completion.json',dict(status='passed',rows=rows,plan_sha256=sha(planpath),source_hashes=identity()))


if __name__=='__main__':main()
