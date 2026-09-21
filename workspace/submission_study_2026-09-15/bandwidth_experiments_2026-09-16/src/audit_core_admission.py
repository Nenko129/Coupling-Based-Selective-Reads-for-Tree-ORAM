"""Explicit gate results; no inference from successful performance runs."""
from common import *
from run_core import configs_for
from optimized_gate import OptimizedBank

def main():
    plan=json.loads((PACKAGE/'formal_core_plan.json').read_text(encoding='utf-8'));bank=OptimizedBank();rows=[]
    for kind in dict.fromkeys(s['kind'] for s in plan['specs']):
        spec=next(s for s in plan['specs'] if s['kind']==kind);cs=configs_for(spec)
        record=dict(kind=kind,configs=[dict(vars(c)) for c in cs],performance_run_eligibility=True,
                    common_boundary_stash_blocks=256,common_crypto_serializer=True,
                    published_core_lifetime_admission=False)
        try:gate=bank.plan(cs,1<<56)
        except (ValueError,KeyError) as e:record['existing_gate_rejection']=str(e)
        else:
            record['published_core_lifetime_admission']=True;record['gate']=gate
            record['qualification']='Existing SOC3 core gate + transport differential binding, conditional PRF model. No new independent security audit.'
        if kind not in ('sde','r0'):
            record['outstanding']='Need baseline-specific capacity/lifetime/active-crypto binding; the selective certificate is not assigned by similarity.'
        rows.append(record)
    save(PACKAGE/'results/core_admission.json',dict(status='partial_admission',rows=rows,bank_variant_hashes_checked=bank.variant_hashes_checked,
         all_baselines_same_certified_lifetime=False,comparison_claim='same public geometry, serializer and reserved stash; full same-guarantee label remains pending'))
    print(json.dumps({r['kind']:r['published_core_lifetime_admission'] for r in rows}))
if __name__=='__main__':main()
