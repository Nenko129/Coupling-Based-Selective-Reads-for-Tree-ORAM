"""Independent exact expectations for small complete service intervals."""
from pathlib import Path
import sys,math,json
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from optimized_oram import Config,local_indices
from optimized_cost import expected_tree,probabilities,mean_local_witnesses
checks=0
for Z,A in [(4,3),(7,6)]:
    for kind in ('ring','r0'):
        for L in range(1,5):
            for S in (1,3,6):
                c=Config(kind,L,1,64,Z=Z,A=A,S=S)
                pp=probabilities(L) if kind=='r0' else (F(1),)*(L+1)
                k=sum(pp[d] for d in c.levels);q=len(c.levels);w1=mean_local_witnesses(c.n,1);wZ=mean_local_witnesses(c.n,Z);cn=len(local_indices(c.n))
                exact=k*(c.W+2*c.H)+(2*L+q+1+k*(w1+1))*64+272+8*k
                exact+=F(1,A)*(q*((Z+c.n)*c.W+2*c.H)+(2*L+1+q*(wZ+cn+2))*64+272+8*q)
                for d in c.levels:
                    n=A*(1<<d);p=pp[d]/(1<<d)
                    eta=sum(F(math.comb(n,x))*p**x*(1-p)**(n-x)*max(0,(x-1)//S) for x in range(n+1))/A
                    exact+=eta*((Z+c.n-1)*c.W+(wZ-w1+cn)*64)
                got=expected_tree(c)['total']
                assert F(got['lower'])<=exact<=F(got['upper']),(c,exact,got)
                checks+=1
result=dict(exact_complete_interval_expectations=checks,all_inside_outward_bounds=True,max_binomial_trials=96)
(ROOT/'results/exact_expected_intervals.json').write_text(json.dumps(result,indent=2));print(result)
