"""Static depth-layout cost; actual finite prefixes are independently invoiced."""
from common import *
from fractions import Fraction as F
from decimal import localcontext,ROUND_FLOOR,ROUND_CEILING
from optimized_cost import Interval,COMPONENTS,probabilities,early_interval,mean_local_witnesses
from optimized_oram import TAG,FRAME,local_indices

def expected_tree(c):
    q=probabilities(c.L) if c.selective else (F(1),)*(c.L+1);ds=c.levels;k=sum(q[d] for d in ds);D=len(ds);n=c.L+1
    v={key:Interval.exact(0) for key in COMPONENTS}
    def add(key,val):v[key]=v[key]+val
    def subtract(key,val):
        with localcontext() as ctx:
            ctx.prec=100;ctx.rounding=ROUND_FLOOR;lo=v[key].lo-val.hi
            ctx.rounding=ROUND_CEILING;hi=v[key].hi-val.lo
        v[key]=Interval(lo,hi)
    if not c.ring:
        for d in ds:
            bc=c.at(1<<d)
            if c.kind=='path':
                add('data_download',bc.Z*c.W);add('data_upload',bc.Z*c.W)
                add('headers_download',bc.H);add('headers_upload',bc.H)
            else:
                add('data_download',(q[d]+F(1,c.A))*bc.Z*c.W);add('data_upload',F(bc.Z*c.W,c.A))
                add('headers_download',(q[d]+F(1,c.A))*bc.H);add('headers_upload',(q[d]+F(1,c.A))*bc.H)
        if c.kind=='path':
            add('authentication_download',c.L*TAG);add('authentication_upload',2*n*TAG)
            add('framing_and_control',4*FRAME+40)
        else:
            add('authentication_download',(c.L+D-k+F(c.L,c.A))*TAG)
            add('authentication_upload',(k+n+F(D+n,c.A))*TAG)
            add('framing_and_control',(1+F(1,c.A))*(4*FRAME+40))
    else:
        add('authentication_download',(c.L+D+F(c.L+D,c.A))*TAG)
        add('authentication_upload',(n+F(n,c.A))*TAG)
        add('framing_and_control',(1+F(1,c.A))*(6*FRAME+56))
        for d in ds:
            bc=c.at(1<<d);w1=mean_local_witnesses(bc.n,1);wZ=mean_local_witnesses(bc.n,bc.Z);cn=len(local_indices(bc.n))
            rate=early_interval(c.A*(1<<d),q[d]/(1<<d),bc.S)*F(1,c.A)
            add('data_download',(q[d]+F(bc.Z,c.A))*c.W);add('data_upload',F(bc.n*c.W,c.A))
            add('headers_download',(q[d]+F(1,c.A))*bc.H);add('headers_upload',(q[d]+F(1,c.A))*bc.H)
            add('authentication_download',(q[d]*w1+F(wZ,c.A))*TAG)
            add('authentication_upload',(q[d]+F(cn+1,c.A))*TAG)
            add('framing_and_control',8*(q[d]+F(1,c.A)))
            if c.fused:
                add('data_download',rate*(bc.Z-1)*c.W);add('data_upload',rate*bc.n*c.W)
                add('authentication_download',rate*wZ*TAG);subtract('authentication_download',rate*w1*TAG)
                add('authentication_upload',rate*cn*TAG)
            else:
                add('data_download',rate*bc.Z*c.W);add('data_upload',rate*bc.n*c.W)
                add('headers_upload',rate*bc.H);add('authentication_download',rate*wZ*TAG)
                add('authentication_upload',rate*(cn+d+2)*TAG);add('framing_and_control',rate*(4*FRAME+48))
    return dict(components={key:val.obj() for key,val in v.items()},total=sum(v.values(),Interval.exact(0)).obj(),
                model='static depth Z/S, no cache/CB/DeadQ, full service-interval expectation')
