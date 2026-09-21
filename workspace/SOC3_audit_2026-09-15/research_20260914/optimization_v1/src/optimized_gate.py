"""Separate research gate for the SOC3 variant and two explicit m=2 cores."""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext,ROUND_CEILING
import csv,json,hashlib,math,sys
from optimized_oram import Config,RecursiveORAM,Reject
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parents[1]/'selective_oram_final_chain_2026-09-11'
sys.path.append(str(BASE/'src'))
from certified_driver import CertificateBank

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def upper(v):
    with localcontext() as ctx:
        ctx.prec=60;ctx.rounding=ROUND_CEILING
        return str(Decimal(v.numerator)/Decimal(v.denominator))
def require(v,m):
    if not v:raise ValueError(m)

class OptimizedBank:
    def __init__(self,verify_variant=True):
        self.original=CertificateBank();self.grids={(4,3):self.original.values}
        modes={}
        for mode in ('up','next'):
            prefix=ROOT/f'numerics/z7a6_{mode}_c280_h24'
            meta=json.loads(prefix.with_name(prefix.name+'_meta.json').read_text())
            require((meta['Z'],meta['rate'],meta['height'],meta['cap'],meta['poisson_cutoff'])==(7,'3',24,280,128),'numeric profile')
            require(meta['arithmetic']==mode and meta['rounding_self_test'] and not meta['renormalized'] and not meta['positive_states_discarded'],'numeric policy')
            require(meta['model']=='m2-independent-Poisson-ghost','numeric recurrence model')
            require(meta['poisson_zero_upper_hex']==json.loads((ROOT/'numerics/poisson_seed.json').read_text())['upper_hex'],'numeric seed binding')
            vals={}
            for row in csv.DictReader(prefix.with_suffix('.csv').open()):
                h,r=int(row['height']),int(row['threshold'])
                known=F.from_float(float.fromhex(row['known_upper_hex']));unknown=F.from_float(float.fromhex(row['unknown_moment_hex']))
                value=F.from_float(float.fromhex(row['total_upper_hex']))
                require(known>=0 and unknown>=0 and value>=known+unknown,'invalid outward enclosure');require((h,r) not in vals,'duplicate numeric point')
                vals[h,r]=value
            require(set(vals)=={(h,r) for h in range(1,25) for r in range(281)},'incomplete grid')
            for h in range(1,25):
                require(all(vals[h,r]>=vals[h,r+1] for r in range(280)),'nonmonotone stop loss')
            modes[mode]=vals
        self.grids[7,6]={p:max(v[p] for v in modes.values()) for p in modes['up']}
        if verify_variant:
            contract=json.loads((ROOT/'variant_contract.json').read_text())
            require(contract['scope_id']=='SOC3-AUDIT-m2-Z4A3-Z7A6-2026-09-15','contract identity')
            for name,digest in contract['artifact_sha256'].items():require(sha(ROOT/name)==digest,'variant artifact changed: '+name)
        self.variant_hashes_checked=verify_variant
    @staticmethod
    def offset(c):return c.A-1+(c.Z if c.rootless else 0)
    def epsilon(self,c):
        if c.R>=c.N:return F(0)
        key=c.L+1,c.R-self.offset(c)
        require(key in self.grids[c.Z,c.A],'outside numeric grid')
        return self.grids[c.Z,c.A][key]
    def plan(self,cs,online,limit=F(1,1<<130)):
        require(bool(cs) and online>=0,'operation horizon')
        subtotal=0;total=F(0);points=[];q=[]
        for j,c in enumerate(cs):
            require(c.kind in ('sde','r0') and (c.Z,c.A) in self.grids,'unsupported core')
            require((c.Z,c.A)!=(7,6) or c.kind=='r0','Z7A6 currently R0 only')
            require(c.compact and c.fused,'wrong serializer/fusion profile')
            require(c.B<=4096 and c.n<=13 and c.L<=30 and c.tree==j,'primitive/geometry profile')
            require(c.H==76+32*((8+30*c.Z+31)//32),'header profile')
            if j+1<len(cs):require(cs[j+1].N==(c.N+cs[j+1].B//4-1)//(cs[j+1].B//4),'recursive geometry')
            subtotal+=c.N;Q=online+subtotal;q.append(Q);eps=self.epsilon(c);total+=Q*eps
            points.append(dict(tree=j,kind=c.kind,Z=c.Z,A=c.A,S=c.S,L=c.L,N=c.N,B=c.B,R=c.R,
                               offset=self.offset(c),height=c.L+1,threshold=c.R-self.offset(c),Q=Q,fixed_time_upper=upper(eps),
                               rule='deterministic current count <= N' if c.R>=c.N else 'certified stop-loss grid',
                               certified_height_max=None if c.R>=c.N else (24 if (c.Z,c.A)==(7,6) else 31)))
        require(total<=limit,'stash lifetime target')
        # Syntactic bound proven in the variant note for Z<=7,n<=13,B<=4096,L<=30.
        calls=(1<<22)*sum(q)+(1<<13)*sum((1<<(c.L+1))-1 for c in cs)+2*sum(c.N for c in cs)
        require(calls<1<<96,'primitive counter lifetime')
        epsF=F(1,1<<132);bias=math.factorial(max(c.n for c in cs))
        advantage=2*epsF+F(calls*calls,1<<511)+2*total+F(calls*bias,1<<513)
        require(advantage<F(1,1<<128),'conditional ORAM target')
        return dict(points=points,online_horizon=online,stash_lifetime_upper=upper(total),stash_limit=upper(limit),
                    primitive_calls_upper=calls,conditional_advantage_upper=upper(advantage),passes_2m128=True,
                    persistent_payload_plus_terminal=sum(c.R*c.B for c in cs)+4*cs[-1].N,
                    hashes_checked=self.variant_hashes_checked,
                    scope='Research-level reduction, numerical enclosure and serialized execution; fixed histories independent of ORAM coins; one serial nonrollback fail-stop client; variable-input PRF hybrid assumption <=2^-132 at this call bound; no crash/concurrent/local-timing theorem.')

class OptimizedCertifiedORAM(RecursiveORAM):
    def __init__(self,cs,key,online,bank=None):
        self.approval=(bank or OptimizedBank()).plan(cs,online)
        super().__init__(cs,key);self.limits=[x['Q'] for x in self.approval['points']]
    def access(self,a,value=None,*,start_layer=0):
        if any(self.trees[j].t>=self.limits[j] for j in range(start_layer,len(self.trees))):raise Reject('public certified horizon exhausted')
        return super().access(a,value,start_layer=start_layer)
