#!/usr/bin/env python3
"""Independent trace invoice and outward Decimal expected-cost intervals.
Both derive constants and proof shapes from the executed serializer. Bytes are
application protocol frames, not Ethernet/TCP/TLS bytes or wall-clock speedups.
"""
from __future__ import annotations
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from collections import Counter
from pathlib import Path
import math,json
from optimized_oram import *

COMPONENTS=('data_download','data_upload','headers_download','headers_upload','authentication_download','authentication_upload','framing_and_control')

def invoice_event(c:Config,e:dict)->dict:
    """Predict wire sizes from public event fields, not recorded len(bytes)."""
    v=Counter({k:0 for k in COMPONENTS});op=e['opcode']
    if op==INIT:
        root=c.rootless and e['bucket']==1
        v['headers_upload']=0 if root else c.H
        v['data_upload']=0 if root else c.n*c.W
        v['authentication_upload']=(2+(len(local_indices(c.n)) if c.ring and not root else 0))*TAG
        v['framing_and_control']=2*FRAME+8
    else:
        ds=e['depths'];k=len(ds)
        if op in (OPEN_HEAD,OPEN_FULL):
            v['headers_download']=k*c.H
            v['authentication_download']=(c.L+len(c.levels)-k+(k if op==OPEN_HEAD else 0))*TAG
            v['data_download']=k*c.n*c.W if op==OPEN_FULL else 0
            v['framing_and_control']=2*FRAME+16
        elif op==READ_SLOTS:
            v['data_download']=sum(len(s) for s in e['slots'])*c.W
            v['authentication_download']=sum(len(witnesses(c.n,tuple(s))) for s in e['slots'])*TAG
            v['framing_and_control']=2*FRAME+16+8*k
        elif op==WRITE:
            kf=len(e['full_depths']);v['headers_upload']=k*c.H;v['data_upload']=kf*c.n*c.W
            v['authentication_upload']=(k+max(ds)+1+(kf*len(local_indices(c.n)) if c.ring else 0))*TAG
            v['framing_and_control']=2*FRAME+24
        else:raise AssertionError('unknown opcode')
    return dict(v)

def invoice(configs:list[Config],events:list[dict])->dict:
    total=Counter();by_stage={};by_tree={};checks=0
    for e in events:
        v=invoice_event(configs[e['tree']],e)
        assert sum(v.values())==e['request_bytes']+e['response_bytes'],(e,v)
        assert all(v[k]==e['components'].get(k,0) for k in COMPONENTS),(e,v)
        total.update(v);by_stage.setdefault(e['stage'],Counter()).update(v);by_tree.setdefault(str(e['tree']),Counter()).update(v);checks+=1
    return dict(events_checked=checks,total=dict(total),total_bytes=sum(total.values()),
                by_stage={k:dict(v) for k,v in by_stage.items()},by_tree={k:dict(v) for k,v in by_tree.items()})

@lru_cache(None)
def probabilities(L:int):
    state=(Fraction(1),Fraction(0),Fraction(0));out=[Fraction(1)]
    for _ in range(L):
        selected=(state[0]+state[1])/2+state[2]
        out.append(selected);state=selected,state[0]/2,state[1]/2
    return tuple(reversed(out))

@dataclass(frozen=True)
class Interval:
    lo:Decimal;hi:Decimal
    @staticmethod
    def exact(x):
        f=x if isinstance(x,Fraction) else Fraction(x)
        with localcontext() as c:
            c.prec=100;c.rounding=ROUND_FLOOR;lo=Decimal(f.numerator)/Decimal(f.denominator)
            c.rounding=ROUND_CEILING;hi=Decimal(f.numerator)/Decimal(f.denominator)
        return Interval(lo,hi)
    def __add__(self,o):
        if not isinstance(o,Interval):o=Interval.exact(o)
        with localcontext() as c:
            c.prec=100;c.rounding=ROUND_FLOOR;lo=self.lo+o.lo
            c.rounding=ROUND_CEILING;hi=self.hi+o.hi
        return Interval(lo,hi)
    __radd__=__add__
    def __mul__(self,o):
        if not isinstance(o,Interval):o=Interval.exact(o)
        assert min(self.lo,o.lo)>=0
        with localcontext() as c:
            c.prec=100;c.rounding=ROUND_FLOOR;lo=self.lo*o.lo
            c.rounding=ROUND_CEILING;hi=self.hi*o.hi
        return Interval(lo,hi)
    __rmul__=__mul__
    def pow(self,n:int):
        ans=Interval.exact(1);base=self
        while n:
            if n&1:ans=ans*base
            n>>=1
            if n:base=base*base
        return ans
    def obj(self):return {'lower':str(self.lo),'upper':str(self.hi)}

@lru_cache(None)
def early_interval(n:int,p:Fraction,S:int)->Interval:
    if p==1:return Interval.exact(max(0,(n-1)//S))
    pm=Interval.exact(1-p).pow(n);res=Interval.exact(0);K=min(n,160)
    for k in range(K+1):
        res=res+pm*max(0,(k-1)//S)
        if k<K:pm=pm*Fraction(n-k,k+1)*(p/(1-p))
    if K<n:
        # For X>K, X <= (X)_(K+1)/K!, hence E[X;X>K]<= (np)^(K+1)/K!.
        tail=Interval.exact((n*p)**(K+1)/math.factorial(K))
        with localcontext() as ctx:
            ctx.prec=100;ctx.rounding=ROUND_CEILING
            res=Interval(res.lo,res.hi+tail.hi)
    return res

@lru_cache(None)
def mean_local_witnesses(n:int,k:int)->Fraction:
    return Fraction(sum(len(witnesses(n,t)) for t in combinations(range(n),k)),math.comb(n,k))

def expected_tree(c:Config)->dict:
    """Periodic full-service-interval expectation; finite trace costs use invoice()."""
    pp=probabilities(c.L) if c.selective else (Fraction(1),)*(c.L+1)
    k=sum(pp[d] for d in c.levels);q=len(c.levels);n=c.L+1
    v={x:Interval.exact(0) for x in COMPONENTS}
    def plus(key,x):v[key]=v[key]+x
    def minus(key,x):
        with localcontext() as ctx:
            ctx.prec=100;ctx.rounding=ROUND_FLOOR;lo=v[key].lo-x.hi
            ctx.rounding=ROUND_CEILING;hi=v[key].hi-x.lo
        v[key]=Interval(lo,hi)
    if not c.ring:
        if c.kind=='path':
            plus('data_download',n*c.Z*c.W);plus('data_upload',n*c.Z*c.W)
            plus('headers_download',n*c.H);plus('headers_upload',n*c.H)
            plus('authentication_download',c.L*TAG);plus('authentication_upload',2*n*TAG)
            plus('framing_and_control',2*FRAME*2+40)
        else:
            plus('data_download',(k+Fraction(n,c.A))*c.Z*c.W);plus('data_upload',Fraction(n,c.A)*c.Z*c.W)
            plus('headers_download',(k+Fraction(n,c.A))*c.H);plus('headers_upload',(k+Fraction(n,c.A))*c.H)
            plus('authentication_download',(2*c.L+1-k+Fraction(c.L,c.A))*TAG)
            plus('authentication_upload',(k+n+Fraction(2*n,c.A))*TAG)
            plus('framing_and_control',(1+Fraction(1,c.A))*(4*FRAME+40))
    else:
        w1=mean_local_witnesses(c.n,1);wZ=mean_local_witnesses(c.n,c.Z);cn=len(local_indices(c.n))
        # Logical headers, one slot per selected bucket, fixed refresh.
        plus('data_download',k*c.W);plus('headers_download',k*c.H);plus('headers_upload',k*c.H)
        plus('authentication_download',(c.L+q+k*w1)*TAG)
        plus('authentication_upload',(k+n)*TAG)
        plus('framing_and_control',6*FRAME+56+8*k)
        # Full scheduled RMW, with a separate authenticated path opening.
        plus('data_download',Fraction(q*c.Z*c.W,c.A));plus('data_upload',Fraction(q*c.n*c.W,c.A))
        plus('headers_download',Fraction(q*c.H,c.A));plus('headers_upload',Fraction(q*c.H,c.A))
        plus('authentication_download',Fraction(1,c.A)*(c.L+q+q*wZ)*TAG)
        plus('authentication_upload',Fraction(1,c.A)*(q*(cn+1)+n)*TAG)
        plus('framing_and_control',Fraction(6*FRAME+56+8*q,c.A))
        for d in c.levels:
            rate=early_interval(c.A*(1<<d),pp[d]/(1<<d),c.S)*Fraction(1,c.A)
            if c.fused:
                plus('data_download',rate*(c.Z-1)*c.W);plus('data_upload',rate*c.n*c.W)
                plus('authentication_download',rate*wZ*TAG);minus('authentication_download',rate*w1*TAG)
                plus('authentication_upload',rate*cn*TAG)
            else:
                plus('data_download',rate*c.Z*c.W);plus('data_upload',rate*c.n*c.W)
                plus('headers_upload',rate*c.H)
                plus('authentication_download',rate*wZ*TAG)
                plus('authentication_upload',rate*(cn+d+2)*TAG)
                plus('framing_and_control',rate*(4*FRAME+48))
    total=sum(v.values(),Interval.exact(0))
    return dict(kind=c.kind,L=c.L,N=c.N,B=c.B,Z=c.Z,A=c.A,S=c.S,R=c.R,header=c.H,tag=TAG,nonce=NONCE,
                components={k:x.obj() for k,x in v.items()},total=total.obj(),cover=str(k),
                local_read_witnesses=str(mean_local_witnesses(c.n,1)) if c.ring else None,
                local_rmw_witnesses=str(mean_local_witnesses(c.n,c.Z)) if c.ring else None)

def sum_rows(rows:list[dict])->dict:
    vals={key:sum((Interval(Decimal(r['components'][key]['lower']),Decimal(r['components'][key]['upper'])) for r in rows),Interval.exact(0)) for key in COMPONENTS}
    return {'components':{k:x.obj() for k,x in vals.items()},'total':sum(vals.values(),Interval.exact(0)).obj()}

def main():
    results={}
    for kind in ['path','deferred','sde','ring','gc_ring','r0']:
        configs=[Config(kind,L,N,4096,S=(5 if kind=='ring' and j==0 else 4 if kind=='ring' else 3),R=192 if j==0 else 144,tree=j) for j,(N,L) in enumerate([(12582912,23),(12288,13)])]
        rows=[expected_tree(c) for c in configs];results[kind]={'layers':rows,**sum_rows(rows)}
    payload={'profile':'SOC2 HMAC-PRF research profile, no XOR/top cache; application framed bytes, not TCP/TLS',
             'expectation':'Complete service-interval periodic expectation; lower/upper outward Decimal enclosures, K=160 factorial-moment tail',
             'geometry':'Two external trees (12582912,L23),(12288,L13); each B4096; terminal position map49152 bytes',
             'table':results}
    out=Path(__file__).resolve().parents[1]/'results/unified_cost_table.json';out.write_text(json.dumps(payload,indent=2))
    for k,v in results.items():print(k,Decimal(v['total']['upper']).quantize(Decimal('.01')),v['components']['framing_and_control']['upper'])
if __name__=='__main__':main()
