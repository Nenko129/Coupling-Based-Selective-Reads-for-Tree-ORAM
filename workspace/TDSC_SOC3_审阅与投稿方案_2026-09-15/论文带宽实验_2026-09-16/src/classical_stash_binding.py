"""Bind classical stash arithmetic to concrete core geometries and clocks.

This is an ideal-random-leaf stash ledger, not full active-security admission.
Ring uses an explicit A-1 completed-access reserve after an eviction bound.
"""
from common import *
from fractions import Fraction as F
from dataclasses import asdict, replace
import math
from baseline_capacity_arithmetic import ring_constants, pack
from run_core import configs_for

ONLINE = 1 << 56
STASH_LIMIT = F(1, 1 << 130)


def point(config, rounds):
    c = config
    assert c.kind in ('path', 'ring') and rounds >= 0
    if c.R >= c.N:
        return dict(rule='deterministic current-record count',epsilon=F(0),offset=0)
    if c.kind == 'path':
        if c.Z != 5 or c.N > (1 << c.L):
            raise ValueError('Path theorem needs Z5 and working set N <= 2^L')
        return dict(rule='Path JACM Theorem 5.1 with working-set upper bound 2^L',
                    epsilon=min(F(1),14 * F(3,5)**c.R),offset=0)
    if c.N > c.A * (1 << (c.L-1)):
        raise ValueError('Ring population geometry')
    constants = ring_constants(c.Z,c.A)
    if constants is None or constants['beta_upper'] >= 1:
        raise ValueError('Ring Chernoff parameter condition not satisfied')
    offset = c.A - 1
    if c.R < offset:
        epsilon = F(1)
    else:
        epsilon = min(F(1), constants['rho']**(c.R-offset)/(1-constants['beta_upper']))
    return dict(rule='Ring post-eviction bound plus A-1 completed-access reserve',
                epsilon=epsilon,offset=offset,constants=constants)


def ledger(configs, online=ONLINE, limit=STASH_LIMIT):
    subtotal = 0; total = F(0); rows = []; errors = []
    for j,c in enumerate(configs):
        assert c.tree == j
        subtotal += c.N
        q = online + subtotal
        record = dict(config=asdict(c),initialization_accesses=subtotal,online_accesses=str(online),
                      checked_boundary_count=str(q))
        try:
            result = point(c,q)
        except ValueError as ex:
            errors.append(dict(tree=j,reason=str(ex)))
            record.update(covered=False,reason=str(ex))
        else:
            eps = result.pop('epsilon');constants = result.pop('constants',None)
            total += q*eps
            record.update(covered=True,**result,fixed_boundary_bound=pack(eps),
                          lifetime_bound=pack(q*eps))
            if constants: record['constants']={k:pack(v) for k,v in constants.items()}
        rows.append(record)
    return dict(points=rows,online_horizon=str(online),stash_budget=pack(limit),
                all_points_covered=not errors,errors=errors,
                lifetime_stash_upper=pack(total) if not errors else None,
                log2_lifetime_upper=(math.log2(total) if total else None) if not errors else None,
                ideal_stash_budget_passed=not errors and total<=limit,
                full_security_admission=False)


def smallest_common_r(configs):
    # Respect source theorem scope even if a brute-force N-block allocation
    # would eventually make a previously unsupported profile deterministic.
    for c in configs: point(replace(c,R=0),0)
    for r in range(1,4097):
        adjusted=[replace(c,R=r) for c in configs]
        if ledger(adjusted)['ideal_stash_budget_passed']: return r
    raise ValueError('R search exhausted')


def main():
    checker_path=PACKAGE/'results/classical_execution_projection_checks.json'
    checked=json.loads(checker_path.read_text())
    assert checked['status']=='passed' and checked['source_hashes']==source_identity()
    assert checked['checker_sha256']==sha(PACKAGE/'src/check_classical_execution_projection.py')
    plans={};rows=[]
    for file in ('formal_core_plan.json','formal_tuned_plan.json'):
        p=PACKAGE/file;plan=json.loads(p.read_text());plans[file]=sha(p)
        specs=plan.get('specs') or [i['spec'] for i in plan['items']]
        for kind in ('path','ring'):
            s=next(s for s in specs if s['kind']==kind);configs=configs_for(s)
            row=dict(plan=file,spec=s,configs=[asdict(c) for c in configs],ledger=ledger(configs))
            try:row['minimum_common_R_for_classical_bound']=smallest_common_r(configs)
            except ValueError as ex:row['minimum_R_unavailable_reason']=str(ex)
            rows.append(row)
    base=next(r for r in rows if r['plan']=='formal_tuned_plan.json' and r['spec']['kind']=='path')
    spec=dict(base['spec']);spec['profile']=[5,3,3]
    configurations=configs_for(spec);minimum=smallest_common_r(configurations);spec['R']=minimum
    configurations=configs_for(spec)
    supplemental=dict(spec=spec,configs=[asdict(c) for c in configurations],minimum_common_R=minimum,
                      ledger=ledger(configurations),performance_measured=False)
    assert supplemental['ledger']['ideal_stash_budget_passed']
    corrections=[]
    for z,a in ((4,3),(7,6)):
        constants=ring_constants(z,a)
        for k in (1,16):
            fn=lambda r: k*(1<<96)*constants['rho']**(r-(a-1))/(1-constants['beta_upper'])
            r=next(r for r in range(a-1,1024) if fn(r)<=F(1,1<<128))
            corrections.append(dict(Z=z,A=a,K=k,completed_boundary_offset=a-1,
                lifetime_log2_at_R256=math.log2(fn(256)),minimum_R=r))
    out=dict(status='ideal_stash_ledger_bound_to_execution_projection',rows=rows,
             supplemental_path=supplemental,historical_horizon_phase_corrections=corrections,
             proof_note='45_经典基线执行归约与容量账本.md',producer_sha256=sha(__file__),
             arithmetic_source_sha256=sha(PACKAGE/'src/baseline_capacity_arithmetic.py'),
             projection_receipt_sha256=sha(checker_path),plan_hashes=plans,
             paper_hashes={x:sha(ROOT/'baselines'/f'{x}.pdf') for x in ('path','ring')},
             scope='homogeneous core with fixed address histories independent of ORAM coins, honest authenticated prefix, ideal independent leaves',
             source_hashes=source_identity(),full_security_admission=False,
             exclusions=['full malicious-transcript simulation and concrete PRF bound',
                         'IR-Stash/CB/heterogeneous buckets/adaptive local-hit scheduling',
                         'true peak client memory; R excludes path workspace',
                         'unsupported Z4 Path is retained as an empirical comparator'])
    save(PACKAGE/'results/classical_stash_execution_ledger.json',out)
    print(json.dumps(dict(status=out['status'],rows=len(rows),
        supplemental_path_R=minimum,supplemental_path_log2= supplemental['ledger']['log2_lifetime_upper'],
        full_security_admission=False)),flush=True)


if __name__=='__main__':main()
