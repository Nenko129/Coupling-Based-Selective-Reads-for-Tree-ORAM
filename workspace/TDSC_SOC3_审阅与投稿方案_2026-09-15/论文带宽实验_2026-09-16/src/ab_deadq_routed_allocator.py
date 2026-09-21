"""Authenticated, encrypted data-plane realization of report 52's allocator.

This module does not import/run the whole-state Allocator. Directory rows,
reverse owners and the FIFO live in the external Merkle store. Transaction
caches are discarded at commit. This is NOT a CB/ORAM or native AB engine.
It assumes a serial, non-restarting trusted client and correctly supplied
admissions. Public operation selection and obliviousness belong to the caller.
"""
import hashlib
import secrets
import struct
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ab_deadq_authenticated_store import RowServer,WireRecorder,VerifiedRows,need


NONE=2**32-1


@dataclass(frozen=True)
class Layout:
    buckets:int
    base:int
    extra:int
    component_cap:int
    queue_cap:int
    payload_bytes:int=64

    def __post_init__(self):
        need(self.buckets>=2 and self.buckets&(self.buckets-1)==0,'power-of-two level')
        need(self.base>=1 and 1<=self.extra<=self.base,'base/extra')
        need(1<=self.component_cap<=self.buckets and self.queue_cap>=self.extra,'limits')
        need(self.payload_bytes>0 and self.count<NONE,'encoding limits')

    @property
    def physical(self):return self.buckets*self.base
    @property
    def count(self):return 2+self.buckets+2*self.physical
    @property
    def queue_row(self):return 1+self.buckets+self.physical
    def bucket_row(self,b):
        need(0<=b<self.buckets,'bucket address');return 1+b
    def owner_row(self,p):
        need(0<=p<self.physical,'physical address');return 1+self.buckets+p
    def data_row(self,p):
        need(0<=p<self.physical,'data address');return self.queue_row+1+p
    def length(self,index):
        need(0<=index<self.count,'row address')
        if index==0:return 8
        if index<=self.buckets:return 12+5*(self.base+self.extra)
        if index<self.queue_row:return 16
        if index==self.queue_row:return 4+12*self.queue_cap
        return self.payload_bytes+37 # nonce12, flag1, UID8, payloadB, GCM tag16


def encode_bucket(g,epoch,maps,valid):
    need(len(maps) in (g.base,g.base+g.extra) and len(valid)==len(maps),'logical shape')
    out=struct.pack('>QI',epoch,len(maps))
    out+=b''.join(struct.pack('>IB',p,int(v)) for p,v in zip(maps,valid))
    return out+bytes(5*(g.base+g.extra-len(maps)))


def encode_owner(owner,version):
    return struct.pack('>IIQ',*(owner if owner is not None else (NONE,NONE)),version)


def encode_queue(g,queue):
    need(len(queue)<=g.queue_cap,'queue capacity')
    return struct.pack('>I',len(queue))+b''.join(struct.pack('>IQ',p,v) for p,v in queue)+bytes(12*(g.queue_cap-len(queue)))


class RoutedAllocator:
    def __init__(self,rows,g,key,domain,nonce,placement):
        self.rows=rows;self.g=g;self.key=key;self.aead=AESGCM(key);self.domain=domain
        self.next_nonce=nonce;self.placement=placement;self.cache=None;self.dirty=None
        self.pending=None;self.last_workspace=None

    @property
    def dead(self):return self.rows.dead

    def _get(self,i):
        if i not in self.cache:self.cache[i]=self.rows.row(i)
        return self.cache[i]

    def _set(self,i,value):
        need(len(value)==self.g.length(i),'encoded row size')
        if self._get(i)!=value:self.cache[i]=value;self.dirty.add(i)

    def _bucket(self,b):
        raw=self._get(self.g.bucket_row(b));epoch,n=struct.unpack('>QI',raw[:12])
        need(n in (self.g.base,self.g.base+self.g.extra),'bucket length')
        cells=[struct.unpack('>IB',raw[12+5*j:17+5*j]) for j in range(n)]
        need(all(p<self.g.physical and v in (0,1) for p,v in cells),'bucket cells')
        need(raw[12+5*n:]==bytes(len(raw)-12-5*n),'bucket padding')
        return epoch,[p for p,v in cells],[bool(v) for p,v in cells]

    def _owner(self,p):
        b,j,v=struct.unpack('>IIQ',self._get(self.g.owner_row(p)))
        need((b==j==NONE) or (b<self.g.buckets and j<self.g.base+self.g.extra),'owner cell')
        return (None if b==NONE else (b,j)),v

    def _queue(self):
        raw=self._get(self.g.queue_row);n=struct.unpack('>I',raw[:4])[0]
        need(n<=self.g.queue_cap,'FIFO length')
        queue=[struct.unpack('>IQ',raw[4+12*j:16+12*j]) for j in range(n)]
        need(len({p for p,v in queue})==n and raw[4+12*n:]==bytes(len(raw)-4-12*n),'FIFO uniqueness/padding')
        for p,v in queue:
            owner,current=self._owner(p);need(owner is None and current==v,'FIFO lease')
        return queue

    def _component(self,start):
        seen=set();todo=[start]
        while todo:
            b=todo.pop()
            if b in seen:continue
            seen.add(b);need(len(seen)<=self.g.component_cap,'component invariant')
            epoch,maps,valid=self._bucket(b)
            for j,p in enumerate(maps):
                if not valid[j]:continue
                owner,_=self._owner(p);need(owner==(b,j),'forward/reverse match')
                if p//self.g.base not in seen:todo.append(p//self.g.base)
            for p in range(b*self.g.base,(b+1)*self.g.base):
                owner,_=self._owner(p)
                if owner is None:continue
                logical,j=owner;_,other,ov=self._bucket(logical)
                need(j<len(other) and ov[j] and other[j]==p,'reverse/forward match')
                if logical not in seen:todo.append(logical)
        return seen

    def _aad(self,b,j,p,epoch,version):
        return b'DeadQ-data-v1\x00'+self.domain+struct.pack('>IIIQQ',b,j,p,epoch,version)

    def _seal(self,b,j,p,epoch,version,record):
        need(self.next_nonce<2**96,'nonce exhaustion')
        nonce=self.next_nonce.to_bytes(12,'big');self.next_nonce+=1
        if record is None:plain=bytes(9+self.g.payload_bytes)
        else:
            uid,payload=record;need(0<=uid<2**64 and len(payload)==self.g.payload_bytes,'record format')
            plain=b'\x01'+struct.pack('>Q',uid)+payload
        return nonce+self.aead.encrypt(nonce,plain,self._aad(b,j,p,epoch,version))

    def _record(self,b,j,p):
        epoch,maps,valid=self._bucket(b)
        need(j<len(maps) and valid[j] and maps[j]==p,'live read')
        owner,v=self._owner(p);need(owner==(b,j),'read ownership')
        raw=self._get(self.g.data_row(p)) # Merkle verification precedes AES-GCM.
        plain=self.aead.decrypt(raw[:12],raw[12:],self._aad(b,j,p,epoch,v))
        need(len(plain)==9+self.g.payload_bytes and plain[0] in (0,1),'record plaintext')
        if plain[0]==0:
            need(plain==bytes(len(plain)),'canonical dummy');return None
        return struct.unpack('>Q',plain[1:9])[0],plain[9:]

    def _consume(self,b,j,queue):
        epoch,maps,valid=self._bucket(b)
        need(0<=j<len(maps) and valid[j],'consume once')
        p=maps[j];record=self._record(b,j,p);owner,v=self._owner(p)
        valid[j]=False
        self._set(self.g.bucket_row(b),encode_bucket(self.g,epoch,maps,valid))
        self._set(self.g.owner_row(p),encode_owner(None,v+1))
        if len(queue)<self.g.queue_cap:queue.append((p,v+1))
        return dict(operation='consume',bucket=b,slot=j,physical=p),record

    def _rebuild(self,b,scheduled,queue,admissions):
        g=self.g;t=struct.unpack('>Q',self._get(0))[0]
        expected=int(f'{t%g.buckets:0{g.buckets.bit_length()-1}b}'[::-1],2)
        need(not scheduled or b==expected,'scheduled order')
        group=self._component(b);homes={p for x in group for p in range(x*g.base,(x+1)*g.base)}
        staged={};live=[]
        for x in sorted(group):
            epoch,maps,valid=self._bucket(x);staged[x]=[]
            for j,p in enumerate(maps):
                if valid[j]:
                    need(p in homes,'component closure');live.append((x,j,p))
                    record=self._record(x,j,p)
                    if record is not None:staged[x].append(record)
            staged[x].extend(admissions.get(x,()))
            need(len(staged[x])<=g.base,'caller real-record capacity')
        need(set(admissions)<=group,'admissions only into staged buckets')
        ids=[uid for items in staged.values() for uid,payload in items]
        need(len(ids)==len(set(ids)),'duplicate staged/admitted records')
        queue[:]=[(p,v) for p,v in queue if p not in homes]
        for x in sorted(group):
            epoch,_,_=self._bucket(x);maps=list(range(x*g.base,(x+1)*g.base))
            self._set(g.bucket_row(x),encode_bucket(g,epoch+1,maps,[True]*g.base))
            for j,p in enumerate(maps):
                old,v=self._owner(p);need(old is None or old[0] in group,'foreign owner')
                self._set(g.owner_row(p),encode_owner((x,j),v+1))
        reason='warmup';borrowed=[]
        if t>=g.buckets:
            reason='empty_or_short_queue'
            if len(queue)>=g.extra:
                combined={b}
                for p,v in queue[:g.extra]:
                    owner,current=self._owner(p);need(owner is None and current==v,'donor lease')
                    combined.update(self._component(p//g.base))
                if len(combined)>g.component_cap:reason='component_cap'
                else:
                    reason='expanded';prefix=queue[:g.extra];del queue[:g.extra]
                    epoch,maps,valid=self._bucket(b)
                    for p,v in prefix:
                        j=len(maps);maps.append(p);valid.append(True);borrowed.append(p)
                        self._set(g.owner_row(p),encode_owner((b,j),v+1))
                    self._set(g.bucket_row(b),encode_bucket(g,epoch,maps,valid))
        # Ciphertext is re-created for every public output slot, including dummy.
        for x in sorted(group):
            epoch,maps,valid=self._bucket(x)
            records=list(staged[x])+[None]*(len(maps)-len(staged[x]))
            self.placement.shuffle(records)
            for j,(p,record) in enumerate(zip(maps,records)):
                owner,v=self._owner(p);need(owner==(x,j),'output ownership')
                self._set(g.data_row(p),self._seal(x,j,p,epoch,v,record))
        if scheduled:self._set(0,struct.pack('>Q',t+1))
        return dict(operation='rebuild',bucket=b,scheduled=scheduled,warmed=t>=g.buckets,
            rebuilt=sorted(group),staged_logical_slots=live,physical_writes=sorted(homes)+borrowed,
            borrowed=borrowed,result=reason,collateral_buckets=len(group)-1,
            staged_public_slot_count=len(live),new_logical_slots=len(self._bucket(b)[1]))

    def prepare(self,operation,*args,admissions=None):
        need(not self.dead and self.pending is None and self.cache is None,'ready allocator')
        try:
            self.rows.begin();self.cache={};self.dirty=set();queue=self._queue();record=None
            if operation=='consume':
                need(not admissions,'consume admissions');event,record=self._consume(*args,queue)
            elif operation=='gather':
                need(not admissions,'gather admissions');b,=args;self.g.bucket_row(b);added=[]
                queued={p for p,v in queue}
                for p in range(b*self.g.base,(b+1)*self.g.base):
                    if len(queue)==self.g.queue_cap:break
                    owner,v=self._owner(p)
                    if owner is None and p not in queued:queue.append((p,v));queued.add(p);added.append(p)
                event=dict(operation='gather',physical_home=b,added=added)
            elif operation=='rebuild':event=self._rebuild(*args,queue,admissions or {})
            elif operation=='rebuild_consume':
                b,j,scheduled=args;rebuild=self._rebuild(b,scheduled,queue,admissions or {})
                consume,record=self._consume(b,j,queue)
                event=dict(operation=operation,rebuild=rebuild,consume=consume)
            else:raise ValueError('unknown allocator operation')
            self._set(self.g.queue_row,encode_queue(self.g,queue))
            self.pending=(event,record)
            # Diagnostic logical bytes, not a Python/process/TEE memory peak.
            self.last_workspace=dict(cached_rows=len(self.cache),cached_serialized_bytes=sum(map(len,self.cache.values())),
                dirty_rows=len(self.dirty),data_rows=sum(i>self.g.queue_row for i in self.cache))
            return event
        except Exception:
            self.rows.dead=True;self.cache=None;self.dirty=None;self.pending=None
            raise

    def commit(self):
        need(not self.dead and self.pending is not None,'prepared allocator')
        try:
            for i in sorted(self.dirty):self.rows.row(i,self.cache[i])
            self.rows.commit();event,record=self.pending
            self.cache=None;self.dirty=None;self.pending=None
            return event,record
        except Exception:
            self.rows.dead=True;self.cache=None;self.dirty=None;self.pending=None
            raise

    def apply(self,operation,*args,admissions=None):
        self.prepare(operation,*args,admissions=admissions)
        return self.commit()


def provision(g,initial_records=None,key=None,placement=None):
    """Trusted initial provisioning; its temporary full table is not free memory.

    Caller/harness owns returned wire/server objects. Measured transaction bills
    exclude this setup, whose serialized object sizes are reported separately.
    """
    key=key or AESGCM.generate_key(bit_length=256)
    placement=placement or secrets.SystemRandom()
    # Explicit instance/geometry binding. Supplied keys are for reproducible
    # fixtures; a deploying caller must never provision two instances with the
    # same key and reset nonce. The default allocates a fresh random key.
    geometry=struct.pack('>IIIIII',g.buckets,g.base,g.extra,g.component_cap,g.queue_cap,g.payload_bytes)
    domain=hashlib.sha256(b'DeadQ-instance-v1'+key+geometry).digest()
    initial_records=initial_records or {}
    need(set(initial_records)<=set(range(g.buckets)),'initial bucket keys')
    rows=[struct.pack('>Q',0)]
    rows.extend(encode_bucket(g,0,list(range(b*g.base,(b+1)*g.base)),[True]*g.base) for b in range(g.buckets))
    rows.extend(encode_owner((p//g.base,p%g.base),0) for p in range(g.physical))
    rows.append(encode_queue(g,[]))
    client=RoutedAllocator(None,g,key,domain,0,placement)
    for b in range(g.buckets):
        records=list(initial_records.get(b,()))
        need(len(records)<=g.base,'initial capacity')
        records.extend([None]*(g.base-len(records)));placement.shuffle(records)
        for j,record in enumerate(records):rows.append(client._seal(b,j,b*g.base+j,0,0,record))
    need(len(rows)==g.count and all(len(v)==g.length(i) for i,v in enumerate(rows)),'initial rows')
    wire=WireRecorder(RowServer(rows))
    client.rows=VerifiedRows(wire.exchange,wire.server.committed.root,g)
    return client,wire
