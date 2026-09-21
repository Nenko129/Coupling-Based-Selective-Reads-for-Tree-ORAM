"""Fix the complete supplemental matrix before encrypted target outcomes."""
from common import *
from run_ir_guarded_periodic import identity,evidence
from audit_ir_guarded_periodic import audit_record,tool_hashes


def main():
    gate_path=PACKAGE/'results/ir_guarded_runner_checks.json';gate=json.loads(gate_path.read_text())
    assert gate['status']=='passed' and gate['source_hashes']==identity() and gate['proof_hashes']==evidence()
    assert gate['checker_sha256']==sha(Path(__file__).with_name('check_ir_guarded_periodic.py'))
    assert gate['audit_tools']==tool_hashes() and len(gate['cases'])==6 and len(gate['rejected_receipts'])==7
    for ref in gate['cases']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];r=json.loads(p.read_text());assert audit_record(r,r['spec'])==ref['audit']
    oldpath=PACKAGE/'formal_ir_compressed_plan.json';old=json.loads(oldpath.read_text())
    selected=[s for s in old['specs'] if s['dwb'] and s['workload']=='hot90'];assert len(selected)==30
    specs=[dict(s,id=f"IRGUARD_beta{s['beta']}_{s['kind']}_seed{s['trace_seed']}",tail_periods=1,
        cohort='guarded_beta'+str(s['beta']),experiment_class='formal_ir_guarded') for s in selected]
    specs.sort(key=lambda s:(s['trace_seed'],-s['beta'],('path','deferred','sde').index(s['kind'])))
    base=specs[0];pilots=[dict(base,id=f'IRGUARDpilot_beta{beta}',kind='sde',beta=beta,trace_seed=901,oram_seed=1901,
        cohort='guarded_target_gate',experiment_class='pilot_ir_guarded') for beta in (14,4)]
    replay=PACKAGE/'results/ir_reset_window_replay.json';replayed=json.loads(replay.read_text())
    assert replayed['status']=='passed' and replayed['encrypted_receipts_checked']==30 and not replayed['actual_bandwidth']
    assert replayed['checker_sha256']==sha(Path(__file__).with_name('ir_reset_window_replay.py'))
    plan=dict(specs=specs,pilots=pilots,source_hashes=identity(),proof_hashes=evidence(),audit_tools=tool_hashes(),
        runner_gate_sha256=sha(gate_path),original_plan_sha256=sha(oldpath),
        original_completed_snapshot_sha256=sha(PACKAGE/'results/ir_compressed_completed_snapshot.json'),
        logical_diagnosis_sha256=sha(replay),generator_sha256=sha(__file__),dispatcher_sha256=sha(Path(__file__).with_name('dispatch_ir_guarded.py')),
        design='N4096/B64/X32/PLB8/LLC8x2/cache6/R480, Hot90,DWB on,beta14/4 x Path/Deferred/SDE x seeds101-105: 30 new encrypted runs.',
        selection='Supplement designed after the original 75 outcomes and diagnostic logical replay; fixed before new target encrypted performance outcomes. Not a blind original preregistration.',
        public_window='Keep arrival gap 8 and Qwarm1536/Qmeasure6144. Append exactly one public period P=12288 to BOTH phase windows for EVERY beta/backend: warm24576, measurement61440. No early stop or outcome-dependent extra tail.',
        interpretation='One-period tail preserves public maintenance phase alignment; it is a conservative measurement design, not a proved minimal padding policy or a worst-case completion guarantee.',
        accounting='All active-window and tail bytes/RPCs billed; report prefix and guard separately. Measurements include 25% more slots than original, warmup100% more. Original outcomes remain unchanged; compare beta within this new design.',
        primary_comparisons='Within each beta: Path->SDE and Deferred->SDE; within each backend: beta14->beta4, all five paired seeds. Report absolute bytes, reset/dummy slots, completion and tail cost.',
        statistics='Paired Student-t(df4) on independent synthetic seeds. If any compared cost CV>10% or reduction CI half-width>5pp, extend the entire affected pair group to ten with seeds106-110; no survivor-only means.',
        failure_policy='Retain exact phase, bills and independently checkable partial answer digest; stop on any unexpected error. Never retry/replace original75 or silently enlarge this public tail.',
        scope='Existing compressed-map/static IR/DWB variant; no IR-Stash, PMMAC, native system security closure or latency claim.',
        goal_complete=False)
    path=PACKAGE/'formal_ir_guarded_plan.json';assert not path.exists();save(path,plan)
    save(PACKAGE/'results/ir_guarded_plan_receipt.json',dict(status='declared_before_new_ciphertext_runs',plan_sha256=sha(path),
        source_hashes=identity(),runner_gate_sha256=sha(gate_path),generator_sha256=sha(__file__),new_runs=30,pilots=2))
    print(json.dumps(dict(status='prepared',new_runs=30,pilots=2,plan_sha256=sha(path))))


if __name__=='__main__':main()
