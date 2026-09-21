from common import *
from decimal import Decimal
import heterogeneous_oram as h
from optimized_cost import expected_tree as reference
from heterogeneous_cost import expected_tree

def main():
    rows=[]
    for B in (64,4096):
        for kind in ('path','deferred','sde','ring','gc_ring','r0'):
            for fused in (False,True):
                c=h.Config(kind,12,4096,B,Z=4,A=3,S=3,R=256,fused=fused)
                a=reference(c);b=expected_tree(c)
                for key in a['components']:
                    x=a['components'][key];y=b['components'][key]
                    assert Decimal(x['lower'])<=Decimal(y['upper']) and Decimal(y['lower'])<=Decimal(x['upper']),(B,kind,fused,key,x,y)
                rows.append(dict(B=B,kind=kind,fusion=fused,all_seven_components_match=True))
    save(PACKAGE/'results/heterogeneous_cost_regression.json',dict(status='passed',uniform_regression=rows,
         scope='homogeneous reduction check; heterogeneous finite trace sizes validated separately by actual frames'))
    print(json.dumps(dict(status='passed',homogeneous_configs=len(rows))))
if __name__=='__main__':main()
