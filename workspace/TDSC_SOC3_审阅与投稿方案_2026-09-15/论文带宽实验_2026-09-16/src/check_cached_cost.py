from common import *
from decimal import Decimal
import heterogeneous_oram as h
from cached_cost import expected_tree
from heterogeneous_cost import expected_tree as no_cache

def main():
    checks=0
    for kind in ('path','deferred','sde','ring','gc_ring','r0'):
        for fusion in (False,True):
            c=h.Config(kind,4,16,64,Z=4,A=3,S=3,R=128,fused=fusion,Z_by_depth=(4,2,1,3,4) if not kind in ('ring','gc_ring','r0') else (),S_by_depth=(3,2,1,3,2) if kind in ('ring','gc_ring','r0') else ())
            a=expected_tree(c,0);b=no_cache(c)
            for key in a['components']:
                x,y=a['components'][key],b['components'][key]
                assert Decimal(x['lower'])<=Decimal(y['upper']) and Decimal(y['lower'])<=Decimal(x['upper'])
            for cut in (1,2,4):assert Decimal(expected_tree(c,cut)['total']['upper'])<Decimal(a['total']['lower'])
            checks+=1
    save(PACKAGE/'results/cached_cost_regression.json',dict(status='passed',zero_cache_seven_component_regressions=checks,
         caution='positive-cache model checked by wire-level differential test and requires measured-period validation'))
    print(json.dumps(dict(status='passed',zero_cache_configs=checks)))
if __name__=='__main__':main()
