from pathlib import Path
import sys,json
from fractions import Fraction
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minimal_runtime import *
from optimized_cost import probabilities

def main():
    cases=0;edges=0;prob=[]
    for L in range(1,9):
        counts=[0]*(L+1)
        for leaf in range(1<<L):
            ds=h.gc(0,leaf,L)
            assert L in ds
            for d in ds:counts[d]+=1
        expected=probabilities(L);assert tuple(Fraction(n,1<<L) for n in counts)==expected
        for g in range(1<<L):
            ep=h.rev(g,L)
            for leaf in range(1<<L):
                a=h.gc(g,leaf,L);b=h.gc(g+1,leaf,L);z=h.lcp(leaf,ep,L)
                assert {d for d in a if d>z}=={d for d in b if d>z}
                assert all(h.node(leaf,d,L)==h.node(ep,d,L) for d in a^b)
                cases+=1;edges+=len(a^b)
        prob.append(dict(L=L,exact_probabilities=[str(p) for p in expected]))
    save(HOME/'results/public_selector_checks.json',dict(status='passed',phase_leaf_cases=cases,changed_depth_checks=edges,probabilities=prob,
        source_sha256=sha(Path(__file__)),engine_sha256=sha(EVAL/'src/heterogeneous_oram.py'),scope='exact finite locality and probability checks, L1..8'))
    print(json.dumps(dict(status='passed',phase_leaf_cases=cases,changed_depth_checks=edges)))
if __name__=='__main__':main()
