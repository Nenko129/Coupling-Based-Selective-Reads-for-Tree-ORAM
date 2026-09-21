"""Predeclare ten supplementary Z5 Path measurements; retain stronger Z4 data."""
from common import *
from classical_stash_binding import ledger
from run_core import configs_for
from run_bulk_scale import identity
from prepare_fair_tuning import object_storage
from optimized_cost import expected_tree,sum_rows


def main():
    lp=PACKAGE/'results/classical_stash_execution_ledger.json';a=PACKAGE/'results/classical_stash_execution_ledger_audit.json'
    bound=json.loads(lp.read_text());audit=json.loads(a.read_text());ref=bound['supplemental_path']
    assert audit['status']=='passed' and audit['source_sha256']==sha(lp)
    basep=PACKAGE/'formal_tuned_plan.json';base=json.loads(basep.read_text())
    specs=base.get('specs') or [i['spec'] for i in base['items']]
    items=[]
    for s in specs:
        if s['kind']!='path':continue
        c=dict(s);c.update(id=f"C1_path5_{s['workload']}_seed{s['trace_seed']}",profile=[5,3,3],
            R=ref['minimum_common_R'],experiment_class='formal_classical_reference',study='published_bound_path_reference')
        configurations=configs_for(c);check=ledger(configurations)
        assert check['ideal_stash_budget_passed']
        assert object_storage(configurations)<=4*(1<<30)
        assert sum(x.R*x.B for x in configurations)+4*configurations[-1].N<=256*(1<<20)
        items.append(dict(entry='core',spec=c,paired_original_path_id=s['id'],
            paired_sde_id=f"B3_sde_{s['workload']}_seed{s['trace_seed']}",
            expected_periodic_cost=sum_rows([expected_tree(x) for x in configurations]),
            stash_ledger=check))
    assert len(items)==10 and {i['spec']['trace_seed'] for i in items}==set(range(101,106))
    plan=dict(status='predeclared_before_new_measurements',items=items,source_hashes=identity(),
        base_plan_sha256=sha(basep),stash_ledger_sha256=sha(lp),stash_audit_sha256=sha(a),
        unchanged=['N','B','map_B','terminal_bytes','warmup','requests','trace_seed','oram_seed','workload','compact','fusion'],
        changes=['Path Z4 to Z5','common R256 to published-bound minimum R258'],
        purpose='supplemental published-stash-bound reference; empirical Z4 remains the primary tuned Path comparator',
        full_security_admission=False,peak_client_memory_claim=False,
        statistics='five paired seeds per workload, actual serialized bytes including authentication and recursive trees; no latency claim')
    planp=PACKAGE/'formal_classical_reference_plan.json';queuep=PACKAGE/'classical_reference_queue.json'
    assert not planp.exists() and not queuep.exists()
    assert all(not (PACKAGE/'results/formal_classical_reference'/f"{i['spec']['id']}.json").exists() for i in items)
    save(planp,plan)
    save(queuep,dict(items=items,workers=1,dependencies=[],source_plan_hashes={
        planp.name:sha(planp),str(lp.relative_to(PACKAGE)):sha(lp),str(a.relative_to(PACKAGE)):sha(a)}))
    print(json.dumps(dict(status='predeclared',runs=len(items),R=ref['minimum_common_R'],
        model_bytes_per_request=items[0]['expected_periodic_cost'],queue=queuep.name)),flush=True)


if __name__=='__main__':main()
