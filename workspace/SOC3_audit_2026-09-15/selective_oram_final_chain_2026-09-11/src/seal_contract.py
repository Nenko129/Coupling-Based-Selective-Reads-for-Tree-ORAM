#!/usr/bin/env python3
"""Create the explicit reproducibility contract after reviewing changed sources.
This does NOT automatically prove a changed implementation. verify_chain.py
checks, but never silently reseals, these identities.
"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]

def main():
    names=['src/integrated_oram.py','src/certified_driver.py','src/unified_cost.py',
           'legacy/ghost_scalar.cpp','legacy/poisson_seed.h','legacy/poisson_seed.py','legacy/poisson_seed.json']
    names += [f'certificates/ghost_{m}_c280_h31{suffix}' for m in ('up','next') for suffix in ('.csv','_meta.json')]
    names += [str(p.relative_to(ROOT)) for p in (ROOT/'proofs').glob('*.md')]
    names += [str(p.relative_to(ROOT)) for p in (ROOT/'src').glob('*.py')]
    names += ['verify_chain.py']
    names = sorted(set(names))
    ct={
        'theorem_id':'GC-SERIAL-LEAF-RETAINED-SOC2-v2-2026-09-11',
        'theorem_scope':{
            'requests':'Any fixed logical address/value stream independent of ORAM coins; mixtures and applications adapting only to correct logical RAM outputs are covered.',
            'not_claimed':'A logical-query selector that adaptively reads the ORAM server transcript/internal random state is not included in the stash theorem.',
            'client':'One serial trusted client with nonrollback private state, root and nonce allocation; fail-stop on rejection/overflow.',
            'initialization':'Authenticated dummy tree, then bottom-up position-map loading and data loading through normal counted operations.',
            'timing':'Application scheduling/local computation timing, concurrent clients and crash recovery are outside this model.'},
        'protocol':{'Z':4,'A':3,'m':2,'priority':'immutable version_serial',
                    'shadow_delete':'first mapped-leaf service after invalidation',
                    'neutral_reshuffle_fills_from_stash':False,'checkpoint':'after completed logical access including scheduled maintenance'},
        'ghost':{'recurrence':'((sum(R)+L[2]+P-4)_+,L[0],L[1])','rate':'3/2','bucket_levels':'L+1','initial_state':[0,0,0]},
        'offsets':{'sde':2,'r0':6},
        'authentication':{'profile':'domain-separated variable-input 512-bit PRF','instantiation_for_tests':'HMAC-SHA-512','header_Z4_bytes':364,'nonce_bytes':16,'tag_bytes':64,'frame_header_bytes':36,'server_computes_keyed_tags':False},
        'cost':'Exact per-trace application frame invoice; periodic complete-service-interval expectation uses outward Decimal intervals.',
        'artifact_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}}
    (ROOT/'theorem_contract.json').write_text(json.dumps(ct,indent=2));print('Sealed',len(names),'identities; mathematical review remains explicit.')
if __name__=='__main__':main()
