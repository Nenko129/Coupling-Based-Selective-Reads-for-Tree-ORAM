"""Bind revised protocol identity, then reuse independent geometry/bill checks."""
from common import *
from audit_ab_cb import audit_record as base_audit,matched,bill


def inputs(plan_name='ab_dummy_first_periodic_plan.json'):
    from run_ab_dummy_first_periodic import identity
    path=PACKAGE/plan_name;plan=json.loads(path.read_text());assert plan['source_hashes']==identity()
    assert plan['selection_policy']=='dummy_first_v1' and plan['periodic'] and plan['paced_initialization']
    p=PACKAGE/'results/ab_dummy_first_frontend_checks.json';proof=json.loads(p.read_text())
    assert proof['status']=='passed' and proof['source_hashes']==plan['source_hashes']['runtime']
    assert len(proof['cases'])==12 and proof['pressure_exercised']
    assert plan['frontend_checks_sha256']==sha(p)
    assert proof['engine_checks_sha256']==sha(PACKAGE/'results/ab_dummy_first_checks.json')
    manifest=json.loads((COMPOSITION.parent/'MANIFEST.sha256.json').read_text());files=manifest.get('files',manifest)
    for name in ('frontends.py','transfer_backend.py'):assert sha(COMPOSITION/name)==files['src/'+name]
    return plan,dict(source=plan['source_hashes'],proof_hash=sha(p),periodic=True,paced=True)


def audit_record(r,s,source,proof_hash,periodic=True,paced=True):
    assert periodic and paced and r['cb_selection_policy']=='dummy_first_v1'
    return base_audit(r,s,source,proof_hash,periodic=True,paced=True)
