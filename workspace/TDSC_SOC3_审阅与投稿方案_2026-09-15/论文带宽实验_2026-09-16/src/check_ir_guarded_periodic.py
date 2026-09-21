"""Small encrypted driver checks, including model and guard-cost corruption."""
from common import *
import copy
from run_ir_guarded_periodic import run,identity,evidence
from audit_ir_guarded_periodic import audit_record,tool_hashes


def main():
    rows=[];records=[]
    for beta in (2,14):
        for kind in ('path','deferred','sde'):
            s=dict(id=f'IRGUARDcheck_beta{beta}_{kind}',kind=kind,N=64,B=64,X=8,beta=beta,profile=[4,3,3],
                R=480,cached_levels=2,Z_by_depth=[4,4,2,2,3,4,4],plb=3,llc_sets=4,llc_ways=2,dwb=True,
                layout='depth',warmup=24,requests=96,arrival_gap=8,slots_per_request=8,period_slots=192,tail_periods=1,
                trace_seed=901,oram_seed=1901,workload='hot90',map_mode='compressed',cohort='guarded_small_gate',experiment_class='check_ir_guarded')
            path=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
            if not path.exists():run(s)
            r=json.loads(path.read_text())
            check=audit_record(r,s);records.append(r)
            rows.append(dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path),audit=check))
    for beta in (2,14):
        rs=[r for r in records if r['spec']['beta']==beta]
        for phase in ('warmup','measurement'):
            for k in ('schedules','frontend_metrics','map_metrics','clearance_slot','reset_start','reset_end'):
                assert all(r['phases'][phase][k]==rs[0]['phases'][phase][k] for r in rs)
    assert all(r['phases']['measurement']['frontend_metrics']['group_reset_slots']>0 for r in records if r['spec']['beta']==2)
    base=records[0];rejected=[]
    def reject(label,edit):
        bad=copy.deepcopy(base);edit(bad)
        try:audit_record(bad,bad['spec'])
        except AssertionError:rejected.append(label)
        else:raise AssertionError('accepted corrupt receipt: '+label)
    reject('omit charged public tail',lambda r:r['phases']['measurement'].__setitem__('guard_bytes',0))
    reject('false cutoff completion',lambda r:r['phases']['measurement']['original_cut'].__setitem__('completed',0))
    reject('wrong partial answer digest',lambda r:r['phases']['warmup']['original_cut'].__setitem__('answer_sha256','0'*64))
    reject('guarded cost divided by wrong request count',lambda r:r.__setitem__('bytes_per_request',r['bytes_per_request']*.8))
    reject('hide reset events',lambda r:r['phases']['measurement']['frontend_metrics'].__setitem__('group_reset_slots',0))
    reject('wrong transfer schedule',lambda r:r['phases']['measurement']['schedules'][0].__setitem__('remove_admit_sha256','0'*64))
    reject('replace original outcomes',lambda r:r.__setitem__('original_75_outcomes_replaced',True))
    save(PACKAGE/'results/ir_guarded_runner_checks.json',dict(status='passed',source_hashes=identity(),proof_hashes=evidence(),
        checker_sha256=sha(__file__),audit_tools=tool_hashes(),cases=rows,rejected_receipts=rejected,
        model_is_diagnostic_only=True,security_admission=False,latency_claim=False))
    print(json.dumps(dict(status='passed',cases=len(rows),rejected=len(rejected))),flush=True)


if __name__=='__main__':main()
