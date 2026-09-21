"""Independently verify displayed minimum-R and historical phase-corrected rows."""
from common import *
from fractions import Fraction as F
import math


def unpack(x):return F(int(x['numerator']),int(x['denominator']))


def main():
    p=PACKAGE/'results/classical_stash_execution_ledger.json';d=json.loads(p.read_text())
    ap=PACKAGE/'results/classical_stash_execution_ledger_audit.json';a=json.loads(ap.read_text())
    assert a['status']=='passed' and a['source_sha256']==sha(p)
    constants={}
    for row in d['rows']:
        if row['spec']['kind']=='ring':
            cs=row['ledger']['points'][0]['constants'];z,a_=row['spec']['profile'][:2]
            constants[z,a_]=(unpack(cs['rho']),unpack(cs['beta_upper']))
    checked=[]
    for row in d['rows']+[d['supplemental_path']]:
        if not row['ledger']['all_points_covered']:continue
        claimed=row.get('minimum_common_R_for_classical_bound',row.get('minimum_common_R'))
        def total(r):
            result=F(0);initial=0
            for c in row['configs']:
                initial+=c['N'];q=(1<<56)+initial
                if r>=c['N']:eps=F(0)
                elif c['kind']=='path':eps=min(F(1),14*F(3,5)**r)
                else:
                    rho,beta=constants[c['Z'],c['A']];shift=c['A']-1
                    eps=F(1) if r<shift else min(F(1),rho**(r-shift)/(1-beta))
                result+=q*eps
            return result
        assert total(claimed)<=F(1,1<<130)<total(claimed-1)
        assert all(total(r)>F(1,1<<130) for r in range(claimed))
        checked.append(dict(kind=row['spec']['kind'],profile=row['spec']['profile'],minimum_R=claimed))
    assert len(checked)==3
    history=d['historical_horizon_phase_corrections'];assert len(history)==4
    for row in history:
        z,a_,k,r=row['Z'],row['A'],row['K'],row['minimum_R']
        rho,beta=constants[z,a_];shift=a_-1;assert row['completed_boundary_offset']==shift
        calc=lambda r:k*(1<<96)*rho**(r-shift)/(1-beta)
        assert calc(r)<=F(1,1<<128)<calc(r-1)
        assert abs(math.log2(calc(256))-row['lifetime_log2_at_R256'])<1e-12
    save(PACKAGE/'results/classical_minima_audit.json',dict(status='passed',main_minima=checked,
        historical_rows_checked=4,ledger_sha256=sha(p),ledger_audit_sha256=sha(ap),
        auditor_sha256=sha(__file__),interpretation='minimum for the stated conservative expression, not minimum physically safe stash'))
    print(json.dumps(dict(status='passed',main_minima=3,historical_rows=4)))


if __name__=='__main__':main()
