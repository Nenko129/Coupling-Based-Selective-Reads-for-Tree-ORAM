"""Authenticated transfer-slot research prototype, built on frozen SOC3 primitives.

One slot removes at most one canonical block and admits at most one new version.
The trusted frontend owns residency and position-map preconditions. No remote
plaintext mirror or direct access to server records is used by this module.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'SOC3_audit_2026-09-15/research_20260914/optimization_v1/src'
sys.path.insert(0,str(SOURCE))
from heterogeneous_oram import (Config,Tree,PRF,Server,Transport,Record,Reject,Overflow,
                            encode,need,gc,node,ui)
from optimized_cost import invoice

class TransferConfig(Config):
    def context(self):
        return encode(b'CACHE-TRANSFER-v1-20260915',super().context())

class TransferTree(Tree):
    def __init__(self,c,p,io):
        super().__init__(c,p,io)
        self.dead=False;self.busy=False;self.births=0;self.removals=0
        self.max_boundary=0;self.max_pending_payload=0
        self.logical_calls=[]

    def transfer(self,remove:int|None,oldleaf:int,admit=None,*,replace=None):
        """admit=(address, fresh unpublished leaf, payload), or replace=(leaf, fn).

        replace transforms the removed record, for ordinary data/map accesses.
        Appends are never an independent unclocked primitive.
        """
        if self.dead:raise Reject('fail-stop transfer tree')
        if self.busy:raise Reject('reentrant transfer')
        self.busy=True
        try:
            need(self.t<(1<<56),'public transfer slot horizon exhausted')
            need(admit is None or replace is None,'two admissions in one slot')
            c=self.c
            need(0<=oldleaf<(1<<c.L),'old leaf bounds')
            need(remove is None or 0<=remove<c.N,'remove address bounds')
            if replace is not None:need(remove is not None,'replace requires target')
            if admit is not None:
                a,l,p=admit
                need(0<=a<c.N and 0<=l<(1<<c.L) and len(p)==c.B,'admission bounds')
            address=c.N if remove is None else remove
            ds=tuple(sorted(gc(self.g,oldleaf,c.L)-({0} if c.rootless else set()))) if c.selective else c.levels
            view=self.open_path(oldleaf,ds,'path' if c.kind=='path' else 'logical')
            if c.kind=='path':
                pool={r.uid:r for r in self.stash.values()}
                for r in self.collect(view,'path'):
                    need(r.uid not in pool,'duplicate path uid');pool[r.uid]=r
                hits=[r for r in pool.values() if r.address==address]
                need(len(hits)<=1,'duplicate target');old=hits[0] if hits else None
                if old is not None:pool.pop(old.uid)
            elif c.ring:
                need(c.fused,'prototype supports fused Ring variant only')
                old=self.fused_logical(view,address)
            else:
                old=self.stash.pop(address,None);changes={}
                for d in ds:
                    b=node(oldleaf,d,c.L);h=view.headers[b]
                    matches=[j for j,x in h.live.items() if x.address==address]
                    need(len(matches)<=1,'duplicate target descriptor')
                    if matches:
                        need(old is None,'duplicate current target')
                        j=matches[0];desc=h.live.pop(j)
                        old=Record(desc.uid,desc.address,desc.leaf,view.plaintexts[b][j])
                    changes[b]=self.prepare(b,h,None)
                self.write(view,changes,'logical')
            if remove is not None:
                need(old is not None and old.leaf==oldleaf,'missing or wrong-leaf target')
                self.removals+=1
            else:need(old is None,'dummy cannot remove a real block')
            if replace is not None:
                leaf,fn=replace;admit=(remove,leaf,fn(old.payload))
            if admit is not None:
                a,l,p=admit
                need(0<=a<c.N and 0<=l<(1<<c.L) and isinstance(p,bytes) and len(p)==c.B,'admission format')
                if c.kind!='path':need(a not in self.stash,'duplicate admission in stash')
                self.uid+=1;self.births+=1;r=Record(self.uid,a,l,p)
                if c.kind=='path':
                    need(not any(x.address==a for x in pool.values()),'duplicate admission in pool')
                    pool[r.uid]=r
                else:self.stash[a]=r
            # Canonical admission occurs before the slot's scheduled service.
            # A cache residency interval is not a backend version lifetime.
            if c.kind=='path':
                self.placement(pool,view,self.t+1,False);self.g+=1
            self.t+=1
            if c.kind!='path' and self.t%c.A==0:self.evict()
            self.max_stash=max(self.max_stash,len(self.stash));self.max_boundary=max(self.max_boundary,len(self.stash))
            if len(self.stash)>c.R:raise Overflow('transfer boundary stash')
            self.logical_calls.append({'slot':self.t,'remove':remove,'admit':None if admit is None else admit[0],
                                       'phase':self.g,'births_this_slot':int(admit is not None)})
            return None if old is None else old.payload
        except Exception:
            self.dead=True;raise
        finally:self.busy=False

class Backend:
    def __init__(self,kind,L,N,B=64,Z=4,A=3,S=4,R=128,tree=0,key=b'T'*64):
        self.c=TransferConfig(kind=kind,L=L,N=N,B=B,Z=Z,A=A,S=S,R=R,tree=tree,compact=True,fused=True)
        self.p=PRF(key);self.server=Server([self.c]);self.io=Transport(self.server)
        self.tree=TransferTree(self.c,self.p,self.io);self.tree.initialize()
    def tick(self,*args,**kwargs):return self.tree.transfer(*args,**kwargs)
    def checkpoint(self):return len(self.io.events),self.p.calls,self.p.decryptions
    def stats(self,start):
        i,calls,decryptions=start;events=self.io.events[i:];bill=invoice([self.c]*(self.c.tree+1),events)
        return {'total_bytes':bill['total_bytes'],'components':bill['total'],'rpc':len(events),
                'prf_calls':self.p.calls-calls,'decryptions':self.p.decryptions-decryptions,
                'max_boundary_stash_blocks':self.tree.max_boundary,'final_phase':self.tree.g,
                'accounting':'serialized SOC3 application frames; excludes TCP/TLS/network latency',
                'peak_memory_measured':False}
