"""Restricted Freecursive frontend and rho-inspired exclusive-cache prototype.

These are new, explicitly scoped variants: SOC3 authentication, no PMMAC/ECC,
no hardware timing model. Frontend replacement depends on addresses, not leaves.
"""
from collections import OrderedDict,Counter
from dataclasses import dataclass
import hashlib,hmac,math
from transfer_backend import Backend,Reject,need

def initial_payload(address,B):return address.to_bytes(8,'big')+bytes(B-8)

class Leaves:
    def __init__(self,L,seed,domain):
        self.L=L;self.key=hashlib.sha512(str(seed).encode()+domain).digest();self.seq=0;self.calls=0
    def named(self,*parts):
        self.calls+=1
        raw=b''.join(len(p).to_bytes(4,'big')+p for p in (str(x).encode() for x in parts))
        return int.from_bytes(hmac.new(self.key,raw,hashlib.sha512).digest(),'big')&((1<<self.L)-1)
    def fresh(self,label):
        self.seq+=1;return self.named('stream',label,self.seq)

@dataclass
class CachedMap:
    address:int
    data:bytes
    parked_leaf:int

class FreecursiveFront:
    def __init__(self,kind='sde',N=256,B=64,X=None,beta=14,compressed=True,plb=4,seed=0,profile=(4,3,4)):
        self.N=N;self.B=B;self.compressed=compressed;self.beta=beta
        self.X=X or (32 if compressed else B//4)
        need((64+self.X*beta<=8*B) if compressed else (4*self.X<=B),'map packing')
        self.counts=[N]
        while self.counts[-1]>1:self.counts.append(math.ceil(self.counts[-1]/self.X))
        self.offsets=[];total=0
        for n in self.counts:self.offsets.append(total);total+=n
        self.total=total;self.capacity=plb;self.cache=OrderedDict();self.pinned=set()
        self.L=max(1,math.ceil(math.log2(2*total/3)))
        self.leaves=Leaves(self.L,seed,b'FREE-MAP');self.padding=Leaves(self.L,seed,b'FREE-DUMMY')
        Z,A,S=profile
        self.backend=Backend(kind,self.L,total,B=B,Z=Z,A=A,S=S,R=128)
        self.top=[self.leaves.named('top-init',i) for i in range(self.counts[-1])]
        self.metrics=Counter();self.dead=False
        for level,n in enumerate(self.counts):
            for i in range(n):
                a=self.addr(level,i)
                payload=initial_payload(i,B) if level==0 else self.encode_map(level,i,0,[0]*self.X)
                self.backend.tick(None,self.padding.fresh('init'),admit=(a,self.initial_leaf(level,i),payload))
        self.metrics.clear()

    def addr(self,level,i):return self.offsets[level]+i
    def initial_leaf(self,level,i):
        if level==len(self.counts)-1:return self.top[i]
        return self.leaves.named('compressed-leaf',self.addr(level,i),0,0) if self.compressed else self.leaves.named('raw-init',self.addr(level,i))
    def encode_map(self,level,i,group,counts):
        if self.compressed:
            value=sum(v<<(j*self.beta) for j,v in enumerate(counts))
            return group.to_bytes(8,'big')+value.to_bytes(self.B-8,'big')
        # Only used for initialization; subsequent raw updates edit payload bytes.
        children=range(i*self.X,min((i+1)*self.X,self.counts[level-1]))
        raw=b''.join(self.initial_leaf(level-1,j).to_bytes(4,'big') for j in children)
        return raw+bytes(self.B-len(raw))
    def decode_map(self,payload):
        g=int.from_bytes(payload[:8],'big');v=int.from_bytes(payload[8:],'big')
        return g,[(v>>(j*self.beta))&((1<<self.beta)-1) for j in range(self.X)]

    def reset_group(self,level,parent_i,parent):
        group,counts=self.decode_map(parent.data)
        need(group<(1<<64)-1,'group counter exhausted before I/O')
        self.metrics['group_resets']+=1
        for j in range(self.X):
            child_i=parent_i*self.X+j
            if child_i>=self.counts[level]:break
            a=self.addr(level,child_i)
            old=self.leaves.named('compressed-leaf',a,group,counts[j])
            new=self.leaves.named('compressed-leaf',a,group+1,0)
            if a in self.cache:
                need(self.cache[a].parked_leaf==old,'cached group leaf mismatch')
                self.cache[a].parked_leaf=new;self.metrics['group_cached_rotations']+=1
            else:
                self.backend.tick(a,old,replace=(new,lambda p:p))
                self.metrics['group_backend_slots']+=1
        parent.data=self.encode_map(level+1,parent_i,group+1,[0]*self.X)

    def reserve(self,level,i):
        if level==len(self.counts)-1:
            old=self.top[i];new=self.leaves.fresh('top-remap');self.top[i]=new;return old,new
        parent_i,j=divmod(i,self.X);parent=self.ensure_map(level+1,parent_i)
        self.pinned.add(parent.address)
        try:
            if self.compressed:
                group,counts=self.decode_map(parent.data)
                if counts[j]==(1<<self.beta)-1:
                    self.reset_group(level,parent_i,parent)
                    group,counts=self.decode_map(parent.data)
                a=self.addr(level,i);old=self.leaves.named('compressed-leaf',a,group,counts[j])
                counts[j]+=1;new=self.leaves.named('compressed-leaf',a,group,counts[j])
                parent.data=self.encode_map(level+1,parent_i,group,counts)
            else:
                old=int.from_bytes(parent.data[4*j:4*j+4],'big');new=self.leaves.fresh('raw-remap')
                parent.data=parent.data[:4*j]+new.to_bytes(4,'big')+parent.data[4*j+4:]
            return old,new
        finally:self.pinned.remove(parent.address)

    def ensure_map(self,level,i):
        a=self.addr(level,i)
        if a in self.cache:
            self.metrics['plb_hits']+=1;self.cache.move_to_end(a);return self.cache[a]
        self.metrics['plb_misses']+=1
        old,new=self.reserve(level,i)
        victim=None
        if len(self.cache)>=self.capacity:
            candidates=[k for k in self.cache if k not in self.pinned]
            need(bool(candidates),'PLB needs space for pinned recursion path')
            victim=self.cache.pop(candidates[0]);self.metrics['plb_evictions']+=1
        admission=None if victim is None else (victim.address,victim.parked_leaf,victim.data)
        payload=self.backend.tick(a,old,admit=admission)
        entry=CachedMap(a,payload,new);self.cache[a]=entry
        need(len(self.cache)<=self.capacity,'PLB capacity')
        return entry

    def access(self,a,value=None):
        if self.dead:raise Reject('fail-stop frontend')
        try:
            need(0<=a<self.N,'data address');old,new=self.reserve(0,a)
            answer=self.backend.tick(a,old,replace=(new,(lambda p:p) if value is None else (lambda p:value)))
            self.metrics['application_requests']+=1
            return answer
        except Exception:
            self.dead=True;self.backend.tree.dead=True;raise
    def memory_payload_bound(self):
        # A representation budget, explicitly not measured RSS or peak scratch.
        return {'plb_payload_bytes':self.capacity*self.B,'plb_leaf_and_address_bytes':self.capacity*12,
                'terminal_leaf_bytes':4*len(self.top),'stash_reserved_bytes':self.backend.c.R*self.B,
                'full_private_posmap_present':False,'measured_peak':False}

class RhoFront:
    """Address-only exclusive LLC/rho tags; public n-rho/one-backend frames.

    Fully associative LRU is a scoped replacement for the paper's set-assoc tags.
    The backend PosMap is flat/trusted in this first system prototype.
    """
    def __init__(self,kind='sde',N=256,B=64,llc=8,rho=32,n=3,seed=0,profile=(4,3,4)):
        self.N=N;self.B=B;self.llc_capacity=llc;self.rho_capacity=rho;self.n=n
        self.llc=OrderedDict();self.tags=OrderedDict();self.free=list(range(rho))
        L=max(1,math.ceil(math.log2(2*N/3)))
        Z,A,S=profile
        self.back=Backend(kind,L,N,B=B,Z=Z,A=A,S=S,R=128,tree=0)
        # Keep low-Z front end as Path. Its numerical tail is NOT SOC3 certified.
        LR=max(1,math.ceil(math.log2(8*rho)))
        self.front=Backend('path',LR,rho,B=B,Z=2,A=1,S=0,R=rho,tree=1,key=b'R'*64)
        self.b_rng=Leaves(L,seed,b'RHO-BACK');self.f_rng=Leaves(LR,seed,b'RHO-FRONT')
        self.b_pad=Leaves(L,seed,b'RHO-BACK-DUMMY');self.f_pad=Leaves(LR,seed,b'RHO-FRONT-DUMMY')
        self.backpos={a:self.b_rng.fresh('initial') for a in range(N)}
        self.frontpos={slot:self.f_rng.fresh('initial') for slot in range(rho)}
        for a in range(N):self.back.tick(None,self.b_pad.fresh('init'),admit=(a,self.backpos[a],initial_payload(a,B)))
        self.metrics=Counter();self.dead=False

    def _finish(self,a,previous,value,answers):
        self.llc[a]=previous if value is None else value
        self.llc.move_to_end(a);answers.append(previous)
        need(len(self.llc)<=self.llc_capacity,'LLC overflow')

    def run(self,requests):
        if self.dead:raise Reject('fail-stop rho frontend')
        cursor=0;answers=[]
        try:
            while cursor<len(requests):
                pending=None;self.metrics['frames']+=1
                for _ in range(self.n):
                    if pending is None:
                        while cursor<len(requests) and requests[cursor][0] in self.llc:
                            a,value=requests[cursor];cursor+=1
                            previous=self.llc[a];self._finish(a,previous,value,answers)
                            self.metrics['llc_hits']+=1
                    if pending is not None or cursor==len(requests):
                        self.front.tick(None,self.f_pad.fresh('dummy'));self.metrics['rho_dummy_slots']+=1
                        continue
                    a,value=requests[cursor];cursor+=1;self.metrics['llc_misses']+=1
                    outgoing=self.llc.popitem(last=False) if len(self.llc)>=self.llc_capacity else None
                    if a in self.tags:
                        self.metrics['rho_hits']+=1;slot=self.tags.pop(a)
                        old=self.frontpos[slot];new=self.f_rng.fresh('rho-hit');self.frontpos[slot]=new
                        admission=None if outgoing is None else (slot,new,outgoing[1])
                        previous=self.front.tick(slot,old,admit=admission)
                        if outgoing is None:self.free.append(slot)
                        else:self.tags[outgoing[0]]=slot
                        self._finish(a,previous,value,answers)
                    else:
                        self.metrics['rho_misses']+=1;victim=None
                        if outgoing is not None:
                            if self.free:
                                slot=self.free.pop(0);old=self.f_pad.fresh('empty-slot');remove=None
                            else:
                                victim_address,slot=self.tags.popitem(last=False)
                                old=self.frontpos[slot];remove=slot
                            new=self.f_rng.fresh('rho-fill');self.frontpos[slot]=new
                            previous=self.front.tick(remove,old,admit=(slot,new,outgoing[1]))
                            if remove is not None:victim=(victim_address,self.backpos[victim_address],previous)
                            self.tags[outgoing[0]]=slot
                        else:
                            self.front.tick(None,self.f_pad.fresh('empty-llc'));self.metrics['rho_dummy_slots']+=1
                        pending=(a,value,victim)
                # Every completed frame has exactly n front slots and one back slot.
                if pending is None:
                    self.back.tick(None,self.b_pad.fresh('dummy'));self.metrics['back_dummy_slots']+=1
                else:
                    a,value,victim=pending;old=self.backpos[a]
                    self.backpos[a]=self.b_rng.fresh('park')
                    previous=self.back.tick(a,old,admit=victim)
                    self._finish(a,previous,value,answers)
            self.metrics['application_requests']+=len(requests)
            return answers
        except Exception:
            self.dead=True;self.front.tree.dead=True;self.back.tree.dead=True;raise

    def memory_payload_bound(self):
        return {'llc_payload_bytes':self.llc_capacity*self.B,'rho_directory_entries':self.rho_capacity,
                'flat_backend_posmap_bytes':4*self.N,'front_posmap_bytes':4*self.rho_capacity,
                'front_stash_reserved_bytes':self.rho_capacity*self.B,'back_stash_reserved_bytes':128*self.B,
                'full_private_posmap_present':True,'measured_peak':False}
