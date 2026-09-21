#!/usr/bin/env python3
"""Plaintext reference state machines and exact structural/dynamic regressions.
NOT an encrypted end-to-end benchmark. Physical current-record transitions,
Ring dummy consumption, neutral reshuffles, immutable canonical priority, and
an independently recomputed global shadow packing are exercised here.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from functools import lru_cache
from collections import Counter
from pathlib import Path
import random,json

@lru_cache(None)
def rev(x:int,L:int)->int:
    return int(f'{x:0{L}b}'[::-1],2) if L else 0

def node(ell:int,d:int,L:int)->int:return (1<<d)+(ell>>(L-d))
def depth(b:int)->int:return b.bit_length()-1
def lcp(x:int,y:int,L:int)->int:return L-(x^y).bit_length()

@lru_cache(None)
def _mask(g:int,ell:int,L:int)->frozenset[int]:
    x=(g-1-rev(ell,L))% (1<<L); selected={L};q=0
    for d in range(L-1,-1,-1):
        if ((x>>d)&1) or q==2:selected.add(d);q=0
        else:q+=1
    return frozenset(selected)
def mask(g:int,ell:int,L:int)->frozenset[int]:return _mask(g%(1<<L),ell,L)
def generation(g:int,d:int,p:int)->int:
    r=rev(p,d)
    return 0 if g<=r else r+((g-1-r)//(1<<d))*(1<<d)+1

def pinned(g:int,ell:int,L:int)->frozenset[int]:
    return frozenset(d for d in range(1,L+1) if d in mask(generation(g,d,ell>>(L-d)),ell,L))

@dataclass(frozen=True)
class Token:
    uid:int
    address:int
    leaf:int
    value:int
    home:int=-1
    stale:bool=False
    # uid is immutable creation priority; stale status is NEVER a priority key.

class Core:
    def __init__(self,L:int,Z:int,A:int,S:int,kind:str,seed:int):
        self.L,self.Z,self.A,self.S=L,Z,A,S
        self.ring=kind!='sde';self.rootless=kind=='r0';self.g=self.t=0
        self.rng=random.Random(seed);self.stash={};self.tokens={};self.pos={};self.value={}
        self.uid=0;self.trace=[];self.stats=Counter();self.max_stash=0
        n=Z+S if self.ring else Z
        self.slots={b:[None]*n for b in range(1,1<<(L+1)) if not(self.rootless and b==1)}
        self.live={b:set() for b in self.slots};self.used={b:set() for b in self.slots}
        self.generation={b:0 for b in self.slots}
    def readbucket(self,b:int):
        n=len(self.slots[b]);unused=set(range(n))-self.used[b]
        assert self.live[b]<=unused
        real=set(self.live[b]);dummies=sorted(unused-real)
        choose=real|set(self.rng.sample(dummies,self.Z-len(real)))
        assert len(choose)==self.Z
        self.stats['rmw_data_reads']+=self.Z
        return [self.tokens[self.slots[b][j]] for j in sorted(real)]
    def writebucket(self,b:int,tokens:list[Token],gamma:int):
        assert len(tokens)<=self.Z
        n=len(self.slots[b]);v=[x.uid for x in tokens]+[None]*(n-len(tokens))
        self.rng.shuffle(v);self.slots[b]=v;self.live[b]={j for j,x in enumerate(v) if x is not None}
        self.used[b]=set();self.generation[b]=gamma;self.stats['data_writes']+=n
    def neutral(self,b:int):
        before=tuple(sorted(self.slots[b][j] for j in self.live[b]));ga=self.generation[b]
        records=self.readbucket(b);self.writebucket(b,records,ga)
        assert before==tuple(sorted(self.slots[b][j] for j in self.live[b]))
        assert self.generation[b]==ga;self.stats['neutral_reshuffles']+=1
    def access(self,address:int,value:int|None,newleaf:int,initialleaf:int,*,lookup_leaf:int|None=None,transform=None):
        self.t+=1;self.uid+=1
        if lookup_leaf is None:oldleaf=self.pos.setdefault(address,initialleaf)
        else:
            # In recursive tests, the private oracle map is used ONLY for assertions,
            # never to choose the visible old path.
            oldleaf=lookup_leaf
            assert oldleaf==self.pos.get(address,initialleaf)
            self.pos.setdefault(address,initialleaf)
        ms=pinned(self.g,oldleaf,self.L) if self.ring else mask(self.g,oldleaf,self.L)
        if self.ring and not self.rootless:ms=mask(self.g,oldleaf,self.L)
        found=[x for x in self.stash.values() if x.address==address]
        assert len(found)<=1
        old=found[0] if found else None
        for d in sorted(ms):
            b=node(oldleaf,d,self.L)
            if self.ring:
                if len(self.used[b])==self.S:self.neutral(b)
                assert len(self.used[b])<self.S
            matches=[j for j in self.live[b] if self.tokens[self.slots[b][j]].address==address]
            assert len(matches)<=1
            if matches:
                assert old is None
                j=matches[0];old=self.tokens[self.slots[b][j]];self.live[b].remove(j)
            elif self.ring:
                candidates=[j for j,u in enumerate(self.slots[b]) if u is None and j not in self.used[b]]
                assert candidates;j=self.rng.choice(candidates)
            if self.ring:self.used[b].add(j)
            self.stats['logical_data_reads']+=1 if self.ring else self.Z
            self.stats['logical_header_refreshes']+=1
        previous=old.value if old else 0
        assert previous==self.value.get(address,0)
        if old and old.uid in self.stash:del self.stash[old.uid]
        if address in self.value:assert old is not None
        newvalue=transform(previous) if transform is not None else (previous if value is None else value)
        token=Token(self.uid,address,newleaf,newvalue);self.tokens[token.uid]=token
        self.stash[token.uid]=token;self.pos[address]=newleaf;self.value[address]=newvalue
        if self.t%self.A==0:self.evict()
        self.check();self.max_stash=max(self.max_stash,len(self.stash))
        return previous
    def evict(self):
        ep=rev(self.g%(1<<self.L),self.L);levels=range(1 if self.rootless else 0,self.L+1)
        pool=dict(self.stash)
        for d in levels:
            b=node(ep,d,self.L)
            if self.ring: records=self.readbucket(b)
            else:
                records=[self.tokens[self.slots[b][j]] for j in self.live[b]]
                self.stats['rmw_data_reads']+=self.Z
            for tok in records:assert tok.uid not in pool;pool[tok.uid]=tok
        ng=self.g+1
        for d in reversed(list(levels)):
            b=node(ep,d,self.L)
            legal=[tok for tok in sorted(pool.values(),key=lambda x:x.uid)
                   if node(tok.leaf,d,self.L)==b and d in mask(ng,tok.leaf,self.L)]
            chosen=legal[:self.Z]
            for tok in chosen:del pool[tok.uid]
            self.writebucket(b,chosen,ng)
        self.stash=pool;self.g=ng
    def check(self):
        seen={x.address:x.uid for x in self.stash.values()}
        assert len(seen)==len(self.stash)
        for b in self.slots:
            d=depth(b)
            for j in self.live[b]:
                tok=self.tokens[self.slots[b][j]]
                assert tok.address not in seen;seen[tok.address]=tok.uid
                assert node(tok.leaf,d,self.L)==b and d in mask(self.g,tok.leaf,self.L)
                if self.ring:assert d in mask(self.generation[b],tok.leaf,self.L)
                assert self.pos[tok.address]==tok.leaf and self.value[tok.address]==tok.value
            if self.ring:
                assert len(self.used[b])<=self.S and not(self.live[b]&self.used[b])
                assert self.generation[b]==generation(self.g,d,b-(1<<d))
        assert set(seen)==set(self.value)
    def view(self):
        return (tuple((b,tuple(sorted(self.slots[b][j] for j in self.live[b]))) for b in sorted(self.slots)),tuple(sorted(self.stash)))

# Separate proof-only shadow with global home update and immutable priorities.
def pack(tokens:dict[int,Token],g:int,L:int,Z:int,rootless:bool):
    pending={b:[] for b in range(1,1<<(L+1))};stash=[]
    for x in tokens.values():
        if x.home<0:stash.append(x.uid)
        else:pending[node(x.leaf,x.home,L)].append(x.uid)
    out={b:[] for b in pending}
    for b in range((1<<(L+1))-1,0,-1):
        d=depth(b);eligible=[];bypass=[]
        for uid in sorted(pending[b]):
            x=tokens[uid]
            (eligible if d in mask(g,x.leaf,L) else bypass).append(uid)
        cap=0 if rootless and b==1 else Z
        out[b]=eligible[:cap];overflow=eligible[cap:]+bypass
        if b>1:pending[b//2].extend(overflow)
        else:stash.extend(overflow)
    return {b:tuple(sorted(v)) for b,v in out.items()},tuple(sorted(stash))

class Shadow:
    def __init__(self,L,Z,A,rootless):
        self.L,self.Z,self.A,self.rootless=L,Z,A,rootless;self.g=self.t=0
        self.tokens={};self.current={};self.tree,self.stash=pack({},0,L,Z,rootless)
        self.checks=0
    def access(self,uid,address,leaf,value):
        self.t+=1
        if address in self.current:
            old=self.current[address];self.tokens[old]=replace(self.tokens[old],stale=True)
        self.current[address]=uid;self.tokens[uid]=Token(uid,address,leaf,value)
        self.stash=tuple(sorted(self.stash+(uid,)))
        assert (self.tree,self.stash)==pack(self.tokens,self.g,self.L,self.Z,self.rootless);self.checks+=1
        if self.t%self.A:self.checks+=0;return
        ep=rev(self.g%(1<<self.L),self.L)
        # Ring proof shadow deletes stale versions only at their mapped leaf service.
        deleted={u for u,x in self.tokens.items() if x.stale and x.leaf==ep}
        self.tokens={u:replace(x,home=max(x.home,lcp(x.leaf,ep,self.L))) for u,x in self.tokens.items() if u not in deleted}
        path=[node(ep,d,self.L) for d in range(self.L+1)]
        pool={u for u in self.stash if u not in deleted}
        tree=dict(self.tree)
        for b in path:pool.update(u for u in tree[b] if u not in deleted);tree[b]=()
        ng=self.g+1
        for b in reversed(path):
            d=depth(b);cap=0 if self.rootless and b==1 else self.Z
            legal=[u for u in sorted(pool) if node(self.tokens[u].leaf,d,self.L)==b and d in mask(ng,self.tokens[u].leaf,self.L)]
            chosen=legal[:cap];tree[b]=tuple(chosen);pool.difference_update(chosen)
        self.tree,self.stash,self.g=tree,tuple(sorted(pool)),ng
        assert (tree,self.stash)==pack(self.tokens,self.g,self.L,self.Z,self.rootless)
        self.checks+=1

def run():
    pc=loc=0
    for L in range(1,9):
        for g in range(2*(1<<L)+1):
            for ell in range(1<<L):
                assert pinned(g,ell,L)==mask(g,ell,L)-{0};pc+=1
                z=lcp(ell,rev(g%(1<<L),L),L)
                assert {d for d in mask(g,ell,L) if d>z}=={d for d in mask(g+1,ell,L) if d>z};loc+=1
    operations=checks=0;out=[]
    for L in [2,3,4,5,6]:
        for Z in [1,2,4]:
            for seed in range(3):
                r=random.Random(1000*L+100*Z+seed);N=3*(1<<(L-1));steps=600
                cores=[Core(L,Z,3,3,k,seed+100*i) for i,k in enumerate(['sde','ring','r0'])]
                shadows=[Shadow(L,Z,3,False),Shadow(L,Z,3,True)]
                for t in range(steps):
                    # Include sequential load, hot repeats, round robin, and random requests.
                    address=t if t<N else (0 if t%9<3 else ((t-N)%N if t%9<6 else r.randrange(N)))
                    val=r.randrange(1<<30) if t<N or t%4==0 else None
                    leaf=r.randrange(1<<L);initial=r.randrange(1<<L)
                    ans=[c.access(address,val,leaf,initial) for c in cores]
                    assert ans[0]==ans[1]==ans[2]
                    assert cores[0].view()==cores[1].view()
                    for sh,c in [(shadows[0],cores[0]),(shadows[1],cores[2])]:
                        sh.access(c.uid,address,leaf,c.value[address])
                        assert len(c.stash)<=len(sh.stash)
                    operations+=3;checks+=1
                out.append(dict(L=L,Z=Z,seed=seed,steps=steps,max_stash=[c.max_stash for c in cores],neutral_reshuffles=[c.stats['neutral_reshuffles'] for c in cores]))
                checks+=sum(sh.checks for sh in shadows)
    result=dict(pinned_current_mask_equalities=pc,deletion_locality_equalities=loc,
        logical_operations=operations,dynamic_checks=checks,configurations=len(out),runs=out,
        scope='Plaintext unbounded-stash driver; checks functionality and coupled state transitions, not cryptographic probabilities or a full encrypted/network implementation.')
    (Path(__file__).resolve().parent/'core_state_results.json').write_text(json.dumps(result,indent=2))
    print({k:v for k,v in result.items() if k!='runs'})
if __name__=='__main__':run()
