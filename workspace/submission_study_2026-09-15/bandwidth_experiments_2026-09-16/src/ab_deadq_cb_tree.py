"""Transfer tree using authenticated CB/DeadQ levels and actual slot traffic.

Prototype adapter: separate per-level Merkle roots, one serial fail-stop client,
root stored locally for Ring/GC-Ring and absent for R0. No full private position
map lives here. This is not the native AB implementation or a security theorem.
"""
from dataclasses import dataclass
from collections import Counter
import hashlib,random,secrets
from cb_oram import Record,Header,Desc,gc,rev,generation
from ab_dummy_first_policy import eligible_slots
from ab_deadq_authenticated_store import need
from ab_deadq_cb_level import CBLayout,provision_cb
from types import SimpleNamespace


@dataclass(frozen=True)
class TreeConfig:
    kind:str
    L:int
    N:int
    B:int=64
    Z:int=4
    A:int=3
    S:int=4
    Y:int=2
    extra:int=2
    component_cap:int=3
    queue_cap:int=16
    R:int=256
    def __post_init__(self):
        need(self.kind in ('ring','gc_ring','r0') and 1<=self.L<=20,'tree family/height')
        need(0<self.N<=self.A*(1<<(self.L-1)) and self.B>=4,'population/block')
        need(1<=self.Z<=8 and 0<=self.Y<=min(self.Z,self.S) and self.S>=1,'CB parameters')
        need(1<=self.extra<=self.Z+self.S-self.Y and self.queue_cap>=self.extra and self.component_cap>=1,'DeadQ parameters')
    @property
    def rootless(self):return self.kind=='r0'
    @property
    def selective(self):return self.kind!='ring'
    @property
    def n(self):return self.Z+self.S-self.Y


class TrustedRoot:
    """Explicit, bounded trusted root bucket; its payload is resource-accounted."""
    def __init__(self,c,rng):self.c=c;self.rng=rng;self.header=Header();self.payloads={};self.rebuild([],0)
    def rebuild(self,records,gamma):
        need(len(records)<=self.c.Z,'cached root capacity')
        indices=self.rng.sample(range(self.c.n),len(records))
        self.header=Header(gamma=gamma,live={j:Desc(r.uid,r.address,r.leaf,j) for j,r in zip(indices,records)})
        self.payloads={j:r.payload for j,r in zip(indices,records)}
    def records(self):return [Record(d.uid,d.address,d.leaf,self.payloads[j]) for j,d in self.header.live.items()]
    def logical(self,address):
        h=self.header
        if h.count==self.c.S:self.rebuild(self.records(),h.gamma);h=self.header
        j=self.rng.choice(eligible_slots(self.c,h,address));record=None
        if j in h.live:
            d=h.live.pop(j);record=Record(d.uid,d.address,d.leaf,self.payloads.pop(j))
            if d.address!=address:h.green+=1
        h.count+=1;h.used|=1<<j
        return record


class RoutedCBTree:
    def __init__(self,c,seed=None):
        self.c=c;self.t=0;self.g=0;self.uid=0;self.stash={};self.dead=False;self.busy=False
        self.levels={};self.metrics=Counter();self.max_stash=0
        # Default uses private entropy; fixed seeds are explicit test fixtures.
        self.seed_key=secrets.token_bytes(32) if seed is None else hashlib.sha256(b'CB-DeadQ-fixture'+str(seed).encode()).digest()
        def rng_for(label):
            if seed is None:return secrets.SystemRandom()
            return random.Random(int.from_bytes(hashlib.sha256(self.seed_key+label).digest(),'big'))
        self.root=None if c.rootless else TrustedRoot(c,rng_for(b'root'))
        for d in range(1,c.L+1):
            g=CBLayout(1<<d,c.n,c.extra,min(c.component_cap,1<<d),c.queue_cap,c.B+20,
                Z=c.Z,Y=c.Y,address_bound=c.N,leaf_bits=c.L,depth=d)
            key=hashlib.sha256(self.seed_key+b'data'+d.to_bytes(4,'big')).digest()
            level,wire=provision_cb(g,key=key,placement=rng_for(d.to_bytes(4,'big')))
            self.levels[d]=level
            # Wire/server ownership is handed to the external test/transport
            # harness by take_transports(), not consulted by tree operations.
            if d==1:self._initial_transports={}
            self._initial_transports[d]=wire
        self.setup_serialized_client_roots_bytes=32*c.L

    def take_transports(self):
        transports=self._initial_transports;del self._initial_transports
        return transports

    def _insert(self,pool,r):
        need(r.address not in pool and all(x.uid!=r.uid for x in pool.values()),'unique canonical admission')
        pool[r.address]=r

    def _evict(self,pool):
        c=self.c;leaf=rev(self.g%(1<<c.L),c.L);opened={}
        if self.root is not None:
            need(self.root.header.gamma==self.g,'cached root gamma')
            for r in self.root.records():self._insert(pool,r)
        # All path records are available before deepest-first placement.
        for d,level in self.levels.items():
            b=leaf>>(c.L-d);opened[d]=b
            for r in level.open_scheduled(b):self._insert(pool,r)
        chosen={}
        for d in range(c.L,-1,-1):
            if d==0 and c.rootless:continue
            b=leaf>>(c.L-d)
            candidates=[r for r in sorted(pool.values(),key=lambda r:r.uid)
                if r.leaf>>(c.L-d)==b and (not c.selective or d in gc(self.g+1,r.leaf,c.L))][:c.Z]
            for r in candidates:pool.pop(r.address)
            chosen[d]=candidates
        # Stage every level before publishing any client placement state.
        for d,level in self.levels.items():level.stage_scheduled(chosen[d])
        for d,level in self.levels.items():
            event,_=level.commit_cb();self._count(event)
        if self.root is not None:self.root.rebuild(chosen[0],self.g+1)
        self.g+=1

    def _count(self,event):
        self.metrics['level_transactions']+=1
        for e in event['events']:
            if e['operation']=='rebuild':
                self.metrics['scheduled_rebuilds' if e['scheduled'] else 'neutral_rebuilds']+=1
                self.metrics['collateral_buckets']+=e['collateral_buckets']
                self.metrics['expansions']+=e['result']=='expanded'
                self.metrics['maintenance_read_slots']+=sum(len(v) for v in e['maintenance_reads'].values())
            else:self.metrics['logical_consumed_slots']+=1

    def transfer(self,remove,oldleaf,admit=None,*,replace=None):
        need(not self.dead and not self.busy,'ready transfer tree');self.busy=True
        try:
            c=self.c;need(self.t<1<<56 and 0<=oldleaf<1<<c.L,'slot/leaf horizon')
            need(remove is None or 0<=remove<c.N,'target bounds');need(admit is None or replace is None,'single admission')
            need(replace is None or remove is not None,'replace requires target')
            pool=dict(self.stash);old=None if remove is None else pool.pop(remove,None);address=c.N if remove is None else remove
            selected=gc(self.g,oldleaf,c.L) if c.selective else set(range(c.L+1))
            if self.root is not None and 0 in selected:
                need(self.root.header.gamma==self.g,'cached root gamma')
                r=self.root.logical(address)
                if r is not None:
                    if r.address==address:need(old is None,'duplicate cached target');old=r
                    else:self._insert(pool,r);self.metrics['green_promotions']+=1
            for d in sorted(selected-{0}):
                level=self.levels[d];b=oldleaf>>(c.L-d)
                event,result=level.apply_cb('logical',b,address=address);self._count(event)
                if result['target'] is not None:need(old is None,'duplicate remote target');old=result['target']
                if result['green'] is not None:self._insert(pool,result['green']);self.metrics['green_promotions']+=1
            if remove is not None:need(old is not None and old.leaf==oldleaf,'target record/old leaf')
            else:need(old is None,'dummy target')
            if replace is not None:
                leaf,fn=replace;admit=(remove,leaf,fn(old.payload))
            if admit is not None:
                a,l,p=admit;need(0<=a<c.N and 0<=l<1<<c.L and isinstance(p,bytes) and len(p)==c.B,'admission bounds')
                self.uid+=1;self._insert(pool,Record(self.uid,a,l,p))
            if (self.t+1)%c.A==0:self._evict(pool)
            need(len(pool)<=c.R,'completed-boundary stash capacity')
            self.stash=pool;self.t+=1;self.max_stash=max(self.max_stash,len(pool));self.metrics['transfer_slots']+=1
            return None if old is None else old.payload
        except Exception:
            self.dead=True
            for level in self.levels.values():level._abort_cb()
            raise
        finally:self.busy=False
