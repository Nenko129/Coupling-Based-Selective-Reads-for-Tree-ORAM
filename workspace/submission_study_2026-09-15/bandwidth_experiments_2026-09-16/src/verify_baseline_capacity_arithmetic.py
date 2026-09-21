"""Recompute a tighter rational exponential enclosure without producer imports."""
from common import *
from fractions import Fraction as F
import math


def unpack(d):return F(int(d['numerator']),int(d['denominator']))


def main():
    path=PACKAGE/'results/baseline_capacity_arithmetic.json';d=json.loads(path.read_text());target=unpack(d['stash_budget'])
    assert target==F(1,2**128) and d['full_security_admission'] is False
    assert len(d['rows'])==8
    for s in d['sources'].values():assert sha(s['path'])==s['sha256']
    for r in d['rows']:
        K=r['tree_union_factor'];Q=int(r['per_tree_access_bound']);assert Q==2**96 and K in (1,16)
        assert r['executed_protocol_admitted'] is False
        if r['protocol']=='classical_path':
            assert r['Z']==5;fn=lambda n:K*Q*14*F(3,5)**n
        else:
            Z,A=r['Z'],r['A'];rho=F(A,2*Z);x=F(2*Z-A,2);c={k:unpack(v) for k,v in r['constants'].items()}
            assert c['rho']==rho and c['x']==x
            # Explicit powers/factorials at a different order; bound all later
            # consecutive term ratios by x/98.
            low=sum((x**j/F(math.factorial(j)) for j in range(97)),F(0))
            high=low+x**97/F(math.factorial(97))/(1-x/98)
            assert c['exp_lower']<=low<=high<=c['exp_upper']
            beta=c['beta_upper'];assert beta==4*rho**Z*c['exp_upper']
            if not r['theorem_parameter_test']:
                assert 4*rho**Z*low>=1 and r['meets_stash_budget'] is None;continue
            assert beta<1;fn=lambda n:K*Q*rho**n/(1-beta)
        assert fn(r['R'])==unpack(r['lifetime_stash_upper'])
        assert (fn(r['R'])<=target)==r['meets_stash_budget']
        n=r['min_R_for_stash_budget'];assert fn(n)<=target<fn(n-1)
        assert abs(math.log2(fn(r['R']))-r['display_log2_upper'])<1e-12
    save(PACKAGE/'results/baseline_capacity_arithmetic_audit.json',dict(status='passed',rows=8,
        source_sha256=sha(path),verifier_sha256=sha(__file__),independent_enclosure_degree=96,full_security_admission=False))
    print(json.dumps(dict(status='passed',rows=8,full_security_admission=False)))


if __name__=='__main__':main()
