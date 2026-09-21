from common import *
from fractions import Fraction as F
from decimal import localcontext,ROUND_FLOOR,ROUND_CEILING
from optimized_cost import COMPONENTS,Interval,probabilities,early_interval,mean_local_witnesses
from optimized_oram import TAG,FRAME,local_indices

def expected_tree(c,cut=0):
    ds=[d for d in c.levels if d>=cut];D=len(ds);G=c.L-cut+1;T=c.L-max(0,cut-1)
    pp=probabilities(c.L) if c.selective else (F(1),)*(c.L+1);k=sum(pp[d] for d in ds)
    vals={key:Interval.exact(0) for key in COMPONENTS}
    def add(key,v):vals[key]=vals[key]+v
    def sub(key,v):
        with localcontext() as ctx:
            ctx.prec=100;ctx.rounding=ROUND_FLOOR;lo=vals[key].lo-v.hi
            ctx.rounding=ROUND_CEILING;hi=vals[key].hi-v.lo
        vals[key]=Interval(lo,hi)
    if not c.ring:
        for d in ds:
            bc=c.at(1<<d)
            if c.kind=='path':
                add('data_download',bc.Z*c.W);add('data_upload',bc.Z*c.W)
                add('headers_download',bc.H);add('headers_upload',bc.H)
            else:
                add('data_download',(pp[d]+F(1,c.A))*bc.Z*c.W);add('data_upload',F(bc.Z*c.W,c.A))
                add('headers_download',(pp[d]+F(1,c.A))*bc.H);add('headers_upload',(pp[d]+F(1,c.A))*bc.H)
        if c.kind=='path':
            add('authentication_download',T*TAG);add('authentication_upload',(D+G)*TAG);add('framing_and_control',4*FRAME+40)
        else:
            add('authentication_download',(T+D-k+F(T,c.A))*TAG)
            add('authentication_upload',(k+G+F(D+G,c.A))*TAG);add('framing_and_control',(1+F(1,c.A))*(4*FRAME+40))
    else:
        add('authentication_download',(T+D+F(T+D,c.A))*TAG);add('authentication_upload',(G+F(G,c.A))*TAG)
        add('framing_and_control',(1+F(1,c.A))*(6*FRAME+56))
        for d in ds:
            bc=c.at(1<<d);q=pp[d];w1=mean_local_witnesses(bc.n,1);wZ=mean_local_witnesses(bc.n,bc.Z);cn=len(local_indices(bc.n))
            nu=early_interval(c.A*(1<<d),q/(1<<d),bc.S)*F(1,c.A)
            add('data_download',(q+F(bc.Z,c.A))*c.W);add('data_upload',F(bc.n*c.W,c.A))
            add('headers_download',(q+F(1,c.A))*bc.H);add('headers_upload',(q+F(1,c.A))*bc.H)
            add('authentication_download',(q*w1+F(wZ,c.A))*TAG);add('authentication_upload',(q+F(cn+1,c.A))*TAG)
            add('framing_and_control',8*(q+F(1,c.A)))
            if c.fused:
                add('data_download',nu*(bc.Z-1)*c.W);add('data_upload',nu*bc.n*c.W)
                add('authentication_download',nu*wZ*TAG);sub('authentication_download',nu*w1*TAG);add('authentication_upload',nu*cn*TAG)
            else:
                add('data_download',nu*bc.Z*c.W);add('data_upload',nu*bc.n*c.W);add('headers_upload',nu*bc.H)
                add('authentication_download',nu*wZ*TAG);add('authentication_upload',nu*(cn+d-cut+2)*TAG);add('framing_and_control',nu*(4*FRAME+48))
    return dict(components={k:v.obj() for k,v in vals.items()},total=sum(vals.values(),Interval.exact(0)).obj(),
                model='ideal random slots, full service-interval expectation; actual top-cache wire format',cached_levels=cut)
