"""Behavioral IR-Stash extension: address/set + bucket indices, local hits.

Canonical payload remains in the already counted trusted encrypted top cache;
the new index stores descriptors only. This is a protocol reference, not a
claim to reproduce SRAM area/energy or the paper's exact physical organization.
"""
from common import *
from collections import Counter
from dataclasses import dataclass
import hashlib,hmac
import heterogeneous_oram as h
import cached_transport as cache
from ir_transfer import TransferConfig,TransferTree

@dataclass(frozen=True)
class StashConfig(TransferConfig):
    index_sets:int=64
    index_ways:int=4
    indexed:bool=True
    def __post_init__(self):
        super().__post_init__()
        if self.kind not in ('path','deferred','sde'):raise ValueError('IR-Stash first interface is Path/Deferred/SDE')
        if self.index_sets<1 or self.index_ways<1:raise ValueError('positive S-Stash geometry')
    def context(self):
        return h.encode(b'IR-STASH-LOCAL-HIT-v1',super().context(),
            h.ui(self.index_sets,8),h.ui(self.index_ways,8),h.ui(int(self.indexed),1))

class DualIndex:
    """TT-style bucket descriptors and bounded MD5(address) set index."""
    def __init__(self,sets,ways,enforced=True):
        self.sets=[{} for _ in range(sets)];self.ways=ways;self.enforced=enforced;self.buckets={}
    def which(self,a):
        # Public address-to-set hash, not a cryptographic security primitive.
        return int.from_bytes(hashlib.md5(a.to_bytes(8,'big')).digest(),'big')%len(self.sets)
    def lookup(self,a):return self.sets[self.which(a)].get(a)
    def outside_counts(self,replaced):
        return [sum(1 for b,d in group.values() if b not in replaced) for group in self.sets]
    def projected(self,changes):
        buckets={b:dict(ds) for b,ds in self.buckets.items() if b not in changes}
        buckets.update({b:dict(header.live) for b,header in changes.items()})
        groups=[{} for _ in self.sets]
        for b,ds in buckets.items():
            for j,d in ds.items():
                h.need(j==d.slot,'index descriptor slot')
                g=groups[self.which(d.address)]
                h.need(d.address not in g,'duplicate top address')
                g[d.address]=(b,d)
        if self.enforced:h.need(all(len(g)<=self.ways for g in groups),'S-Stash set overflow')
        return buckets,groups
    def replace(self,changes):
        self.buckets,self.sets=self.projected(changes)
    def snapshot(self):
        return {a:(b,d.slot,d.uid,d.leaf) for group in self.sets for a,(b,d) in group.items()}

class AnchoredTransport(cache.CachedTransport):
    """Trusted cut-root anchors enable local writes without fetching a path."""
    def __init__(self,server):
        super().__init__(server);self.cut_roots={}
    def _logical(self,c,op,body,stage,meta,cut):
        result=super()._logical(c,op,body,stage,meta,cut)
        if op==h.INIT:
            b,st,gt=cache.split_init(c,body)
            if h.depth(b)==cut:self.cut_roots[c.tree,b]=gt
        return result
    def cache_storage(self):
        result=super().cache_storage()
        result.update(cut_anchor_records=len(self.cut_roots),cut_anchor_bytes=sum(map(len,self.cut_roots.values())))
        result['bytes']+=result['cut_anchor_bytes']
        return result

class StashTree(TransferTree):
    def __init__(self,c,p,io):
        super().__init__(c,p,io);self.cut=io.server.cuts[c.tree]
        h.need(self.cut>=1,'IR-Stash requires cached top')
        self.index=DualIndex(c.index_sets,c.index_ways,c.indexed);self.local_metrics=Counter()
    def write(self,view,changes,stage):
        cached={b:x[0] for b,x in changes.items() if h.depth(b)<self.cut}
        projected=self.index.projected(cached)
        super().write(view,changes,stage)
        # All index and boundary-root updates follow authenticated write ACK.
        self.index.buckets,self.index.sets=projected
        if self.cut in view.selected or max(view.selected)>=self.cut:
            b=h.node(view.leaf,self.cut,self.c.L)
            self.io.cut_roots[self.c.tree,b]=view.path_tags[b]
    def placement(self,pool,view,gamma,constrained):
        c=self.c;changes={};replaced={h.node(view.leaf,d,c.L) for d in view.selected if d<self.cut}
        occupied=self.index.outside_counts(replaced)
        for d in reversed(view.selected):
            b=h.node(view.leaf,d,c.L);chosen=[]
            for r in sorted(pool.values(),key=lambda x:x.uid):
                if h.node(r.leaf,d,c.L)!=b or (constrained and d not in h.gc(gamma,r.leaf,c.L)):continue
                if d<self.cut and c.indexed:
                    k=self.index.which(r.address)
                    if occupied[k]>=c.index_ways:self.local_metrics['placement_set_conflicts']+=1;continue
                    occupied[k]+=1
                chosen.append(r)
                if len(chosen)==c.at(b).Z:break
            for r in chosen:pool.pop(r.uid)
            changes[b]=self.prepare(b,view.headers[b],chosen,gamma)
        self.write(view,changes,'path' if c.kind=='path' else 'evict')
        self.stash={r.address:r for r in pool.values()}
    def _top_root(self,replacement=None):
        tags={b:tag for (tree,b),tag in self.io.cut_roots.items() if tree==self.c.tree}
        for b in range((1<<self.cut)-1,0,-1):
            item=self.io.local_buckets[self.c.tree,b]
            bt=replacement[1] if replacement is not None and b==replacement[0] else item.bucket_tag
            tags[b]=self.ntag(b,bt,tags[2*b],tags[2*b+1])
        return tags[1],tags
    def _local_records(self,b):
        # Even trusted object format/authentication is checked before payload
        # decryption. No server object or remote plaintext is inspected.
        root,tags=self._top_root();h.need(hmac.compare_digest(root,self.root),'stale local anchor')
        item=self.io.local_buckets[self.c.tree,b];D=self.droot(b,item.slots)
        h.need(hmac.compare_digest(self.btag(b,item.header,D),item.bucket_tag),'local bucket authentication')
        pub=item.header[:h.PUBLIC]
        plain=self.P.decrypt(self.ctx,self.oid(b),pub,item.header[h.PUBLIC:])
        header=h.Header.decode(self.c.at(b),pub,plain)
        h.need(header.live==self.index.buckets.get(b,{}),'TT/current header disagreement')
        records=[h.Record(d.uid,d.address,d.leaf,self.P.decrypt(self.ctx,self.oid(b,j),h.ui(header.w),item.slots[j]))
                 for j,d in sorted(header.live.items())]
        return header,records
    def find_local(self,address,*,leaf=None):
        h.need(0<=address<self.c.N,'local address')
        if address in self.stash:return ('F',None,None)
        if self.c.indexed:
            found=self.index.lookup(address)
            if found is not None:return ('S',found[0],found[1])
        elif leaf is not None:
            for d in range(self.cut):
                b=h.node(leaf,d,self.c.L)
                for desc in self.index.buckets.get(b,{}).values():
                    if desc.address==address:return ('S',b,desc)
        return None
    def local_access(self,address,value=None,*,leaf=None):
        """None means miss; (payload, location) means hit without remapping.

        On dedicated-top baseline, callers must resolve leaf before an S hit.
        F hits are visible without a position lookup in both modes.
        """
        if self.dead:raise h.Reject('fail-stop IR-Stash')
        h.need(not self.busy,'reentrant local IR-Stash')
        self.busy=True
        try:
            h.need(value is None or isinstance(value,bytes) and len(value)==self.c.B,'local value size')
            found=self.find_local(address,leaf=leaf)
            self.local_metrics['local_probes']+=1
            if found is None:return None
            region,b,desc=found
            if region=='F':
                record=self.stash[address];prior=record.payload
                if value is not None:self.stash[address]=h.Record(record.uid,address,record.leaf,value)
            else:
                old,records=self._local_records(b)
                record=next(r for r in records if r.address==address);prior=record.payload
                h.need((record.uid,record.leaf)==(desc.uid,desc.leaf),'index target disagreement')
                if value is not None:
                    updated=[h.Record(r.uid,r.address,r.leaf,value if r.address==address else r.payload) for r in records]
                    prepared=self.prepare(b,old,updated,old.gamma)
                    header,hd,slots,local,D=prepared;bt=self.btag(b,hd,D)
                    root,tags=self._top_root((b,bt));projected=self.index.projected({b:header})
                    self.io.local_buckets[self.c.tree,b]=h.Stored(hd,slots,local,bt)
                    self.io.local_tags.update({(self.c.tree,k):tag for k,tag in tags.items() if h.depth(k)<self.cut})
                    self.index.buckets,self.index.sets=projected;self.root=root
            self.local_metrics[region+'_hits']+=1
            if value is not None:self.local_metrics['local_payload_updates']+=1
            return prior,region
        except Exception:
            self.dead=True;raise
        finally:self.busy=False
    def index_representation(self):
        entries=sum(map(len,self.index.sets))
        return dict(indexed=self.c.indexed,set_count=self.c.index_sets,ways=self.c.index_ways,
            current_real_entries=entries,descriptor_entry_bytes=38,descriptor_bytes=38*entries,
            payload_copy_bytes=0,encrypted_top_payload_is_canonical=True,
            dedicated_control_retains_same_test_index=True,actual_peak_measured=False)

