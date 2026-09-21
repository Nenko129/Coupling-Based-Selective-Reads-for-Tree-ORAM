"""Check the full revised clock/billing pipeline and retained legacy receipts."""
from common import *
import copy
from run_ab_paced_periodic import run,identity
from audit_ab_cb import audit_record,matched


def main():
    source=identity();proof=sha(PACKAGE/'results/ab_cb_frontend_checks.json');rows=[]
    for bottom,layout in ((None,'uniform'),(0,'bottom_d0')):
        for kind in ('ring','gc_ring','r0'):
            s=dict(id=f'check_ABPACED_{layout}_{kind}',kind=kind,N=64,B=64,L=5,X=8,plb=3,llc_sets=4,llc_ways=2,
                profile=[5,5,7],Y=4,R=128,cached_levels=2,bottom_dummy=bottom,pressure_high=48,pressure_low=32,
                warmup=10,requests=40,arrival_gap=8,slots_per_request=16,period_slots=160,initialization_stride=5,
                trace_seed=701,oram_seed=1701,workload='hot90',experiment_class='ab_paced_periodic_checks')
            p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
            if not p.exists():run(s)
            r=json.loads(p.read_text())
            audit_record(r,s,source,proof,periodic=True,paced=True);rows.append(r)
    for bottom in (None,0):
        group=[r for r in rows if r['spec']['bottom_dummy']==bottom]
        for r in group[1:]:matched(group[0],r,'backend')
    r=rows[-1];rejected=[]
    edits=[('old_initial_clock',lambda x:x['initialization'].__setitem__('initial_clock',73)),
        ('missing_initial_dummy',lambda x:x['initialization']['schedule'].__setitem__('slots',73)),
        ('altered_admission_schedule',lambda x:x['initialization']['useful_schedule'].__setitem__('remove_admit_sha256','0'*64)),
        ('incorrect_alignment',lambda x:x['alignment'].__setitem__('public_slots',0)),
        ('initialization_hidden_from_bill',lambda x:x['setup'].__setitem__('total_bytes',0)),
        ('incorrect_final_clock',lambda x:x['final_clock'].__setitem__('t',1))]
    for label,edit in edits:
        x=copy.deepcopy(r);edit(x)
        try:audit_record(x,r['spec'],source,proof,periodic=True,paced=True)
        except (AssertionError,KeyError):rejected.append(label)
        else:raise AssertionError('damaged paced evidence accepted')
    assert source==identity()
    save(PACKAGE/'results/ab_paced_periodic_checks.json',dict(status='passed',source_hashes=source,positive_cases=len(rows),negative_checks=rejected,
        auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py'),checker_sha256=sha(__file__),
        receipts=[dict(id=r['spec']['id'],sha256=sha(PACKAGE/'results'/r['spec']['experiment_class']/f"{r['spec']['id']}.json")) for r in rows]))
    print(json.dumps(dict(status='passed',positive_cases=len(rows),negative_checks=len(rejected))))


if __name__=='__main__':main()
