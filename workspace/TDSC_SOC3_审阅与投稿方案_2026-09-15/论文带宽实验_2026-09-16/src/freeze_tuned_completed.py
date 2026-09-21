"""Freeze only the completed B3 evidence, independently of C1 progress."""
from common import *
from audit_completed_core_components import audit_run
from audit_storage_components import audit_materialized


def main():
    p=PACKAGE/'results/tuned_reference_independent_audit.json';a=json.loads(p.read_text())
    assert a['counts']['tuned']==dict(completed=50,expected=50),'B3 is not complete'
    assert a['auditor_sha256']==sha(PACKAGE/'src/audit_tuned_reference.py')
    for name,digest_ in a['helper_sha256'].items():assert sha(PACKAGE/'src'/name)==digest_
    planp=PACKAGE/'formal_tuned_plan.json';plan=json.loads(planp.read_text())
    specs=plan.get('specs') or [i['spec'] for i in plan['items']]
    assert len(specs)==50 and a['plan_hashes'][planp.name]==sha(planp)
    rows=[r for r in a['rows'] if r['group']=='tuned'];assert len(rows)==50
    assert {r['spec']['id'] for r in rows}=={s['id'] for s in specs}
    for row in rows:
        ref=row['source'];rp=PACKAGE/ref['path'];assert sha(rp)==ref['sha256'];raw=json.loads(rp.read_text())
        audit_run(raw,row['spec'],False)
        assert audit_materialized(raw)==row['resource']
    cells=[c for c in a['cells'] if c['group']=='tuned']
    effects=[e for e in a['effects'] if e['baseline_group']=='tuned']
    assert len(cells)==10 and len(effects)==6
    assert all(c['bytes_per_request']['complete'] and c['bytes_per_request']['n']==5 for c in cells)
    assert all(e['bytes_saving']['complete'] and e['bytes_saving']['n']==5 for e in effects)
    assert not a['repeat_gate_triggered']
    candidates=PACKAGE/'results/fair_tuning_candidates.json';t=json.loads(candidates.read_text())
    assert len(t['candidates'])==72 and len(t['selected'])==5
    for r in rows:
        chosen=next(c for c in t['candidates'] if c['candidate_id'] in t['selected'] and c['spec']['kind']==r['spec']['kind'])
        assert r['configs']==chosen['configs']
    out=dict(status='passed',runs=50,cells=cells,effects=effects,rows=rows,
        receipts=[r['source'] for r in rows],plan_sha256=sha(planp),candidate_sha256=sha(candidates),
        source_identity=source_identity(),audit_producer_sha256=sha(PACKAGE/'src/audit_tuned_reference.py'),
        freezer_sha256=sha(__file__),helper_hashes=a['helper_sha256'],
        repeat_gate_triggered=False,candidates=72,scope='predeclared tuned B3 only, two workloads and five independent paired seeds',
        full_security_admission=False,full_paper_complete=False)
    dest=PACKAGE/'results/tuned_completed_snapshot.json'
    if dest.exists():assert json.loads(dest.read_text())==out,'immutable completed snapshot changed'
    else:save(dest,out)
    print(json.dumps(dict(status='passed',runs=50,cells=10,effects=6)))


if __name__=='__main__':main()
