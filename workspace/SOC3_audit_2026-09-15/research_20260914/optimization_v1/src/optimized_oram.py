#!/usr/bin/env python3
"""Serialized, authenticated, recursive Selective ORAM reference implementation.

This is a research reference, not a production cryptographic suite. HMAC-SHA-512
instantiates the explicitly assumed variable-input PRF. No plaintext server
mirror or nonterminal position map is used by the execution path. The untrusted
server stores bytes and client-created tags. In-process transport serializes and
parses exactly the frames charged by the ledger; it is not a TCP/TLS benchmark.
Single serial client; nonrollback private state; fail-stop, not crash recovery.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
import hashlib, hmac, math, struct
from typing import Callable

TAG=64; NONCE=16; PUBLIC=60; FRAME=36
OPEN_FULL=1; OPEN_HEAD=2; READ_SLOTS=3; WRITE=4; INIT=5
ZERO=bytes(TAG)
KINDS={'path','deferred','sde','ring','gc_ring','r0'}

class Reject(Exception): pass
class Overflow(Reject): pass

def need(ok:bool,message:str)->None:
    if not ok: raise Reject(message)
def ui(x:int,n:int=16)->bytes: return x.to_bytes(n,'big')
def encode(*parts:bytes)->bytes: return b''.join(ui(len(p),8)+p for p in parts)

def frame(op:int,tree:int,seq:int,body:bytes,response=False)->bytes:
    return b'SOC3'+bytes([3,op])+ui(int(response),2)+ui(tree,4)+ui(seq)+ui(len(body),8)+body

def parse_frame(raw:bytes):
    need(len(raw)>=FRAME and raw[:4]==b'SOC3' and raw[4]==3,'frame format')
    op=raw[5];flags=int.from_bytes(raw[6:8],'big');tree=int.from_bytes(raw[8:12],'big')
    seq=int.from_bytes(raw[12:28],'big');length=int.from_bytes(raw[28:36],'big')
    need(flags in (0,1) and len(raw)==FRAME+length,'frame length/flags')
    return op,tree,seq,flags,raw[FRAME:]

class Cursor:
    def __init__(self,b:bytes): self.b=b;self.p=0
    def take(self,n:int)->bytes:
        need(n>=0 and self.p+n<=len(self.b),'short body');r=self.b[self.p:self.p+n];self.p+=n;return r
    def uint(self,n:int=8)->int: return int.from_bytes(self.take(n),'big')
    def end(self): need(self.p==len(self.b),'surplus body')

@lru_cache(None)
def rev(x:int,L:int)->int:
    ans=0
    for _ in range(L): ans=(ans<<1)|(x&1);x>>=1
    return ans

def node(leaf:int,d:int,L:int)->int: return (1<<d)+(leaf>>(L-d))
def depth(b:int)->int: return b.bit_length()-1
def lcp(a:int,b:int,L:int)->int:return L-(a^b).bit_length()
@lru_cache(None)
def _gc(g:int,leaf:int,L:int)->frozenset[int]:
    x=(g-1-rev(leaf,L))%(1<<L);out={L};q=0
    for d in range(L-1,-1,-1):
        if (x>>d)&1 or q==2:out.add(d);q=0
        else:q+=1
    return frozenset(out)
def gc(g:int,leaf:int,L:int):return _gc(g%(1<<L),leaf,L)
def generation(g:int,d:int,prefix:int)->int:
    r=rev(prefix,d)
    return 0 if g<=r else r+((g-1-r)//(1<<d))*(1<<d)+1

def bitmap(indices)->int:return sum(1<<i for i in indices)
def from_bitmap(v:int,n:int)->tuple[int,...]:
    need(0<=v<(1<<n),'bitmap outside layout')
    return tuple(i for i in range(n) if (v>>i)&1)
def factorial_decode(rank:int,n:int)->list[int]:
    pool=list(range(n));out=[]
    for k in range(n,0,-1):
        f=math.factorial(k-1);j,rank=divmod(rank,f);out.append(pool.pop(j))
    return out

def choose_rank(items:list[int],k:int,rank:int)->tuple[int,...]:
    """Lexicographic combinatorial unranking, no rejection loop."""
    need(0<=k<=len(items),'subset capacity')
    out=[];start=0
    for left in range(k,0,-1):
        for j in range(start,len(items)-left+1):
            count=math.comb(len(items)-j-1,left-1)
            if rank<count:out.append(items[j]);start=j+1;break
            rank-=count
    return tuple(out)

@dataclass(frozen=True)
class Config:
    kind:str; L:int; N:int; B:int=4096; Z:int=4; A:int=3; S:int=3; R:int=192; tree:int=0; compact:bool=True; fused:bool=True
    def __post_init__(self):
        if self.kind not in KINDS or not(1<=self.L<=30 and 1<=self.Z<=8 and self.A>=1):raise ValueError('unsupported configuration')
        if self.N<1 or self.N>self.A*(1<<(self.L-1)) or self.B<4 or self.B%4:raise ValueError('N/geometry/block size')
        if self.n>64 or self.R<0 or (self.ring and self.S<1):raise ValueError('slots/stash/dummies')
    @property
    def ring(self):return self.kind in {'ring','gc_ring','r0'}
    @property
    def rootless(self):return self.kind=='r0'
    @property
    def selective(self):return self.kind in {'sde','gc_ring','r0'}
    @property
    def constrained(self):return self.selective
    @property
    def n(self):return self.Z+self.S if self.ring else self.Z
    @property
    def levels(self):return tuple(range(1 if self.rootless else 0,self.L+1))
    @property
    def secret(self):return ((8+(30 if self.compact else 64)*self.Z+31)//32)*32
    @property
    def H(self):return PUBLIC+NONCE+self.secret
    @property
    def W(self):return self.B+NONCE
    def context(self):
        return encode(b'Selective-ORAM-optimization-v3',self.kind.encode(),*[ui(v,8) for v in (self.tree,self.L,self.N,self.B,self.Z,self.A,self.S,self.R,int(self.compact),int(self.fused))])

class PRF:
    def __init__(self,key:bytes):
        if len(key)!=64:raise ValueError('64-byte research-profile key')
        self.key=key;self.calls=0;self.nonces=0;self.samples=0;self.decryptions=0;self.max_input=0
    def F(self,domain:bytes,ctx:bytes,*parts:bytes)->bytes:
        if self.calls>=1<<96:raise Overflow('public primitive budget')
        self.calls+=1;data=encode(domain,ctx,*parts);self.max_input=max(self.max_input,len(data))
        return hmac.new(self.key,data,hashlib.sha512).digest()
    def draw(self,ctx:bytes,event:bytes)->int:
        n=self.samples;self.samples+=1
        return int.from_bytes(self.F(b'SAMPLE',ctx,ui(n),event),'big')
    def initial(self,ctx:bytes,address:int,L:int)->int:
        return int.from_bytes(self.F(b'INITIAL_LEAF',ctx,ui(address)),'big')&((1<<L)-1)
    def stream(self,ctx:bytes,oid:bytes,aad:bytes,nonce:bytes,n:int)->bytes:
        return b''.join(self.F(b'STREAM',ctx,oid,aad,nonce,ui(j,8)) for j in range((n+63)//64))[:n]
    def seal(self,ctx:bytes,oid:bytes,aad:bytes,plain:bytes)->bytes:
        if self.nonces>=1<<128:raise Overflow('nonce capacity')
        nonce=ui(self.nonces);self.nonces+=1
        return nonce+bytes(a^b for a,b in zip(plain,self.stream(ctx,oid,aad,nonce,len(plain))))
    def decrypt(self,ctx:bytes,oid:bytes,aad:bytes,ct:bytes)->bytes:
        need(len(ct)>=NONCE,'ciphertext length');self.decryptions+=1
        return bytes(a^b for a,b in zip(ct[NONCE:],self.stream(ctx,oid,aad,ct[:NONCE],len(ct)-NONCE)))

@dataclass(frozen=True)
class Record:
    uid:int; address:int; leaf:int; payload:bytes
@dataclass(frozen=True)
class Desc:
    uid:int; address:int; leaf:int; slot:int
@dataclass
class Header:
    gamma:int=0; w:int=0; v:int=0; count:int=0; used:int=0
    live:dict[int,Desc]=field(default_factory=dict) # descriptors indexed by physical slot, private
    def public(self)->bytes:
        return ui(self.gamma)+ui(self.w)+ui(self.v)+ui(self.count,4)+ui(self.used,8)
    def secret_bytes(self,c:Config)->bytes:
        ds=[self.live[j] for j in sorted(self.live)]
        need(len(ds)<=c.Z,'header capacity')
        # Active bitmap indexes the fixed Z descriptor array, not physical slots.
        raw=ui((1<<len(ds))-1,8)
        for d in ds:
            raw+=ui(d.uid)+ui(d.address,8)+ui(d.leaf,4)+ui(d.slot,2)+(bytes(34) if not c.compact else b'')
        raw+=bytes((30 if c.compact else 64)*(c.Z-len(ds)))
        return raw+bytes(c.secret-len(raw))
    @classmethod
    def decode(cls,c:Config,pub:bytes,plain:bytes):
        need(len(pub)==PUBLIC and len(plain)==c.secret,'header size')
        q=Cursor(pub);h=cls(q.uint(16),q.uint(16),q.uint(16),q.uint(4),q.uint(8));q.end()
        r=Cursor(plain);livebits=r.uint(8);need(livebits<(1<<c.Z),'descriptor bitmap')
        for i in range(c.Z):
            d=r.take(30 if c.compact else 64)
            if (livebits>>i)&1:
                uid=int.from_bytes(d[:16],'big');a=int.from_bytes(d[16:24],'big');leaf=int.from_bytes(d[24:28],'big');slot=int.from_bytes(d[28:30],'big')
                need(uid>0 and a<c.N and leaf<(1<<c.L) and slot<c.n and slot not in h.live,'descriptor invariant')
                h.live[slot]=Desc(uid,a,leaf,slot)
        need(len({d.address for d in h.live.values()})==len(h.live),'duplicate descriptor address')
        need(h.used<(1<<c.n),'used bitmap')
        if c.ring:need(h.count==h.used.bit_count()<=c.S and not(any(h.used>>j&1 for j in h.live)),'Ring count/used/live')
        else:need(h.count==0 and h.used==0,'SDE public reserved fields')
        return h

@lru_cache(None)
def local_indices(n:int)->tuple[int,...]:
    N=1<<(n-1).bit_length()
    return tuple(p for p in range(1,2*N) if local_start(p,N)<n)
def local_start(p:int,N:int)->int:
    lev=p.bit_length()-1;return (p-(1<<lev))*(N>>lev)
@lru_cache(None)
def witnesses(n:int,indices:tuple[int,...])->tuple[int,...]:
    N=1<<(n-1).bit_length();active={N+i for i in indices};w=set()
    need(bool(active) and all(0<=i<n for i in indices),'local opening set')
    while active!={1}:
        for p in active:
            if (p^1) not in active and local_start(p^1,N)<n:w.add(p^1)
        active={p//2 for p in active}
    return tuple(sorted(w))

def local_make(c:Config,P:PRF,b:int,slots:list[bytes])->dict[int,bytes]:
    N=1<<(c.n-1).bit_length();tags={N+j:P.F(b'SLOT',c.context(),ui(b,8),ui(j,2),x) for j,x in enumerate(slots)}
    for p in range(N-1,0,-1):
        if local_start(p,N)<c.n:tags[p]=P.F(b'LOCAL_NODE',c.context(),ui(b,8),ui(p,8),tags.get(2*p,ZERO),tags.get(2*p+1,ZERO))
    return tags

def local_open_root(c:Config,P:PRF,b:int,slots:dict[int,bytes],proof:dict[int,bytes])->bytes:
    N=1<<(c.n-1).bit_length();inds=tuple(sorted(slots))
    need(set(proof)==set(witnesses(c.n,inds)),'local proof shape')
    tags=dict(proof);active={N+j for j in inds}
    for j,ct in slots.items():
        need(len(ct)==c.W,'slot length');tags[N+j]=P.F(b'SLOT',c.context(),ui(b,8),ui(j,2),ct)
    while active!={1}:
        parents={p//2 for p in active}
        for p in parents:
            for child in (2*p,2*p+1):
                if child not in tags:
                    need(local_start(child,N)>=c.n,'missing local proof');tags[child]=ZERO
            tags[p]=P.F(b'LOCAL_NODE',c.context(),ui(b,8),ui(p,8),tags[2*p],tags[2*p+1])
        active=parents
    return tags[1]

@dataclass
class Stored:
    header:bytes; slots:list[bytes]; local:dict[int,bytes]; bucket_tag:bytes

class Server:
    """Only public configurations, encrypted fixed records, and saved tags."""
    def __init__(self,configs:list[Config]):
        self.configs={c.tree:c for c in configs};self.buckets={};self.global_tags={}
    def handle(self,raw:bytes)->bytes:
        op,tree,seq,flags,body=parse_frame(raw);need(flags==0 and tree in self.configs,'server routing')
        c=self.configs[tree];q=Cursor(body);out=b''
        if op==INIT:
            b=q.uint();need(1<=b<(1<<(c.L+1)),'init bucket')
            if c.rootless and b==1:
                bt=q.take(TAG);gt=q.take(TAG);self.buckets[tree,b]=Stored(b'',[],{},bt)
            else:
                hd=q.take(c.H);slots=[q.take(c.W) for _ in range(c.n)]
                local={p:q.take(TAG) for p in local_indices(c.n)} if c.ring else {}
                bt=q.take(TAG);gt=q.take(TAG);self.buckets[tree,b]=Stored(hd,slots,local,bt)
            self.global_tags[tree,b]=gt;q.end()
        elif op in (OPEN_FULL,OPEN_HEAD,READ_SLOTS,WRITE):
            leaf=q.uint();ms=q.uint();need(leaf<(1<<c.L),'leaf range')
            ds=from_bitmap(ms,c.L+1);need(bool(ds) and (not c.rootless or 0 not in ds),'path mask')
            path=[node(leaf,d,c.L) for d in range(c.L+1)]
            if op in (OPEN_FULL,OPEN_HEAD):
                q.end()
                for d in ds:
                    s=self.buckets[tree,path[d]];out+=s.header
                    out+=b''.join(s.slots) if op==OPEN_FULL else s.local[1]
                for d,b in enumerate(path):
                    if d not in ds and not(c.rootless and d==0):out+=self.buckets[tree,b].bucket_tag
                for d in range(c.L):out+=self.global_tags[tree,path[d+1]^1]
            elif op==READ_SLOTS:
                need(c.ring,'partial read on non-Ring')
                for d in ds:
                    inds=from_bitmap(q.uint(),c.n);s=self.buckets[tree,path[d]]
                    need(bool(inds),'empty subset');out+=b''.join(s.slots[j] for j in inds)
                    out+=b''.join(s.local[p] for p in witnesses(c.n,inds))
                q.end()
            else:
                fs=q.uint();full=from_bitmap(fs,c.L+1);need(set(full)<=set(ds),'full-write mask')
                for d in ds:
                    b=path[d];old=self.buckets[tree,b];hd=q.take(c.H)
                    slots=[q.take(c.W) for _ in range(c.n)] if d in full else old.slots
                    local=({p:q.take(TAG) for p in local_indices(c.n)} if c.ring else {}) if d in full else old.local
                    bt=q.take(TAG);self.buckets[tree,b]=Stored(hd,slots,local,bt)
                for d in range(max(ds)+1):self.global_tags[tree,path[d]]=q.take(TAG)
                q.end()
        else:raise Reject('opcode')
        return frame(op,tree,seq,out,True)

class Transport:
    """Byte-accurate in-process framing. Optional active response mutation."""
    def __init__(self,server:Server):
        self.server=server;self.seq=0;self.events=[];self.total=Counter();self.mutator=None
    def rpc(self,c:Config,op:int,body:bytes,stage:str,meta:dict,components:dict)->bytes:
        seq=self.seq;self.seq+=1;request=frame(op,c.tree,seq,body)
        response=self.server.handle(request)
        if self.mutator is not None:response=self.mutator(c,op,seq,stage,meta,request,response)
        event=dict(sequence=seq,tree=c.tree,stage=stage,opcode=op,request_bytes=len(request),response_bytes=len(response),
                   request_sha256=hashlib.sha256(request).hexdigest(),response_sha256=hashlib.sha256(response).hexdigest(),**meta)
        parts=dict(components);parts['framing_and_control']=len(request)+len(response)-sum(parts.values())
        event['components']=parts;self.events.append(event)
        for k,v in parts.items():self.total[k]+=v
        rop,rt,rs,rf,result=parse_frame(response)
        need((rop,rt,rs,rf)==(op,c.tree,seq,1),'response routing/replay')
        return result

@dataclass
class View:
    leaf:int;selected:tuple[int,...];headers:dict[int,Header];wire_headers:dict[int,bytes]
    data_roots:dict[int,bytes];bucket_tags:dict[int,bytes];siblings:dict[int,bytes];path_tags:dict[int,bytes]
    plaintexts:dict[int,list[bytes]]=field(default_factory=dict)

class Tree:
    def __init__(self,c:Config,P:PRF,transport:Transport):
        self.c=c;self.P=P;self.io=transport;self.ctx=c.context();self.root=b''
        self.t=0;self.g=0;self.uid=0;self.stash:dict[int,Record]={};self.max_stash=0
        self.empty_root=P.F(b'EMPTY_ROOT',self.ctx)
        self.observer=None # optional external test-only observer, not used in path decisions
    def oid(self,b:int,j:int|None=None):return (b'H'+ui(b,8)) if j is None else (b'D'+ui(b,8)+ui(j,2))
    def btag(self,b:int,hd:bytes,D:bytes):return self.P.F(b'BUCKET',self.ctx,ui(b,8),hd,D)
    def ntag(self,b:int,B:bytes,l:bytes,r:bytes):return self.P.F(b'GLOBAL_NODE',self.ctx,ui(b,8),B,l,r)
    def droot(self,b:int,slots:list[bytes]):return self.P.F(b'FULL_DATA',self.ctx,ui(b,8),b''.join(slots))
    def prepare(self,b:int,old:Header,records:list[Record]|None,gamma:int|None=None):
        c=self.c
        if records is None:
            h=Header(old.gamma,old.w,old.v+1,old.count,old.used,dict(old.live));slots=None;local=None
        else:
            need(len(records)<=c.Z,'bucket over capacity')
            rank=self.P.draw(self.ctx,b'PERMUTE'+ui(b,8))%math.factorial(c.n)
            perm=factorial_decode(rank,c.n);plain=[bytes(c.B) for _ in range(c.n)];live={}
            for i,r in enumerate(records):
                need(len(r.payload)==c.B,'payload size');j=perm[i];plain[j]=r.payload;live[j]=Desc(r.uid,r.address,r.leaf,j)
            h=Header(old.gamma if gamma is None else gamma,old.w+1,old.v+1,0,0,live)
            slots=[self.P.seal(self.ctx,self.oid(b,j),ui(h.w),p) for j,p in enumerate(plain)]
            local=local_make(c,self.P,b,slots) if c.ring else {}
        pub=h.public();hd=pub+self.P.seal(self.ctx,self.oid(b),pub,h.secret_bytes(c))
        need(len(hd)==c.H,'serialized header length')
        D=(local[1] if c.ring else self.droot(b,slots)) if slots is not None else None
        return h,hd,slots,local,D
    def initialize(self):
        c=self.c
        def visit(b:int,d:int):
            left=visit(2*b,d+1) if d<c.L else ZERO
            right=visit(2*b+1,d+1) if d<c.L else ZERO
            if c.rootless and b==1:
                bt=self.empty_root;gt=self.ntag(b,bt,left,right);body=ui(b,8)+bt+gt
                comp={'authentication_upload':2*TAG}
            else:
                h,hd,slots,local,D=self.prepare(b,Header(w=0,v=0),[],0)
                bt=self.btag(b,hd,D);gt=self.ntag(b,bt,left,right)
                body=ui(b,8)+hd+b''.join(slots)+(b''.join(local[p] for p in local_indices(c.n)) if c.ring else b'')+bt+gt
                comp={'headers_upload':c.H,'data_upload':c.n*c.W,'authentication_upload':(len(local)+2)*TAG}
            out=self.io.rpc(c,INIT,body,'physical_setup',{'bucket':b},comp);need(out==b'','init ack')
            return gt
        self.root=visit(1,0)
    def reconstruct(self,leaf:int,B:dict[int,bytes],siblings:dict[int,bytes]):
        c=self.c;tags={};nxt=ZERO
        for d in range(c.L,-1,-1):
            b=node(leaf,d,c.L)
            if d==c.L:l=r=ZERO
            elif node(leaf,d+1,c.L)%2==0:l,r=nxt,siblings[d]
            else:l,r=siblings[d],nxt
            nxt=self.ntag(b,B[b],l,r);tags[b]=nxt
        return nxt,tags
    def open_path(self,leaf:int,ds:tuple[int,...],stage:str)->View:
        c=self.c;op=OPEN_HEAD if c.ring else OPEN_FULL;k=len(ds)
        skip=len(c.levels)-k
        comp={'headers_download':k*c.H,'authentication_download':(c.L+skip+(k if c.ring else 0))*TAG}
        if not c.ring:comp['data_download']=k*c.n*c.W
        raw=self.io.rpc(c,op,ui(leaf,8)+ui(bitmap(ds),8),stage,{'leaf':leaf,'depths':list(ds)},comp)
        q=Cursor(raw);wh={};D={};cts={};B={}
        for d in ds:
            b=node(leaf,d,c.L);wh[b]=q.take(c.H)
            if c.ring:D[b]=q.take(TAG)
            else:cts[b]=[q.take(c.W) for _ in range(c.n)];D[b]=self.droot(b,cts[b])
            B[b]=self.btag(b,wh[b],D[b])
        for d in range(c.L+1):
            b=node(leaf,d,c.L)
            if d not in ds:B[b]=self.empty_root if c.rootless and d==0 else q.take(TAG)
        siblings={d:q.take(TAG) for d in range(c.L)};q.end()
        root,pt=self.reconstruct(leaf,B,siblings);need(hmac.compare_digest(root,self.root),'global opening not current')
        # The entire global opening is authenticated before any header is decrypted.
        headers={}
        for b,hd in wh.items():
            pub=hd[:PUBLIC];headers[b]=Header.decode(c,pub,self.P.decrypt(self.ctx,self.oid(b),pub,hd[PUBLIC:]))
            if c.kind!='path':need(headers[b].gamma==generation(self.g,depth(b),b-(1<<depth(b))),'placement generation')
        plains={}
        if not c.ring:
            for b,xs in cts.items():plains[b]=[self.P.decrypt(self.ctx,self.oid(b,j),ui(headers[b].w),ct) for j,ct in enumerate(xs)]
        return View(leaf,ds,headers,wh,D,B,siblings,pt,plains)
    def read_slots(self,view:View,selection:dict[int,tuple[int,...]],stage:str):
        need(hmac.compare_digest(view.path_tags[1],self.root),'stale local-read view')
        c=self.c;ds=tuple(sorted(depth(b) for b in selection));count=sum(map(len,selection.values()))
        proofcount=sum(len(witnesses(c.n,tuple(sorted(v)))) for v in selection.values())
        body=ui(view.leaf,8)+ui(bitmap(ds),8)+b''.join(ui(bitmap(selection[node(view.leaf,d,c.L)]),8) for d in ds)
        raw=self.io.rpc(c,READ_SLOTS,body,stage,{'leaf':view.leaf,'depths':list(ds),'slots':[list(selection[node(view.leaf,d,c.L)]) for d in ds]},
                        {'data_download':count*c.W,'authentication_download':proofcount*TAG})
        q=Cursor(raw);allcts={}
        for d in ds:
            b=node(view.leaf,d,c.L);inds=tuple(sorted(selection[b]));cts={j:q.take(c.W) for j in inds}
            proof={p:q.take(TAG) for p in witnesses(c.n,inds)}
            computed=local_open_root(c,self.P,b,cts,proof)
            need(hmac.compare_digest(computed,view.data_roots[b]),'local data opening not current')
            allcts[b]=cts
        q.end()
        # All local openings, including dummy slots, pass before any payload decrypts.
        return {b:{j:self.P.decrypt(self.ctx,self.oid(b,j),ui(view.headers[b].w),ct) for j,ct in cts.items()} for b,cts in allcts.items()}
    def write(self,view:View,changes:dict[int,tuple],stage:str):
        need(hmac.compare_digest(view.path_tags[1],self.root),'stale write view')
        c=self.c;ds=tuple(sorted(depth(b) for b in changes));full=[];serialized={};newB=dict(view.bucket_tags);authup=0;dataup=0
        for d in ds:
            b=node(view.leaf,d,c.L);h,hd,slots,local,D=changes[b]
            if slots is not None:full.append(d);dataup+=len(slots)*c.W
            else:D=view.data_roots[b]
            bt=self.btag(b,hd,D);newB[b]=bt
            serialized[b]=hd+(b''.join(slots) if slots is not None else b'')+(b''.join(local[p] for p in local_indices(c.n)) if slots is not None and c.ring else b'')+bt
            authup+=TAG*(1+(len(local) if local is not None else 0))
        root,pt=self.reconstruct(view.leaf,newB,view.siblings);maxd=max(ds);authup+=(maxd+1)*TAG
        body=ui(view.leaf,8)+ui(bitmap(ds),8)+ui(bitmap(full),8)+b''.join(serialized[node(view.leaf,d,c.L)] for d in ds)+b''.join(pt[node(view.leaf,d,c.L)] for d in range(maxd+1))
        out=self.io.rpc(c,WRITE,body,stage,{'leaf':view.leaf,'depths':list(ds),'full_depths':full},
                        {'headers_upload':len(ds)*c.H,'data_upload':dataup,'authentication_upload':authup})
        need(out==b'','write ack');self.root=root;view.bucket_tags=newB;view.path_tags=pt
        for b,(h,hd,slots,local,D) in changes.items():
            view.headers[b]=h;view.wire_headers[b]=hd
            if D is not None:view.data_roots[b]=D
            if self.observer is not None:self.observer('header',self.c.tree,b,h)
    def subset(self,b:int,h:Header)->tuple[int,...]:
        c=self.c;real=set(h.live);unused=[j for j in range(c.n) if not(h.used>>j&1)];dummy=[j for j in unused if j not in real]
        need(real<=set(unused),'remaining real not unread');k=c.Z-len(real)
        draw=self.P.draw(self.ctx,b'RMW_SUBSET'+ui(b,8));den=math.comb(len(dummy),k)
        extra=choose_rank(dummy,k,draw%den)
        return tuple(sorted(real|set(extra)))
    def fused_logical(self,view:View,address:int):
        from fused_logical import fused_logical
        return fused_logical(self,view,address)
    def neutral(self,view:View,b:int):
        h=view.headers[b];selection=self.subset(b,h);plains=self.read_slots(view,{b:selection},'early')
        records=[Record(d.uid,d.address,d.leaf,plains[b][j]) for j,d in sorted(h.live.items())]
        prepared=self.prepare(b,h,sorted(records,key=lambda x:x.uid),h.gamma)
        self.write(view,{b:prepared},'early')
    def collect(self,view:View,stage:str):
        if self.c.ring:
            selection={b:self.subset(b,view.headers[b]) for b in view.headers}
            plains=self.read_slots(view,selection,stage)
        else:plains={b:dict(enumerate(v)) for b,v in view.plaintexts.items()}
        return [Record(d.uid,d.address,d.leaf,plains[b][j]) for b,h in view.headers.items() for j,d in h.live.items()]
    def placement(self,pool:dict[int,Record],view:View,gamma:int,constrained:bool):
        c=self.c;changes={}
        for d in reversed(view.selected):
            b=node(view.leaf,d,c.L)
            chosen=[r for r in sorted(pool.values(),key=lambda x:x.uid) if node(r.leaf,d,c.L)==b and (not constrained or d in gc(gamma,r.leaf,c.L))][:c.Z]
            for r in chosen:pool.pop(r.uid)
            changes[b]=self.prepare(b,view.headers[b],chosen,gamma)
        self.write(view,changes,'path' if c.kind=='path' else 'evict')
        self.stash={r.address:r for r in pool.values()}
    def evict(self):
        c=self.c;ep=rev(self.g%(1<<c.L),c.L);view=self.open_path(ep,c.levels,'evict')
        pool={r.uid:r for r in self.stash.values()}
        for r in self.collect(view,'evict'):need(r.uid not in pool,'duplicate pool uid');pool[r.uid]=r
        self.placement(pool,view,self.g+1,c.constrained);self.g+=1
    def access(self,address:int,oldleaf:int,newleaf:int,transform:Callable[[bytes],bytes]):
        c=self.c;need(0<=address<c.N and 0<=oldleaf<(1<<c.L) and 0<=newleaf<(1<<c.L),'access bounds')
        ds=tuple(sorted(gc(self.g,oldleaf,c.L)-({0} if c.rootless else set()))) if c.selective else c.levels
        view=self.open_path(oldleaf,ds,'path' if c.kind=='path' else 'logical')
        if c.kind=='path':
            records=self.collect(view,'path');pool={r.uid:r for r in self.stash.values()}
            for r in records:need(r.uid not in pool,'duplicate uid');pool[r.uid]=r
            matches=[r for r in pool.values() if r.address==address];need(len(matches)<=1,'duplicate current address')
            old=matches[0] if matches else None
            if old:pool.pop(old.uid)
        elif c.ring and c.fused:
            old=self.fused_logical(view,address)
        else:
            if c.ring:
                for d in ds:
                    b=node(oldleaf,d,c.L)
                    if view.headers[b].count==c.S:self.neutral(view,b)
                selections={}
                for d in ds:
                    b=node(oldleaf,d,c.L);h=view.headers[b];draw=self.P.draw(self.ctx,b'LOGICAL_SLOT'+ui(b,8))
                    matches=[j for j,x in h.live.items() if x.address==address];need(len(matches)<=1,'multiple target slots')
                    dummy=[j for j in range(c.n) if not(h.used>>j&1) and j not in h.live]
                    need(bool(dummy),'no fresh dummy')
                    j=matches[0] if matches else dummy[draw%len(dummy)];selections[b]=(j,)
                plains=self.read_slots(view,selections,'logical')
            else:plains={b:dict(enumerate(v)) for b,v in view.plaintexts.items()}
            old=self.stash.pop(address,None);changes={}
            for d in ds:
                b=node(oldleaf,d,c.L);h=view.headers[b]
                matches=[j for j,x in h.live.items() if x.address==address]
                if matches:
                    need(old is None,'duplicate current');j=matches[0];de=h.live.pop(j);old=Record(de.uid,de.address,de.leaf,plains[b][j])
                if c.ring:
                    j=selections[b][0];h.count+=1;h.used|=1<<j
                changes[b]=self.prepare(b,h,None)
            self.write(view,changes,'logical')
        previous=old.payload if old else bytes(c.B)
        updated=transform(previous);need(isinstance(updated,bytes) and len(updated)==c.B,'fixed payload transform')
        self.uid+=1;fresh=Record(self.uid,address,newleaf,updated)
        if c.kind=='path':pool[fresh.uid]=fresh;self.placement(pool,view,self.t+1,False);self.g+=1
        else:self.stash[address]=fresh
        self.t+=1
        if c.kind!='path' and self.t%c.A==0:self.evict()
        self.max_stash=max(self.max_stash,len(self.stash))
        if len(self.stash)>c.R:raise Overflow('persistent round-boundary stash')
        if self.observer is not None:self.observer('access',c.tree,(address,oldleaf,newleaf,previous,updated),self)
        return previous

class RecursiveORAM:
    def __init__(self,configs:list[Config],key:bytes):
        need(bool(configs),'empty recursion')
        for i,c in enumerate(configs):
            need(c.tree==i,'ordered tree contexts')
            if i+1<len(configs):need(configs[i+1].N==(c.N+configs[i+1].B//4-1)//(configs[i+1].B//4),'map geometry')
        self.configs=configs;self.P=PRF(key);self.server=Server(configs);self.io=Transport(self.server)
        self.trees=[Tree(c,self.P,self.io) for c in configs]
        last=configs[-1];self.terminal_pos=[self.P.initial(last.context(),a,last.L) for a in range(last.N)]
        self.dead=False;self.busy=False;self.committed=None;self.commits=0;self.ready=False;self.initializing=False
    def anchor(self):
        return (tuple((t.root,t.t,t.g,tuple(sorted((r.uid,r.address,r.leaf,hashlib.sha256(r.payload).digest()) for r in t.stash.values()))) for t in self.trees),tuple(self.terminal_pos))
    def _access(self,j:int,a:int,transform):
        tree=self.trees[j];c=tree.c;newleaf=self.P.draw(c.context(),b'REMAP')&((1<<c.L)-1)
        if j==len(self.trees)-1:oldleaf=self.terminal_pos[a];self.terminal_pos[a]=newleaf
        else:
            chi=self.configs[j+1].B//4;b,off=divmod(a,chi)
            def modify(p:bytes):return p[:4*off]+ui(newleaf,4)+p[4*off+4:]
            word=self._access(j+1,b,modify);oldleaf=int.from_bytes(word[4*off:4*off+4],'big')
        return tree.access(a,oldleaf,newleaf,transform)
    def access(self,a:int,value:bytes|None=None,*,start_layer:int=0):
        if self.dead:raise Reject('fail-stop client')
        if not(self.ready or self.initializing):raise Reject('initialization required')
        if self.busy:raise Reject('concurrent/reentrant operation')
        self.busy=True
        try:
            answer=self._access(start_layer,a,(lambda p:p) if value is None else (lambda p:value))
            self.committed=self.anchor();self.commits+=1
            return answer
        except Exception:
            # Working roots/storage may have advanced. No unsafe retry or rollback.
            self.dead=True;raise
        finally:self.busy=False
    def initialize(self,data:Callable[[int],bytes]|None=None):
        if self.dead or self.committed is not None:raise Reject('initialization state')
        self.initializing=True
        try:
            for t in self.trees:t.initialize()
            self.committed=self.anchor()
            for j in range(len(self.trees)-1,0,-1):
                c=self.configs[j];parent=self.configs[j-1];chi=c.B//4
                for b in range(c.N):
                    word=b''.join(ui(self.P.initial(parent.context(),a,parent.L),4) if a<parent.N else bytes(4) for a in range(b*chi,(b+1)*chi))
                    self.access(b,word,start_layer=j)
            c=self.configs[0]
            for a in range(c.N):self.access(a,data(a) if data else bytes(c.B))
            self.ready=True
        except Exception:
            self.dead=True;raise
        finally:self.initializing=False
