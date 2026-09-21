#!/usr/bin/env python3
"""Certificate-gated entry point: exact dyadic budgets, no rounded-bit decisions.
The gate binds an audited implementation and an explicit theorem scope; hashes
are reproducibility identifiers, not a substitute for the reduction proof.
"""
from __future__ import annotations
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext,ROUND_CEILING
import csv,json,hashlib
from integrated_oram import Config,RecursiveORAM,Reject
ROOT=Path(__file__).resolve().parents[1]

class GateError(ValueError):pass

def require(v,m):
    if not v:raise GateError(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def upper_decimal(v:F):
    with localcontext() as c:
        c.prec=50;c.rounding=ROUND_CEILING
        return str(Decimal(v.numerator)/Decimal(v.denominator))

class CertificateBank:
    def __init__(self,root:Path=ROOT,check_hashes=True):
        self.root=root;self.contract=json.loads((root/'theorem_contract.json').read_text())
        ct=self.contract
        require(ct['ghost']['recurrence']=='((sum(R)+L[2]+P-4)_+,L[0],L[1])','different ghost')
        require(ct['ghost']['bucket_levels']=='L+1' and ct['ghost']['rate']=='3/2','levels/rate')
        require(ct['protocol']['Z']==4 and ct['protocol']['A']==3 and ct['protocol']['m']==2,'core parameters')
        require(ct['protocol']['priority']=='immutable version_serial','tie break')
        require(ct['protocol']['shadow_delete']=='first mapped-leaf service after invalidation','shadow semantics')
        require(ct['protocol']['neutral_reshuffle_fills_from_stash'] is False,'nonneutral reshuffle')
        require(ct['offsets']=={'sde':2,'r0':6},'actual/ghost offsets')
        au=ct['authentication']
        require((au['header_Z4_bytes'],au['nonce_bytes'],au['tag_bytes'],au['frame_header_bytes'],au['server_computes_keyed_tags'])==(364,16,64,36,False),'authentication/serializer profile')
        if check_hashes:
            for name,digest in ct['artifact_sha256'].items():require(sha(root/name)==digest,'artifact changed: '+name)
        self.values={};self.mode_values={}
        for mode in ('up','next'):
            prefix=root/f'certificates/ghost_{mode}_c280_h31'
            meta=json.loads(prefix.with_name(prefix.name+'_meta.json').read_text())
            require((meta['rate'],meta['Z'],meta['height'],meta['cap'],meta['poisson_cutoff'])==('3/2',4,31,280,128),'certificate parameters')
            require(meta['arithmetic']==mode and not meta['renormalized'] and not meta['positive_states_discarded'],'arithmetic policy')
            vals={}
            with prefix.with_suffix('.csv').open() as f:
                for row in csv.DictReader(f):
                    h,r=int(row['height']),int(row['threshold'])
                    known=F.from_float(float.fromhex(row['known_upper_hex']));unknown=F.from_float(float.fromhex(row['unknown_moment_hex']));upper=F.from_float(float.fromhex(row['total_upper_hex']))
                    require(upper>=known+unknown>=0,'bad enclosure addition')
                    require((h,r) not in vals,'duplicate point');vals[h,r]=upper
            require(len(vals)==31*281,'incomplete point grid')
            for h in range(1,32):
                for r in range(280):require(vals[h,r]>=vals[h,r+1],'nonmonotone stop loss')
            self.mode_values[mode]=vals
        self.values={key:max(self.mode_values[m][key] for m in ('up','next')) for key in self.mode_values['up']}
        require(self.values[24,186]<=F(1,1<<194),'lifetime target failed')
    def plan(self,configs:list[Config],max_online:int,stash_bits:int=130):
        require(bool(configs) and max_online>=0,'plan horizon')
        q=[];subtotal=0;total=F();points=[]
        for j,c in enumerate(configs):
            require(c.kind in ('sde','r0') and (c.Z,c.A)==(4,3),'unsupported certified core')
            require(c.B<=4096 and c.n<=9 and c.L<=30,'primitive-call profile limit')
            require(c.tree==j,'tree domain')
            if j+1<len(configs):require(configs[j+1].N==(c.N+configs[j+1].B//4-1)//(configs[j+1].B//4),'position-map geometry')
            subtotal+=c.N;Q=max_online+subtotal;q.append(Q)
            r=c.R-self.contract['offsets'][c.kind];h=c.L+1
            if c.R>=c.N:epsilon=F();rule='deterministic current-record count <= N'
            else:
                require((h,r) in self.values,'outside certificate grid')
                epsilon=self.values[h,r];rule='independent scalar stop-loss enclosure'
            total+=Q*epsilon
            points.append(dict(tree=j,kind=c.kind,L=c.L,bucket_levels=h,N=c.N,R=c.R,ghost_threshold=r,
                               operations_including_setup=Q,fixed_time_upper=upper_decimal(epsilon),rule=rule))
        require(total<=F(1,1<<stash_bits),'lifetime budget exceeds target')
        # Conservative syntactic call bound for B<=4096,L<=30,Z4,slots<=9.
        primitive_bound=(1<<18)*sum(q)+(1<<11)*sum((1<<(c.L+1))-1 for c in configs)+2*sum(c.N for c in configs)
        require(primitive_bound<1<<96,'primitive counter lifetime')
        epsF=F(1,1<<132)
        crypto=2*epsF+F(primitive_bound**2,1<<511)+2*total+F(primitive_bound*362880,1<<513)
        return dict(points=points,max_online_operations=max_online,total_stash_lifetime_upper=upper_decimal(total),
                    stash_target_bits=stash_bits,primitive_calls_upper_integer=primitive_bound,
                    conditional_ORAM_advantage_upper=upper_decimal(crypto),passes_2m128=crypto<F(1,1<<128),
                    PRF_assumption='Each real-to-ideal PRF hybrid advantage <= 2^-132 at the stated time, query count and input lengths',
                    terminal_map_bytes=4*configs[-1].N,scope=self.contract['theorem_scope'])

class CertifiedRecursiveORAM(RecursiveORAM):
    def __init__(self,configs:list[Config],key:bytes,max_online:int,bank:CertificateBank|None=None,stash_bits=130):
        bank=bank or CertificateBank();self.approval=bank.plan(configs,max_online,stash_bits)
        super().__init__(configs,key)
        self.operation_limits=[p['operations_including_setup'] for p in self.approval['points']]
    def access(self,a:int,value:bytes|None=None,*,start_layer:int=0):
        if any(self.trees[j].t>=self.operation_limits[j] for j in range(start_layer,len(self.trees))):raise Reject('public certified horizon exhausted')
        return super().access(a,value,start_layer=start_layer)


def main():
    bank=CertificateBank();N0,N1=12582912,12288;online=(1<<64)-N0-N1;out={}
    for kind in ('sde','r0'):
        configs=[Config(kind,23,N0,tree=0,R=192),Config(kind,13,N1,tree=1,R=144)]
        out[kind]=bank.plan(configs,online)
    (ROOT/'results/certificate_bindings.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
