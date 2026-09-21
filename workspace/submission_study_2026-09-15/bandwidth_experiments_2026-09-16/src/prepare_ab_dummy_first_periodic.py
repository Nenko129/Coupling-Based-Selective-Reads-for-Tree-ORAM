"""Predeclare a new paired batch only after every explicit validation gate passes."""
from common import *
from run_ab_dummy_first_periodic import identity
from audit_ab_cb import bill


def main():
    source=identity();periodic=PACKAGE/'results/ab_dummy_first_periodic_checks.json';p=json.loads(periodic.read_text())
    assert p['status']=='passed' and p['source_hashes']==source and p['positive_cases']==6 and len(p['negative_checks'])==7
    assert p['auditor_sha256']==sha(Path(__file__).with_name('audit_ab_dummy_first.py'))
    assert p['base_auditor_sha256']==sha(Path(__file__).with_name('audit_ab_cb.py'))
    init=PACKAGE/'results/ab_dummy_first_controlled_checks.json';c=json.loads(init.read_text())
    assert c['status']=='passed' and len(c['cases'])==6 and c['source_hashes']['runtime']==source['runtime']
    assert c['source_hashes']['frontend']==source['bootstrap_frontend']
    assert {(r['spec']['kind'],r['spec']['bottom_dummy']) for r in c['cases']}=={(k,b) for k in ('ring','gc_ring','r0') for b in (None,0)}
    for r in c['cases']:
        s=r['spec'];path=PACKAGE/'results/ab_dummy_first_controlled'/f"{s['layout']}_{s['kind']}.json"
        assert json.loads(path.read_text())==r and r['status']=='passed' and r['source_hashes']==c['source_hashes']
        assert (s['N'],s['L'],s['R'],s['Q'],s['W'],s['high'],s['low'])==(4096,11,500,4096,65536,48,32)
        assert r['checked_data_records']==4096 and r['initialization']['t']==21845 and r['final_t']==87381
        assert r['max_boundary_stash']<=500 and r['metrics']['application_completed']==4096
        bill(r['initialization']['bill']);bill(r['validation_bill'])
    diag=PACKAGE/'results/ab_selection_diagnostic.json';d=json.loads(diag.read_text())
    assert d['status']=='diagnostic_completed' and len(d['cases'])==2
    assert next(r for r in d['cases'] if r['spec']['policy']=='dummy_first')['status']=='completed'
    oldpath=PACKAGE/'ab_periodic_plan.json';old=json.loads(oldpath.read_text())
    specs=[dict(s,id=s['id'].replace('ABPER_','ABDF_',1),experiment_class='ab_dummy_first_periodic',initialization_stride=s['profile'][1]) for s in old['specs']]
    failures=['results/failures/ABPER_uniform_ring_uniform_seed101.json','results/ab_paced_uncontrolled_failure_observation.json','results/ab_paced_controlled_failure.json']
    plan=dict(old,specs=specs,periodic=True,paced_initialization=True,selection_policy='dummy_first_v1',source_hashes=source,
        runner_checks_sha256=sha(periodic),initialization_checks_sha256=sha(init),diagnostic_sha256=sha(diag),
        frontend_checks_sha256=sha(PACKAGE/'results/ab_dummy_first_frontend_checks.json'),old_plan_sha256=sha(oldpath),
        preserved_failures={name:sha(PACKAGE/name) for name in failures},
        initialization='public stride A: one admit then A-1 billed CB Transfers, all arms matched',
        horizon='21845 initialization + 8875 alignment + 10240 warmup + 40960 measurement; final t=81920',
        revision_scope='dummy-first selection for all arms and same public initialization cadence; unchanged N/L/R/C/A/Y/D, H48/L32 and public slots',
        scope='authenticated dummy-first CB with static bottom dummy allocation, raw recursive map, prefix cache, PLB and inclusive LLC; no DeadQ or complete adaptive capacity proof')
    path=PACKAGE/'ab_dummy_first_periodic_plan.json'
    if path.exists():assert json.loads(path.read_text())==plan
    else:save(path,plan)
    print(json.dumps(dict(planned=len(specs),full_scale_checks=6,security_admission=False)),flush=True)


if __name__=='__main__':main()
