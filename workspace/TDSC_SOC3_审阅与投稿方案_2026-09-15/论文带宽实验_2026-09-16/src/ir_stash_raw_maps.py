"""Raw-map IR-Stash bypass at every recursion level.

A locally resident map remains canonical in F/S-Stash and is updated through
an ephemeral handle. Only remote map fetches move ownership into the PLB.
No local handle may be used after a Transfer or be saved in the PLB.
"""
from common import *
import heterogeneous_oram as h
from frontends import CachedMap
from ir_stash_frontend import StashDataFront


class LocalMap:
    def __init__(self,front,address,leaf):
        self.front=front;self.address=address;self.leaf=leaf
        self.created_at=front.backend.tree.t
    def _check(self):
        h.need(self.front.backend.tree.t==self.created_at,'local map handle crossed a Transfer')
        h.need(self.address not in self.front.cache,'local map cannot also have PLB ownership')
    @property
    def data(self):
        self._check();result=self.front.backend.local_access(self.address,leaf=self.leaf)
        h.need(result is not None,'local map ceased to be local within serial step')
        return result[0]
    @data.setter
    def data(self,value):
        self._check();result=self.front.backend.local_access(self.address,value,leaf=self.leaf)
        h.need(result is not None,'local map write lost canonical owner')
        self.front.metrics['local_map_payload_updates']+=1


class StashRawMapsFront(StashDataFront):
    def _lookup_raw_leaf(self,level,i):
        if level==len(self.counts)-1:return self.top[i],None,i
        parent_i,j=divmod(i,self.X)
        parent=yield from self._ensure_staged(level+1,parent_i)
        raw=parent.data
        return int.from_bytes(raw[4*j:4*j+4],'big'),parent,j

    def _lookup_data_leaf(self,a):
        return (yield from self._lookup_raw_leaf(0,a))

    def _ensure_staged(self,level,i):
        a=self.addr(level,i)
        if a in self.cache:
            self.metrics['plb_hits']+=1;self.cache.move_to_end(a);return self.cache[a]
        self.metrics['plb_misses']+=1
        found=self.backend.tree.find_local(a)
        if found is not None:
            # F descriptors and S index metadata are trusted, not a PosMap read.
            leaf=self.backend.tree.stash[a].leaf if found[0]=='F' else found[2].leaf
            h.need(self.backend.local_access(a,leaf=leaf) is not None,'local map probe changed')
            self.metrics['map_local_'+found[0]+'_before_parent']+=1
            return LocalMap(self,a,leaf)
        old,parent,j=yield from self._lookup_raw_leaf(level,i)
        hit=self.backend.local_access(a,leaf=old)
        if hit is not None:
            self.metrics['map_local_'+hit[1]+'_after_parent']+=1
            return LocalMap(self,a,old)
        # Only this branch creates a parked new map leaf and removes the map
        # from the backend. Parent updates are committed before the Transfer;
        # an error stops the frontend so a half-reservation cannot be reused.
        new=self.leaves.fresh('top-remap' if parent is None else 'raw-remap')
        if parent is None:self.top[j]=new
        else:
            raw=parent.data;parent.data=raw[:4*j]+new.to_bytes(4,'big')+raw[4*j+4:]
            self.pinned.add(parent.address)
        try:
            victim=None
            if len(self.cache)>=self.capacity:
                candidates=[x for x in self.cache if x not in self.pinned]
                h.need(bool(candidates),'PLB space for local-map recursion')
                victim=self.cache.pop(candidates[0]);self.metrics['plb_evictions']+=1
            admit=None if victim is None else (victim.address,victim.parked_leaf,victim.data)
            payload=self.backend.tick(a,old,admit=admit)
            entry=CachedMap(a,payload,new);self.cache[a]=entry
            self.metrics['map_remote_removals']+=1
            h.need(len(self.cache)<=self.capacity,'PLB capacity')
        finally:
            if parent is not None:self.pinned.remove(parent.address)
        # No LocalMap handle is read or mutated beyond this suspension point.
        yield dict(type='posmap',level=level,address=a,transfers=1)
        return entry


def identity():
    import ir_stash_frontend
    return dict(data_bridge=ir_stash_frontend.identity(),raw_maps_sha256=sha(__file__))
