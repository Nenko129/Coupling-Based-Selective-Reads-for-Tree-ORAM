"""Predeclare compressed IR main and reset-stress matrices before outcomes."""
from common import *
from run_ir_compressed_periodic import identity,evidence
from audit_ir_compressed import inputs,audit_record

def gates():
    p=PACKAGE/'results/ir_compressed_runner_checks.json';r=json.loads(p.read_text())
    assert r['status']=='passed' and r['source_hashes']==identity() and r['proof_hashes']==evidence()
    assert r['checker_sha256']==sha(Path(__file__).with_name('check_ir_compressed_runner.py'))
    assert r['auditor_sha256']==sha(Path(__file__).with_name('audit_ir_compressed.py'))
    assert len(r['cases'])==6 and len(r['rejected_receipts'])==12
    for x in r['cases']:
        f=PACKAGE/x['path'];assert sha(f)==x['sha256'];row=json.loads(f.read_text());audit_record(row,row['spec'],**inputs())
    f=PACKAGE/r['expected_failure']['path'];assert sha(f)==r['expected_failure']['sha256']
    assert json.loads(f.read_text())['status']=='failed'
    return sha(p)

def main():
    gate=gates();oldpath=PACKAGE/'formal_ir_periodic_plan.json';old=json.loads(oldpath.read_text());specs=[]
    for s in old['specs']:
        specs.append(dict(s,id=s['id'].replace('IRPER_','IRCM_',1),X=32,beta=14,map_mode='compressed',
            cohort='main_beta14',experiment_class='formal_ir_compressed'))
    for s in list(specs):
        if s['dwb'] and s['workload']=='hot90':
            specs.append(dict(s,id=s['id'].replace('IRCM_','IRCM_B4_',1),beta=4,cohort='reset_stress_beta4'))
    assert len(specs)==75
    pilots=[dict(specs[0],id=f'IRCMpilot_beta{beta}',kind='sde',dwb=True,workload='hot90',beta=beta,trace_seed=901,oram_seed=1901,
                 cohort='target_scale_gate',experiment_class='pilot_ir_compressed_target') for beta in (14,4)]
    closure={n:sha(Path(__file__).parent/n) for n in ('audit_ir_compressed.py','dispatch_ir_compressed.py','start_ir_compressed_validation.py')}
    plan=dict(specs=specs,pilots=pilots,source_hashes=identity(),proof_hashes=evidence(),runner_checks_sha256=gate,execution_tools=closure,
        comparison_raw_plan_sha256=sha(oldpath),predeclared_before_target_outcomes=True,
        design='Main: depth x DWB off/on x Path/Deferred/SDE x uniform/hot90 x five seeds (60). Reset stress: same X32, beta4, DWB on, hot90 x three backends x five seeds (15); compare to main beta14.',
        parameters='N4096/B64/X32, population4229/L12, PLB8/cache6/LLC8x2/R480/A3; init4229 + alignment8059 =12288, warm12288, measure49152, finalt73728.',
        control='Same input, budget, slots and backend phase as the 60 raw-map runs. Raw-to-compressed changes packing X16 to X32 and leaf-label derivation; not a pure selective effect.',
        endpoint='No extra draining. Report pending private reset and dirty LLC. Any incomplete horizon or overflow is retained as failure; stop queue, do not silently enlarge W or R.',
        interpretation='A fixed slot budget can convert fewer map Transfers into more dummy Transfers without reducing total full-path bytes; show map-work changes separately.',
        security='conditional protocol variant; no IR-Stash, adaptive frontend reduction or full native IR claim',
        warmup_periods=1,measurement_periods=4,steady_state_claim=False,latency_claim=False,
        dependencies=[dict(pid=6200,completion='results/ir_periodic_queue_completion.json',plan='formal_ir_periodic_plan.json')])
    p=PACKAGE/'formal_ir_compressed_plan.json';assert not p.exists();save(p,plan)
    for s in pilots:save(PACKAGE/'specs'/f"{s['id']}.json",s)
    save(PACKAGE/'results/ir_compressed_plan_receipt.json',dict(plan_sha256=sha(p),generator_sha256=sha(__file__),runner_checks_sha256=gate))
    print(json.dumps(dict(status='predeclared',main=60,stress=15,pilots=2,plan_sha256=sha(p))))

if __name__=='__main__':main()

