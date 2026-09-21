"""New named revision after both full-scale controller and clock checks pass."""
from common import *
from run_ab_paced_periodic import identity
from audit_ab_cb import bill


def main():
    source=identity();periodic=PACKAGE/'results/ab_paced_periodic_checks.json';p=json.loads(periodic.read_text())
    assert p['status']=='passed' and p['source_hashes']==source and p['positive_cases']==6
    init=PACKAGE/'results/ab_paced_controlled_checks.json';c=json.loads(init.read_text())
    assert c['status']=='passed' and len(c['cases'])==6
    assert c['source_hashes']['runtime']==source['runtime'] and c['source_hashes']['frontend']==source['bootstrap_frontend']
    assert {(x['spec']['kind'],x['spec']['bottom_dummy']) for x in c['cases']}=={(k,b) for k in ('ring','gc_ring','r0') for b in (None,0)}
    for r in c['cases']:
        s=r['spec'];rp=PACKAGE/'results/ab_paced_controlled'/f"{s['layout']}_{s['kind']}.json"
        assert json.loads(rp.read_text())==r and r['status']=='passed' and r['source_hashes']==c['source_hashes']
        assert (s['N'],s['L'],s['R'],s['Q'],s['W'])==(4096,11,500,4096,65536)
        assert r['checked_data_records']==4096 and r['initialization']['t']==21845 and r['final_t']==87381
        assert r['max_boundary_stash']<=500 and r['metrics']['application_completed']==4096
        bill(r['initialization']['bill']);bill(r['validation_bill'])
    oldpath=PACKAGE/'ab_periodic_plan.json';old=json.loads(oldpath.read_text());specs=[]
    for s in old['specs']:
        specs.append(dict(s,id=s['id'].replace('ABPER_','ABPACED_',1),experiment_class='ab_paced_periodic',initialization_stride=s['profile'][1]))
    failure=PACKAGE/'results/failures/ABPER_uniform_ring_uniform_seed101.json';assert failure.exists()
    plan=dict(old,periodic=True,paced_initialization=True,specs=specs,source_hashes=source,runner_checks_sha256=sha(periodic),
        initialization_checks_sha256=sha(init),old_plan_sha256=sha(oldpath),preserved_initial_failure_sha256=sha(failure),
        initialization='same public A-slot loading cadence for all arms: one admit followed by A-1 ordinary CB dummy Transfers; setup is fully billed',
        horizon='21845 initialization Transfer slots, 8875 alignment slots, 10240 warmup slots and 40960 measured slots; final t=81920',
        revision_scope='only the common initialization cadence and the corresponding alignment clock changed; N/L/R/C/A/Y/D, pressure policy and measurement remain matched')
    path=PACKAGE/'ab_paced_periodic_plan.json'
    if path.exists():assert json.loads(path.read_text())==plan
    else:save(path,plan)
    print(json.dumps(dict(planned=len(specs),full_scale_checks=6,security_admission=False)))


if __name__=='__main__':main()
