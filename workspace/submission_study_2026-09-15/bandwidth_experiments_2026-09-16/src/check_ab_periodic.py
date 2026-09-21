"""End-to-end aligned CB windows and rejecting altered alignment evidence."""
from common import *
import copy
from run_ab_periodic import run,identity
from audit_ab_cb import audit_record,matched


def main():
    source=identity();proof=sha(PACKAGE/'results/ab_cb_frontend_checks.json');rows=[]
    for bottom,layout in ((None,'uniform'),(0,'bottom_d0')):
        for kind in ('ring','gc_ring','r0'):
            s=dict(id=f'check_ABPER_{layout}_{kind}',kind=kind,N=64,B=64,L=5,X=8,plb=3,llc_sets=4,llc_ways=2,
                profile=[5,5,7],Y=4,R=128,cached_levels=2,bottom_dummy=bottom,pressure_high=48,pressure_low=32,
                warmup=10,requests=40,arrival_gap=8,slots_per_request=16,period_slots=160,
                trace_seed=701,oram_seed=1701,workload='hot90',experiment_class='ab_periodic_checks')
            run(s);p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json";r=json.loads(p.read_text())
            audit_record(r,s,source,proof,periodic=True);rows.append(r)
    for bottom in (None,0):
        group=[r for r in rows if r['spec']['bottom_dummy']==bottom]
        for r in group[1:]:matched(group[0],r,'backend')
    r=rows[-1];rejected=[]
    for label,edit in [('alignment_slots',lambda x:x['alignment'].__setitem__('public_slots',0)),
        ('alignment_bill',lambda x:x['alignment']['bill'].__setitem__('total_bytes',0)),
        ('periodic_claim',lambda x:x['periodic_extension'].__setitem__('measurement_complete_periods',5)),
        ('nonaligned_start',lambda x:x['phases']['measurement'].__setitem__('start_clock',1))]:
        x=copy.deepcopy(r);edit(x)
        try:audit_record(x,r['spec'],source,proof,periodic=True)
        except (AssertionError,KeyError):rejected.append(label)
        else:raise AssertionError('damaged alignment accepted')
    assert source==identity()
    save(PACKAGE/'results/ab_periodic_checks.json',dict(status='passed',source_hashes=source,positive_cases=len(rows),negative_checks=rejected,
        auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py'),checker_sha256=sha(__file__),
        receipts=[dict(id=r['spec']['id'],sha256=sha(PACKAGE/'results'/r['spec']['experiment_class']/f"{r['spec']['id']}.json")) for r in rows]))
    print(json.dumps(dict(status='passed',positive_cases=len(rows),negative_checks=len(rejected))))


if __name__=='__main__':main()
