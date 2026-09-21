"""Actual CB logical/maintenance operations on authenticated DeadQ routing.

A single level is an integration layer, not yet a complete recursive AB ORAM.
All reads/writes go through VerifiedRows. A caller must schedule public buckets,
perform path/stash placement, and publish application results only after commit.
The old routed allocator and existing performance batches stay unchanged.
"""
from dataclasses import dataclass
from types import SimpleNamespace
import hashlib,secrets,struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ab_deadq_authenticated_store import need,RowServer,WireRecorder,VerifiedRows
from ab_deadq_routed_allocator import Layout,RoutedAllocator,encode_bucket,encode_owner,encode_queue
from cb_oram import Header,Desc,Record,generation
from ab_dummy_first_policy import eligible_slots


@dataclass(frozen=True)
class CBLayout(Layout):
    Z:int=4
    Y:int=2
    address_bound:int=4096
    leaf_bits:int=12
    depth:int=1

    def __post_init__(self):
        super().__post_init__()
        need(1<=self.Z<=self.base and 0<=self.Y<=self.Z,'CB real/green capacities')
        need(self.base-self.Z+self.Y>=1,'positive base consumption threshold')
        need(self.payload_bytes>=24 and self.address_bound>0 and 1<=self.depth<=self.leaf_bits<=30,'CB record geometry')
        need(self.buckets==1<<self.depth,'one complete tree level')
        need(self.base+self.extra<65536,'slot encoding')

    @property
    def original_count(self):return 2+self.buckets+2*self.physical
    @property
    def count(self):return self.original_count+self.buckets
    @property
    def block_bytes(self):return self.payload_bytes-20
    @property
    def private_plain_bytes(self):return ((24+30*self.Z+31)//32)*32
    def head_row(self,b):self.bucket_row(b);return self.original_count+b
    def length(self,index):
        need(0<=index<self.count,'CB row address')
        if index>=self.original_count:return self.private_plain_bytes+28
        return super().length(index)


def pack_record(r,g):
    need(0<r.uid<2**128 and 0<=r.address<g.address_bound and 0<=r.leaf<1<<g.leaf_bits,'CB record fields')
    need(isinstance(r.payload,bytes) and len(r.payload)==g.block_bytes,'CB payload length')
    return r.uid,(r.uid>>64).to_bytes(8,'big')+r.address.to_bytes(8,'big')+r.leaf.to_bytes(4,'big')+r.payload


def unpack_record(packed,g):
    if packed is None:return None
    low,body=packed;need(len(body)==g.payload_bytes,'CB packed length')
    r=Record((int.from_bytes(body[:8],'big')<<64)|low,int.from_bytes(body[8:16],'big'),int.from_bytes(body[16:20],'big'),body[20:])
    pack_record(r,g)
    return r


class CBRoutedLevel(RoutedAllocator):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.headers={};self.cover_records={};self.rebuilding=False;self.drop_target=None;self.new_live={}
        self.events=[];self.prepared_result=None
        self.maintenance_inputs={};self.open_schedule_bucket=None

    def _header_aad(self,b):
        return b'DeadQ-CB-header-v1\x00'+self.domain+struct.pack('>I',b)+self._get(self.g.bucket_row(b))

    def _header(self,b):
        if b in self.headers:return self.headers[b]
        raw=self._get(self.g.head_row(b)) # Merkle authentication before decryption.
        plain=self.aead.decrypt(raw[:12],raw[12:],self._header_aad(b))
        need(len(plain)==self.g.private_plain_bytes,'private header size')
        gamma=int.from_bytes(plain[:16],'big');green,nreal=struct.unpack('>II',plain[16:24])
        epoch,maps,valid=self._bucket(b)
        used=sum(1<<j for j,v in enumerate(valid) if not v);count=used.bit_count()
        live={};need(nreal<=self.g.Z,'CB header capacity')
        for i in range(nreal):
            x=plain[24+30*i:54+30*i]
            uid=int.from_bytes(x[:16],'big');a=int.from_bytes(x[16:24],'big');leaf=int.from_bytes(x[24:28],'big');j=int.from_bytes(x[28:30],'big')
            need(uid>0 and a<self.g.address_bound and leaf<1<<self.g.leaf_bits and j<len(maps) and valid[j] and j not in live,'CB descriptor')
            live[j]=Desc(uid,a,leaf,j)
        need(plain[24+30*nreal:]==bytes(len(plain)-24-30*nreal),'canonical header padding')
        need(len({x.uid for x in live.values()})==len({x.address for x in live.values()})==len(live),'unique live descriptors')
        need(0<=green<=min(self.g.Y,count) and count<=self._threshold(len(maps)),'CB count/green')
        need(gamma==generation(struct.unpack('>Q',self._get(0))[0],self.g.depth,b),'CB placement gamma')
        h=Header(gamma=gamma,w=epoch,count=count,used=used,live=live,green=green);self.headers[b]=h
        return h

    def _threshold(self,n):return n-self.g.Z+self.g.Y

    def _write_header(self,b,h):
        epoch,maps,valid=self._bucket(b);used=sum(1<<j for j,v in enumerate(valid) if not v)
        need(h.used==used and h.count==used.bit_count()<=self._threshold(len(maps)),'directory/header consumption')
        need(0<=h.green<=min(self.g.Y,h.count) and len(h.live)<=self.g.Z,'green/live capacity')
        need(all(0<=j<len(maps) and valid[j] and x.slot==j for j,x in h.live.items()),'live slots unread')
        need(len({x.uid for x in h.live.values()})==len({x.address for x in h.live.values()})==len(h.live),'unique output descriptors')
        plain=h.gamma.to_bytes(16,'big')+struct.pack('>II',h.green,len(h.live))
        for j,x in sorted(h.live.items()):plain+=x.uid.to_bytes(16,'big')+x.address.to_bytes(8,'big')+x.leaf.to_bytes(4,'big')+j.to_bytes(2,'big')
        plain+=bytes(self.g.private_plain_bytes-len(plain));need(self.next_nonce<2**96,'nonce exhaustion')
        nonce=self.next_nonce.to_bytes(12,'big');self.next_nonce+=1
        self._set(self.g.head_row(b),nonce+self.aead.encrypt(nonce,plain,self._header_aad(b)))
        self.headers[b]=h

    def _seal(self,b,j,p,epoch,version,record):
        wire_record=None if record is None else (record[0]&((1<<64)-1),record[1])
        raw=super()._seal(b,j,p,epoch,version,wire_record)
        if record is not None:
            r=unpack_record(record,self.g)
            self.new_live.setdefault(b,{})[j]=Desc(r.uid,r.address,r.leaf,j)
        return raw

    def _read_cover(self,b,selection):
        h=self._header(b);_,maps,valid=self._bucket(b)
        need(len(set(selection))==len(selection) and all(0<=j<len(maps) and valid[j] for j in selection),'cover valid slots')
        # Every selected route and encrypted row is authenticated before ANY
        # selected payload is decrypted. A zero cover still verified its header.
        for j in selection:
            p=maps[j];owner,_=self._owner(p);need(owner==(b,j),'cover owner')
            self._get(self.g.data_row(p))
        records={}
        for j in selection:
            packed=super()._record(b,j,maps[j]);r=unpack_record(packed,self.g);desc=h.live.get(j)
            if desc is None:need(r is None,'dummy/header mismatch')
            else:need(r is not None and (r.uid,r.address,r.leaf)==(desc.uid,desc.address,desc.leaf),'data/header mismatch')
            records[j]=None if r is None else pack_record(r,self.g)
        self.cover_records[b]=records
        return records

    def _record(self,b,j,p):
        if not self.rebuilding:return super()._record(b,j,p)
        h=self._header(b)
        if j not in h.live:return None
        need(j in self.cover_records[b],'all live records covered')
        return None if b==self.drop_target else self.cover_records[b][j]

    def _maintenance_input(self,b):
        if b in self.maintenance_inputs:return self.maintenance_inputs[b]
        group=self._component(b);oldheads={x:self._header(x) for x in sorted(group)};covers={}
        for x,h in oldheads.items():
            _,maps,valid=self._bucket(x);unread=[j for j,v in enumerate(valid) if v]
            filler=[j for j in unread if j not in h.live];k=min(self.g.Z,len(unread))-len(h.live)
            need(0<=k<=len(filler),'public maintenance cover')
            covers[x]=tuple(sorted(list(h.live)+self.placement.sample(filler,k)))
        # Authenticate all buckets' selected rows before decrypting any bucket.
        for x,selection in covers.items():
            _,maps,_=self._bucket(x)
            for j in selection:
                p=maps[j];owner,_=self._owner(p);need(owner==(x,j),'maintenance owner');self._get(self.g.data_row(p))
        for x,selection in covers.items():self._read_cover(x,selection)
        target_records=[unpack_record(self.cover_records[b][j],self.g) for j in sorted(oldheads[b].live)]
        result=(group,oldheads,covers,target_records);self.maintenance_inputs[b]=result
        return result

    def _rebuild_cb(self,b,scheduled,queue,transform=None):
        group,oldheads,covers,target_records=self._maintenance_input(b)
        admissions={}
        if transform is not None:
            need(scheduled,'only scheduled target may be redistributed')
            output=list(transform(tuple(target_records)))
            need(len(output)<=self.g.Z,'scheduled real capacity')
            need(all(r.leaf>>(self.g.leaf_bits-self.g.depth)==b for r in output),'scheduled bucket path')
            admissions[b]=[pack_record(r,self.g) for r in output];self.drop_target=b
        self.new_live={x:{} for x in group};self.rebuilding=True
        try:event=super()._rebuild(b,scheduled,queue,admissions)
        finally:self.rebuilding=False;self.drop_target=None
        for x in sorted(group):
            epoch,maps,valid=self._bucket(x)
            gamma=struct.unpack('>Q',self._get(0))[0] if scheduled and x==b else oldheads[x].gamma
            self._write_header(x,Header(gamma=gamma,w=epoch,live=self.new_live[x]))
        event.update(maintenance_reads={x:list(sel) for x,sel in covers.items()},
            old_gamma={x:h.gamma for x,h in oldheads.items()},new_gamma={x:self.headers[x].gamma for x in group},
            n=len(self._bucket(b)[1]),tau=self._threshold(len(self._bucket(b)[1])))
        self.events.append(event)
        return tuple(target_records)

    def _begin_cb(self):
        need(not self.dead and self.pending is None and self.cache is None,'ready CB level')
        self.rows.begin();self.cache={};self.dirty=set();self.headers={};self.cover_records={};self.events=[];self.new_live={}
        self.maintenance_inputs={};self.open_schedule_bucket=None
        return self._queue()

    def _abort_cb(self):
        self.rows.dead=True;self.cache=None;self.dirty=None;self.pending=None;self.prepared_result=None
        self.headers={};self.cover_records={};self.new_live={};self.maintenance_inputs={};self.open_schedule_bucket=None

    def open_scheduled(self,b):
        """Private maintenance staging; application outputs still wait for ACK.

        The tree opens every scheduled path bucket before choosing placement,
        so records from ancestors can move downwards in the same eviction.
        """
        try:
            queue=self._begin_cb();t=struct.unpack('>Q',self._get(0))[0]
            expected=int(f'{t%self.g.buckets:0{self.g.depth}b}'[::-1],2)
            need(b==expected,'scheduled order')
            records=tuple(self._maintenance_input(b)[3]);self.open_schedule_bucket=(b,queue)
            return records
        except Exception:self._abort_cb();raise

    def stage_scheduled(self,records):
        need(not self.dead and self.open_schedule_bucket is not None and self.pending is None,'open scheduled stage')
        try:
            b,queue=self.open_schedule_bucket;output=tuple(records)
            old=self._rebuild_cb(b,True,queue,lambda previous:output)
            self._set(self.g.queue_row,encode_queue(self.g,queue))
            self.prepared_result=dict(previous_target_records=old)
            self.pending=(dict(operation='scheduled',bucket=b,events=list(self.events)),None)
            self.open_schedule_bucket=None
            return self.pending[0]
        except Exception:self._abort_cb();raise

    def prepare_cb(self,operation,b,address=None,transform=None):
        need(not self.dead and self.pending is None and self.cache is None,'ready CB level')
        try:
            queue=self._begin_cb();result=None;self.g.bucket_row(b)
            if operation=='logical':
                need(address is not None and 0<=address<=self.g.address_bound and transform is None,'logical address')
                h=self._header(b);_,maps,_=self._bucket(b);tau=self._threshold(len(maps))
                if h.count==tau:
                    self._rebuild_cb(b,False,queue);h=self._header(b);_,maps,_=self._bucket(b);tau=self._threshold(len(maps))
                cfg=SimpleNamespace(n=len(maps),Y=self.g.Y)
                choices=eligible_slots(cfg,h,address);j=self.placement.choice(choices)
                packed=self._read_cover(b,(j,))[j];r=unpack_record(packed,self.g)
                consumed,_=super()._consume(b,j,queue)
                if r is not None:
                    h.live.pop(j)
                    if r.address!=address:h.green+=1
                h.count+=1;h.used|=1<<j;self._write_header(b,h)
                consumed.update(n=len(maps),tau=tau,count=h.count,gamma=h.gamma)
                self.events.append(consumed)
                result=dict(target=r if r is not None and r.address==address else None,
                    green=r if r is not None and r.address!=address else None)
            elif operation=='scheduled':
                need(address is None,'scheduled address field')
                old=self._rebuild_cb(b,True,queue,transform)
                result=dict(previous_target_records=old)
            else:raise ValueError('CB operation')
            self._set(self.g.queue_row,encode_queue(self.g,queue))
            self.prepared_result=result;self.pending=(dict(operation=operation,bucket=b,events=list(self.events)),None)
            self.last_workspace=dict(cached_rows=len(self.cache),cached_serialized_bytes=sum(map(len,self.cache.values())),
                dirty_rows=len(self.dirty),decoded_record_payload_bytes=sum(self.g.block_bytes for records in self.cover_records.values() for p in records.values() if p is not None),
                actual_peak=False)
            # Do not return target/green payloads before the final commit ACK.
            return self.pending[0]
        except Exception:
            self._abort_cb()
            raise

    def commit_cb(self):
        result=self.prepared_result
        try:
            event,_=super().commit()
            return event,result
        finally:
            self.prepared_result=None;self.headers={};self.cover_records={};self.new_live={};self.maintenance_inputs={};self.open_schedule_bucket=None

    def apply_cb(self,*args,**kwargs):
        self.prepare_cb(*args,**kwargs)
        return self.commit_cb()


def provision_cb(g,initial_records=None,key=None,placement=None):
    key=key or AESGCM.generate_key(bit_length=256);placement=placement or secrets.SystemRandom()
    geometry=repr(g).encode('ascii');domain=hashlib.sha256(b'DeadQ-CB-instance-v1'+key+geometry).digest()
    initial_records=initial_records or {};need(set(initial_records)<=set(range(g.buckets)),'initial CB buckets')
    allrecords=[r for records in initial_records.values() for r in records]
    need(len({r.uid for r in allrecords})==len({r.address for r in allrecords})==len(allrecords),'unique initial records')
    rows=[struct.pack('>Q',0)]+[encode_bucket(g,0,list(range(b*g.base,(b+1)*g.base)),[True]*g.base) for b in range(g.buckets)]
    rows.extend(encode_owner((p//g.base,p%g.base),0) for p in range(g.physical));rows.append(encode_queue(g,[]))
    c=CBRoutedLevel(None,g,key,domain,0,placement)
    for b in range(g.buckets):
        records=list(initial_records.get(b,()));need(len(records)<=g.Z,'initial CB capacity')
        need(all(r.leaf>>(g.leaf_bits-g.depth)==b for r in records),'initial bucket path')
        records=[pack_record(r,g) for r in records]+[None]*(g.base-len(records));placement.shuffle(records)
        c.new_live[b]={}
        for j,record in enumerate(records):rows.append(c._seal(b,j,b*g.base+j,0,0,record))
    rows.extend(bytes(g.length(g.head_row(b))) for b in range(g.buckets))
    c.cache={i:raw for i,raw in enumerate(rows)};c.dirty=set()
    for b in range(g.buckets):c._write_header(b,Header(live=c.new_live[b]))
    rows=[c.cache[i] for i in range(g.count)];c.cache=None;c.dirty=None;c.headers={};c.new_live={}
    need(all(len(v)==g.length(i) for i,v in enumerate(rows)),'initial CB row format')
    wire=WireRecorder(RowServer(rows));c.rows=VerifiedRows(wire.exchange,wire.server.committed.root,g)
    return c,wire
