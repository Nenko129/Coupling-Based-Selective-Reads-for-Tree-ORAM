"""A real static tree-top cache: only remote frames cross the counted boundary.

The original ORAM sees an equivalent logical RPC. Top records are stored only
in the client cache; the remote parser has no references to that cache.
"""
from common import *
from collections import Counter,defaultdict
import heterogeneous_oram as h

CUTS={}

def layout(c,b):return c.at(b) if hasattr(c,'at') else c
def path(c,leaf):return [h.node(leaf,d,c.L) for d in range(c.L+1)]
def split_init(c,body):
    q=h.Cursor(body);b=q.uint();bc=layout(c,b)
    h.need(1<=b<1<<(c.L+1),'init bucket bounds')
    if c.rootless and b==1:st=h.Stored(b'',[],{},q.take(h.TAG))
    else:
        hd=q.take(bc.H);slots=[q.take(c.W) for _ in range(bc.n)]
        local={p:q.take(h.TAG) for p in h.local_indices(bc.n)} if c.ring else {}
        st=h.Stored(hd,slots,local,q.take(h.TAG))
    tag=q.take(h.TAG);q.end();return b,st,tag

def write_piece(c,b,q,full,old):
    bc=layout(c,b);hd=q.take(bc.H)
    slots=[q.take(c.W) for _ in range(bc.n)] if full else old.slots
    tags={p:q.take(h.TAG) for p in h.local_indices(bc.n)} if full and c.ring else old.local
    bt=q.take(h.TAG)
    return h.Stored(hd,slots,tags,bt)

def serialize_piece(c,b,item,full):
    bc=layout(c,b)
    return item.header+(b''.join(item.slots) if full else b'')+(b''.join(item.local[p] for p in h.local_indices(bc.n)) if full and c.ring else b'')+item.bucket_tag

class RemoteServer:
    """Only below-cut ciphertext objects; no private cache access or plaintext."""
    def __init__(self,configs):
        self.configs={c.tree:c for c in configs};self.cuts={c.tree:CUTS.get(c.tree,0) for c in configs}
        for c in configs:h.need(0<=self.cuts[c.tree]<=c.L,'keep at least one remote level')
        self.buckets={};self.global_tags={}
    def handle(self,raw):
        op,tree,seq,flags,body=h.parse_frame(raw);h.need(flags==0 and tree in self.configs,'remote routing')
        c=self.configs[tree];cut=self.cuts[tree];q=h.Cursor(body);out=b''
        if op==h.INIT:
            b,st,gt=split_init(c,body);h.need(h.depth(b)>=cut,'cached bucket sent remotely')
            self.buckets[tree,b]=st;self.global_tags[tree,b]=gt
        else:
            leaf=q.uint();ds=h.from_bitmap(q.uint(),c.L+1)
            h.need(0<=leaf<1<<c.L and all(d>=cut for d in ds),'remote path/cut')
            h.need(not c.rootless or 0 not in ds,'rootless selection');pp=path(c,leaf)
            if op in (h.OPEN_FULL,h.OPEN_HEAD):
                q.end()
                for d in ds:
                    item=self.buckets[tree,pp[d]];out+=item.header
                    out+=b''.join(item.slots) if op==h.OPEN_FULL else item.local[1]
                for d in range(cut,c.L+1):
                    if d not in ds and not(c.rootless and d==0):out+=self.buckets[tree,pp[d]].bucket_tag
                for d in range(max(0,cut-1),c.L):out+=self.global_tags[tree,pp[d+1]^1]
            elif op==h.READ_SLOTS:
                h.need(c.ring and bool(ds),'remote slot read shape')
                for d in ds:
                    b=pp[d];bc=layout(c,b);inds=h.from_bitmap(q.uint(),bc.n);h.need(bool(inds),'empty slots')
                    item=self.buckets[tree,b];out+=b''.join(item.slots[j] for j in inds)
                    out+=b''.join(item.local[p] for p in h.witnesses(bc.n,inds))
                q.end()
            elif op==h.WRITE:
                h.need(bool(ds),'empty remote write');full=h.from_bitmap(q.uint(),c.L+1);h.need(set(full)<=set(ds),'full subset')
                pending={}
                for d in ds:
                    b=pp[d];pending[tree,b]=write_piece(c,b,q,d in full,self.buckets[tree,b])
                tags={(tree,pp[d]):q.take(h.TAG) for d in range(cut,max(ds)+1)};q.end()
                self.buckets.update(pending);self.global_tags.update(tags)
            else:raise h.Reject('unknown remote op')
        return h.frame(op,tree,seq,out,True)

class CachedTransport:
    def __init__(self,server):
        self.server=server;self.seq=0;self.wire_seq=0;self.mutator=None
        self.local_buckets={};self.local_tags={};self.capture_limit=0;self.events=[];self.logical_events=[]
        self.total=Counter();self.reset_meter()
    def reset_meter(self):
        self.components=Counter();self.stage=defaultdict(Counter);self.tree=defaultdict(Counter);self.opcodes=Counter()
        self.rpc_count=0;self.local_calls=0;self.up=0;self.down=0;self.transcript=hashlib.sha256();self.first_seq=self.wire_seq
    def _wire(self,c,op,body,stage,meta):
        seq=self.wire_seq;self.wire_seq+=1;req=h.frame(op,c.tree,seq,body);res=self.server.handle(req)
        if self.mutator is not None:res=self.mutator(c,op,seq,stage,meta,req,res)
        e=dict(sequence=seq,tree=c.tree,stage=stage,opcode=op,request_bytes=len(req),response_bytes=len(res),
               request_sha256=hashlib.sha256(req).hexdigest(),response_sha256=hashlib.sha256(res).hexdigest(),**meta)
        comp=wire_invoice(c,self.server.cuts[c.tree],e)
        h.need(sum(comp.values())==len(req)+len(res),'cache boundary invoice mismatch')
        e['components']=comp
        if len(self.events)<self.capture_limit:self.events.append(e)
        for key in ('request_sha256','response_sha256'):self.transcript.update(bytes.fromhex(e[key]))
        self.components.update(comp);self.total.update(comp);self.stage[stage].update(comp);self.tree[str(c.tree)].update(comp)
        self.opcodes[str(op)]+=1;self.rpc_count+=1;self.up+=len(req);self.down+=len(res)
        ro,rt,rs,rf,result=h.parse_frame(res);h.need((ro,rt,rs,rf)==(op,c.tree,seq,1),'cache boundary routing/replay')
        return result
    def rpc(self,c,op,body,stage,meta,components):
        seq=self.seq;self.seq+=1;cut=self.server.cuts[c.tree];result=self._logical(c,op,body,stage,meta,cut)
        if len(self.logical_events)<self.capture_limit:
            req=h.frame(op,c.tree,seq,body);res=h.frame(op,c.tree,seq,result,True)
            self.logical_events.append((hashlib.sha256(req).hexdigest(),hashlib.sha256(res).hexdigest()))
        return result
    def _logical(self,c,op,body,stage,meta,cut):
        if op==h.INIT:
            b,st,gt=split_init(c,body)
            if h.depth(b)<cut:
                self.local_buckets[c.tree,b]=st;self.local_tags[c.tree,b]=gt;self.local_calls+=1;return b''
            return self._wire(c,op,body,stage,meta)
        q=h.Cursor(body);leaf=q.uint();ds=h.from_bitmap(q.uint(),c.L+1);pp=path(c,leaf);cold=tuple(d for d in ds if d>=cut)
        if op in (h.OPEN_FULL,h.OPEN_HEAD):
            q.end();wiremeta=dict(meta,depths=list(cold))
            reply=self._wire(c,op,h.ui(leaf,8)+h.ui(h.bitmap(cold),8),stage,wiremeta);r=h.Cursor(reply);pieces={};btags={};siblings={}
            for d in cold:
                bc=layout(c,pp[d]);pieces[d]=r.take(bc.H+(bc.n*c.W if op==h.OPEN_FULL else h.TAG))
            for d in range(cut,c.L+1):
                if d not in cold and not(c.rootless and d==0):btags[d]=r.take(h.TAG)
            for d in range(max(0,cut-1),c.L):siblings[d]=r.take(h.TAG)
            r.end();out=b''
            for d in ds:
                if d>=cut:out+=pieces[d]
                else:
                    st=self.local_buckets[c.tree,pp[d]];out+=st.header+(b''.join(st.slots) if op==h.OPEN_FULL else st.local[1])
            for d in range(c.L+1):
                if d not in ds and not(c.rootless and d==0):
                    out+=self.local_buckets[c.tree,pp[d]].bucket_tag if d<cut else btags[d]
            for d in range(c.L):out+=self.local_tags[c.tree,pp[d+1]^1] if d+1<cut else siblings[d]
            return out
        if op==h.READ_SLOTS:
            selection={d:h.from_bitmap(q.uint(),layout(c,pp[d]).n) for d in ds};q.end();parts={}
            if cold:
                wire=h.ui(leaf,8)+h.ui(h.bitmap(cold),8)+b''.join(h.ui(h.bitmap(selection[d]),8) for d in cold)
                reply=self._wire(c,op,wire,stage,dict(meta,depths=list(cold),slots=[list(selection[d]) for d in cold]));r=h.Cursor(reply)
                for d in cold:
                    bc=layout(c,pp[d]);parts[d]=r.take(len(selection[d])*c.W+len(h.witnesses(bc.n,selection[d]))*h.TAG)
                r.end()
            else:self.local_calls+=1
            out=b''
            for d in ds:
                if d>=cut:out+=parts[d]
                else:
                    st=self.local_buckets[c.tree,pp[d]];bc=layout(c,pp[d]);inds=selection[d]
                    out+=b''.join(st.slots[j] for j in inds)+b''.join(st.local[p] for p in h.witnesses(bc.n,inds))
            return out
        if op==h.WRITE:
            full=h.from_bitmap(q.uint(),c.L+1);local={};coldpieces={}
            for d in ds:
                b=pp[d];bc=layout(c,b)
                # Remote pieces are opaque here. Header-only writes do not fetch
                # a remote old bucket into the client cache.
                size=bc.H+h.TAG+((bc.n*c.W+(len(h.local_indices(bc.n))*h.TAG if c.ring else 0)) if d in full else 0)
                piece=q.take(size)
                if d<cut:
                    parse=h.Cursor(piece);local[c.tree,b]=write_piece(c,b,parse,d in full,self.local_buckets[c.tree,b]);parse.end()
                else:coldpieces[d]=piece
            tags={d:q.take(h.TAG) for d in range(max(ds)+1)};q.end()
            if cold:
                wire=h.ui(leaf,8)+h.ui(h.bitmap(cold),8)+h.ui(h.bitmap(set(full)&set(cold)),8)
                wire+=b''.join(coldpieces[d] for d in cold)+b''.join(tags[d] for d in range(cut,max(cold)+1))
                reply=self._wire(c,op,wire,stage,dict(meta,depths=list(cold),full_depths=[d for d in full if d>=cut]))
                h.need(reply==b'','cache write ack')
            else:self.local_calls+=1
            # Commit trusted cached objects only after any remote ACK passed.
            self.local_buckets.update(local)
            self.local_tags.update({(c.tree,pp[d]):tag for d,tag in tags.items() if d<cut})
            return b''
        raise h.Reject('cache logical op')
    def snapshot(self):
        return dict(rpc=self.rpc_count,request_bytes=self.up,response_bytes=self.down,total_bytes=self.up+self.down,
             components=dict(self.components),by_stage={k:dict(v) for k,v in self.stage.items()},by_tree={k:dict(v) for k,v in self.tree.items()},
             opcode_counts=dict(self.opcodes),transcript_sha256=self.transcript.hexdigest(),first_sequence=self.first_seq,next_sequence=self.wire_seq,
             independently_invoiced_rpcs=self.rpc_count,retained_event_count=len(self.events),local_only_rpcs=self.local_calls,
             scope='actual frames through separate below-cut server parser; client cache excluded from remote object store')
    def cache_storage(self):
        return dict(bucket_records=len(self.local_buckets),global_tag_records=len(self.local_tags),
                    bytes=sum(len(s.header)+sum(map(len,s.slots))+sum(map(len,s.local.values()))+len(s.bucket_tag) for s in self.local_buckets.values())+sum(map(len,self.local_tags.values())))

def wire_invoice(c,cut,e):
    """Lengths from public operation/masks/layout, independent of response bytes."""
    v=Counter({key:0 for key in ('data_download','data_upload','headers_download','headers_upload','authentication_download','authentication_upload','framing_and_control')})
    op=e['opcode']
    if op==h.INIT:
        bc=layout(c,e['bucket']);empty=c.rootless and e['bucket']==1
        v['headers_upload']=0 if empty else bc.H;v['data_upload']=0 if empty else bc.n*c.W
        v['authentication_upload']=h.TAG*(2+(len(h.local_indices(bc.n)) if c.ring and not empty else 0))
        v['framing_and_control']=2*h.FRAME+8
    else:
        ds=e['depths'];bc={d:layout(c,1<<d) for d in ds};k=len(ds)
        if op in (h.OPEN_FULL,h.OPEN_HEAD):
            v['headers_download']=sum(bc[d].H for d in ds)
            v['data_download']=sum(bc[d].n*c.W for d in ds) if op==h.OPEN_FULL else 0
            remote_levels=sum(d>=cut for d in c.levels)
            v['authentication_download']=h.TAG*(remote_levels-k+(k if op==h.OPEN_HEAD else 0)+c.L-max(0,cut-1))
            v['framing_and_control']=2*h.FRAME+16
        elif op==h.READ_SLOTS:
            v['data_download']=sum(len(x) for x in e['slots'])*c.W
            v['authentication_download']=sum(len(h.witnesses(bc[d].n,tuple(s))) for d,s in zip(ds,e['slots']))*h.TAG
            v['framing_and_control']=2*h.FRAME+16+8*k
        elif op==h.WRITE:
            full=e['full_depths'];v['headers_upload']=sum(bc[d].H for d in ds);v['data_upload']=sum(bc[d].n*c.W for d in full)
            v['authentication_upload']=h.TAG*(k+max(ds)-cut+1+sum(len(h.local_indices(bc[d].n)) for d in full if c.ring))
            v['framing_and_control']=2*h.FRAME+24
        else:raise AssertionError(op)
    return dict(v)

def install(cuts):
    global CUTS
    CUTS=dict(cuts);h.Server=RemoteServer;h.Transport=CachedTransport
