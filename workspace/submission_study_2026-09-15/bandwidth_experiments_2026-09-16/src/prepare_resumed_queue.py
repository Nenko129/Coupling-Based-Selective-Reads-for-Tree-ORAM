"""Amend IR reserve from audited numerical evidence; preserve AB and core inputs."""
from common import *
from run_core import configs_for
from itertools import zip_longest

def main():
    auditpath=PACKAGE/'numerics/IR43_scaled_L12_c480_m128_audit.json'
    audit=json.loads(auditpath.read_text());assert audit['proposed_R_rounded32']==480
    assert next(x for x in audit['tested'] if x['R']==480)['admitted']
    for job in audit['jobs']:
        prefix=PACKAGE/job['prefix'];assert sha(prefix.with_suffix('.csv'))==job['grid_sha256']
    profile=json.loads((PACKAGE/'numerics/profiles/IR43_scaled_L12.json').read_text())
    old=json.loads((PACKAGE/'formal_cached_component_plan.json').read_text(encoding='utf-8'))
    specs=[]
    for original in old['specs']:
        s=dict(original)
        if s['family']=='IR':
            assert len(configs_for(s))==1 and configs_for(s)[0].L==12
            if s['layout']=='depth':assert s['Z_by_depth']==profile['Z_root_to_leaf']
            assert s['N']<=s['profile'][1]*(1<<(12-1))
            s.update(id=s['id'].replace('CC_IR_','CC2_IR_'),R=480,experiment_class='formal_cached_admitted')
        specs.append(s)
    amendment=dict(specs=specs,runs=len(specs),source_hashes=old['source_hashes'],
        reason='IR R256 does not meet the declared finite-lifetime upper-bound target; increase all IR four-cell reserves to R480',
        original_plan_sha256=sha(PACKAGE/'formal_cached_component_plan.json'),certificate_sha256=sha(auditpath),
        IR_old_results='retained as R256 cost/functional diagnostics; excluded from amended primary comparison',
        AB_inputs='unchanged; exact completed receipts are reused',
        security_scope='conditional selective-ghost numerical admission, not complete native IR/AB or baseline-specific cryptographic closure')
    target=PACKAGE/'formal_cached_admitted_plan.json';assert not target.exists();save(target,amendment)
    plans=[('formal_core_plan.json','core'),('formal_ablation_plan.json','core'),('formal_cached_admitted_plan.json','cached')]
    lists=[];hashes={}
    for name,mode in plans:
        p=PACKAGE/name;hashes[name]=sha(p);obj=json.loads(p.read_text(encoding='utf-8'))
        lists.append([dict(spec=s,mode=mode) for s in obj['specs']])
    items=[item for group in zip_longest(*lists) for item in group if item is not None]
    drain=json.loads((PACKAGE/'results/legacy_dispatch_drain.json').read_text(encoding='utf-8'))
    pids=[x['ProcessId'] for d in drain['dispatchers'] for x in d['children']]
    prior=json.loads((PACKAGE/'results/cached_v1_dispatch_stop.json').read_text(encoding='utf-8'))
    pids += [x['ProcessId'] for x in prior['activeChildren']]
    queue=PACKAGE/'formal_resumed_queue.json';assert not queue.exists()
    save(queue,dict(items=items,source_plan_hashes=hashes,drain_pids=sorted(set(pids)),
        scheduling='round-robin across core, ablation and cached plans; independent inputs and estimator unchanged',
        aliases='five B2 cf11 aliases remain in the original ablation plan and are not re-executed'))
    print(json.dumps(dict(queue_items=len(items),IR_new_R=480,drain_pids=pids)))

if __name__=='__main__':main()
