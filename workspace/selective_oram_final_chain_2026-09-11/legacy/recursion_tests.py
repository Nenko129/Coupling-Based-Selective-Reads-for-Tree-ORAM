#!/usr/bin/env python3
"""Three-layer position-map driver using ONE atomic read/modify access per layer.
Plaintext transition regression only; authentication/atomic durable commit are
separate compiler obligations. Full debug maps are assertions, not path inputs.
"""
from pathlib import Path
import json,random
from core_state_tests import Core

class Recursive:
    def __init__(self,kind:str,seed:int,K:int=3):
        self.chi=4;self.wordbits=8;self.sizes=[48,12,3][:K];self.L=[5,3,1][:K];self.K=K
        self.rng=[random.Random(seed+100003*j) for j in range(K)]
        self.cores=[Core(L,4,3,3,kind,seed+313*j) for j,L in enumerate(self.L)]
        initial=[[self.rng[j].randrange(1<<L) for _ in range(self.sizes[j])] for j,L in enumerate(self.L)]
        self.client_pos=initial[-1][:]
        for j in range(K-1,0,-1):
            values=initial[j-1]
            for b in range(self.sizes[j]):
                word=sum(values[b*self.chi+k]<<(self.wordbits*k) for k in range(self.chi) if b*self.chi+k<len(values))
                self.access_layer(j,b,word)
        for i in range(self.sizes[0]):self.access_layer(0,i,i*17)
        self.truth={i:i*17 for i in range(self.sizes[0])}
    def access_layer(self,j:int,address:int,value=None,transform=None):
        newleaf=self.rng[j].randrange(1<<self.L[j])
        if j==self.K-1:
            oldleaf=self.client_pos[address];self.client_pos[address]=newleaf
        else:
            block,offset=divmod(address,self.chi);shift=offset*self.wordbits;bitmask=((1<<self.wordbits)-1)<<shift
            oldword=self.access_layer(j+1,block,transform=lambda w:(w&~bitmask)|(newleaf<<shift))
            oldleaf=(oldword>>shift)&((1<<self.wordbits)-1)
        return self.cores[j].access(address,value,newleaf,oldleaf,lookup_leaf=oldleaf,transform=transform)

def run():
    results=[];top=layer_calls=0
    for K in [2,3]:
        for kind in ['sde','r0']:
            for seed in range(3):
                m=Recursive(kind,seed+101,K);r=random.Random(seed);setup=[c.t for c in m.cores]
                for t in range(1200):
                    a=0 if t%7==0 else r.randrange(48);v=None if t%3 else r.randrange(1<<60)
                    before=[c.t for c in m.cores];got=m.access_layer(0,a,v)
                    assert got==m.truth[a]
                    if v is not None:m.truth[a]=v
                    assert [c.t-before[j] for j,c in enumerate(m.cores)]==[1]*K
                top+=1200;layer_calls+=1200*K
                results.append(dict(external_trees=K,kind=kind,seed=seed,top_requests=1200,setup_accesses=setup,
                    total_layer_accesses=[c.t for c in m.cores],client_position_entries=len(m.client_pos)))
    out=dict(runs=results,top_level_requests=top,online_layer_calls=layer_calls,
        one_atomic_read_modify_per_layer=True,bottom_up_public_setup=True,
        scope='Plaintext recursive state-machine test, not encrypted end-to-end or crash consistency validation.')
    (Path(__file__).resolve().parent/'recursion_results.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k!='runs'},indent=2))
if __name__=='__main__':run()
