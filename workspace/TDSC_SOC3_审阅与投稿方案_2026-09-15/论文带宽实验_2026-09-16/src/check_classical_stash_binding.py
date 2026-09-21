"""Read-only independent recomputation and damaged-ledger rejection."""
from common import *
from fractions import Fraction as F
import copy,math


def fraction(x):return F(int(x['numerator']),int(x['denominator']))


def independent_exp_upper(x):
    # Deliberately independent of the producer's iterative 64-term routine.
    partial=sum((x**k/F(math.factorial(k)) for k in range(129)),F(0))
    return partial+(x**129/F(math.factorial(129)))/(1-x/F(130))


def check_point(p,c,q):
    assert p['config']==c and int(p['checked_boundary_count'])==q
    assert p['initialization_accesses']==q-(1<<56) and int(p['online_accesses'])==1<<56
    if c['R']>=c['N']:
        assert p['covered'] and p['offset']==0 and fraction(p['fixed_boundary_bound'])==0
        eps=F(0)
    elif c['kind']=='path':
        allowed=c['Z']==5 and c['N']<=1<<c['L']
        assert p['covered']==allowed
        if not allowed:return None
        assert p['offset']==0
        eps=min(F(1),14*F(3,5)**c['R'])
    else:
        assert c['kind']=='ring' and c['N']<=c['A']*(1<<(c['L']-1)) and p['covered']
        shift=c['A']-1;assert p['offset']==shift
        rho=F(c['A'],2*c['Z']);x=F(2*c['Z']-c['A'],2)
        constants=p['constants'];eu=fraction(constants['exp_upper'])
        assert rho==fraction(constants['rho']) and x==fraction(constants['x'])
        assert eu>=independent_exp_upper(x)
        beta=4*eu*rho**c['Z']
        assert beta==fraction(constants['beta_upper']) and 0<beta<1
        eps=F(1) if c['R']<shift else min(F(1),rho**(c['R']-shift)/(1-beta))
    assert fraction(p['fixed_boundary_bound'])==eps
    assert fraction(p['lifetime_bound'])==q*eps
    return q*eps


def validate(out):
    assert out['source_hashes']==source_identity() and out['full_security_admission'] is False
    cp=PACKAGE/'results/classical_execution_projection_checks.json';proof=json.loads(cp.read_text())
    assert out['projection_receipt_sha256']==sha(cp) and proof['status']=='passed'
    assert proof['source_hashes']==source_identity() and proof['checker_sha256']==sha(PACKAGE/'src/check_classical_execution_projection.py')
    for name,digest_ in out['plan_hashes'].items():assert sha(PACKAGE/name)==digest_
    assert out['producer_sha256']==sha(PACKAGE/'src/classical_stash_binding.py')
    assert out['arithmetic_source_sha256']==sha(PACKAGE/'src/baseline_capacity_arithmetic.py')
    assert len(out['rows'])==4
    for row in out['rows']+[out['supplemental_path']]:
        cs=row['configs'];ledger=row['ledger'];points=ledger['points']
        assert len(cs)==len(points) and len(cs)>0 and ledger['full_security_admission'] is False
        s=row['spec'];n=s['N'];b=s['B'];summed=0;total=F(0);complete=True
        for j,(c,p) in enumerate(zip(cs,points)):
            assert c['tree']==j and c['N']==n and c['B']==b and c['kind']==s['kind']
            assert (c['Z'],c['A'],c['S'])==tuple(s['profile']) and c['R']==s['R']
            assert c['compact']==s['compact'] and c['fused']==s['fusion']
            height=1
            while n>c['A']*(1<<(height-1)):height+=1
            assert c['L']==height
            if j+1<len(cs):
                assert n*4>s['terminal_bytes'];b=s['map_B'];n=(n+b//4-1)//(b//4)
            else:assert n*4<=s['terminal_bytes']
            summed+=c['N'];bound=check_point(p,c,(1<<56)+summed)
            if bound is None:complete=False
            else:total+=bound
        assert ledger['all_points_covered']==complete
        assert fraction(ledger['stash_budget'])==F(1,1<<130) and int(ledger['online_horizon'])==1<<56
        assert ledger['ideal_stash_budget_passed']==(complete and total<=F(1,1<<130))
        if complete:
            assert fraction(ledger['lifetime_stash_upper'])==total
            if total:assert abs(ledger['log2_lifetime_upper']-math.log2(total))<1e-12
        else:assert ledger['lifetime_stash_upper'] is None
    extra=out['supplemental_path'];r=extra['minimum_common_R']
    assert r==extra['spec']['R'] and extra['spec']['profile']==[5,3,3]
    assert extra['ledger']['ideal_stash_budget_passed'] and extra['performance_measured'] is False
    # A lower bound on the displayed classical expression at R-1 suffices to
    # reject a claim that a still smaller common R passes that expression.
    lower=(1<<56)*14*F(3,5)**(r-1)
    assert lower>F(1,1<<130)
    for r in out['rows']:
        p=PACKAGE/r['plan'];plan=json.loads(p.read_text());specs=plan.get('specs') or [i['spec'] for i in plan['items']]
        assert r['spec'] in specs
    return True


def main():
    path=PACKAGE/'results/classical_stash_execution_ledger.json';out=json.loads(path.read_text())
    validate(out);damaged=[]
    for case in ('remove_phase_reserve','omit_initialization','omit_recursive_layer',
                 'claim_Z4_admitted','change_supplemental_R','shrink_lifetime_bound'):
        x=copy.deepcopy(out)
        ring=next(r for r in x['rows'] if r['spec']['kind']=='ring')
        if case=='remove_phase_reserve':ring['ledger']['points'][0]['offset']=0
        if case=='omit_initialization':ring['ledger']['points'][0]['checked_boundary_count']=str(1<<56)
        if case=='omit_recursive_layer':ring['configs'].pop();ring['ledger']['points'].pop()
        if case=='claim_Z4_admitted':x['rows'][0]['ledger']['ideal_stash_budget_passed']=True
        if case=='change_supplemental_R':x['supplemental_path']['minimum_common_R']-=1
        if case=='shrink_lifetime_bound':ring['ledger']['lifetime_stash_upper']['numerator']='0'
        try:validate(x)
        except AssertionError:damaged.append(dict(case=case,rejected=True))
        else:raise AssertionError('damaged ledger accepted: '+case)
    save(PACKAGE/'results/classical_stash_execution_ledger_audit.json',dict(status='passed',
        source_sha256=sha(path),checker_sha256=sha(__file__),validated_configurations=5,
        independent_exp_degree=128,damaged_ledger_checks=damaged,full_security_admission=False))
    print(json.dumps(dict(status='passed',configurations=5,rejections=len(damaged))))


if __name__=='__main__':main()
