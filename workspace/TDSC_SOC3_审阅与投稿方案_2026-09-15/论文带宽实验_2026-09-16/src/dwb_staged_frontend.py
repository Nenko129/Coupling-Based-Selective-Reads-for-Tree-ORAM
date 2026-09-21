"""Interruptible inclusive writeback over authenticated raw-map Transfer.

This implements the cross-slot DWB interface, not the IR-Stash allocator,
compressed counter reset, a CPU controller, or a latency experiment.
"""
from common import *
import composition_runtime as runtime
from transfer_backend import Reject,need
from frontends import FreecursiveFront,CachedMap
from dataclasses import dataclass


class StagedRawMapFront(FreecursiveFront):
    def __init__(self,*args,**kwargs):
        kwargs['compressed']=False
        super().__init__(*args,**kwargs)
        self.pending_writeback=None

    def _reserve_staged(self,level,i):
        if level==len(self.counts)-1:
            old=self.top[i];new=self.leaves.fresh('top-remap');self.top[i]=new
            return old,new
        parent_i,j=divmod(i,self.X)
        parent=yield from self._ensure_staged(level+1,parent_i)
        self.pinned.add(parent.address)
        try:
            old=int.from_bytes(parent.data[4*j:4*j+4],'big')
            new=self.leaves.fresh('raw-remap')
            parent.data=parent.data[:4*j]+new.to_bytes(4,'big')+parent.data[4*j+4:]
            return old,new
        finally:self.pinned.remove(parent.address)

    def _ensure_staged(self,level,i):
        a=self.addr(level,i)
        if a in self.cache:
            self.metrics['plb_hits']+=1;self.cache.move_to_end(a)
            return self.cache[a]
        self.metrics['plb_misses']+=1
        old,new=yield from self._reserve_staged(level,i)
        victim=None
        if len(self.cache)>=self.capacity:
            candidates=[k for k in self.cache if k not in self.pinned]
            need(bool(candidates),'PLB space for staged recursion')
            victim=self.cache.pop(candidates[0]);self.metrics['plb_evictions']+=1
        admission=None if victim is None else (victim.address,victim.parked_leaf,victim.data)
        payload=self.backend.tick(a,old,admit=admission)
        entry=CachedMap(a,payload,new);self.cache[a]=entry
        need(len(self.cache)<=self.capacity,'PLB capacity')
        # No yield between changing the parent leaf and acquiring this child.
        # At this suspension point the child has one owner and a parked leaf.
        yield dict(type='posmap',level=level,address=a)
        return entry

    def _writeback_steps(self,a,value):
        old,new=yield from self._reserve_staged(0,a)
        prior=self.backend.tick(a,old,replace=(new,lambda p:value))
        yield dict(type='data',level=0,address=a,previous=prior)

    def access(self,a,value=None):
        if self.pending_writeback is not None:self.pending_writeback.cancel('foreground')
        return super().access(a,value)


@dataclass
class DirtyEntry:
    address:int
    payload:bytes
    version:int=0
    dirty:bool=True


class StagedWriteback:
    """Client-selected candidate; is_current tests version, residency and LRU.

    An external public-slot scheduler owns when advance() may run. A False
    result performs no I/O; that scheduler must emit the required dummy slot.
    Foreground preemption cancels this object before ordinary access begins.
    """
    def __init__(self,front,entry,is_current):
        need(not front.dead and front.pending_writeback is None,'writeback already active or stopped')
        need(entry.dirty and 0<=entry.address<front.N and len(entry.payload)==front.B,'dirty candidate')
        self.front=front;self.entry=entry;self.version=entry.version;self.value=entry.payload
        self.is_current=is_current;self.steps=front._writeback_steps(entry.address,self.value)
        self.state='pending';self.events=[];self.reason=None;front.pending_writeback=self

    def cancel(self,reason):
        if self.state!='pending':return
        self.steps.close();self.state='cancelled';self.reason=reason
        self.front.pending_writeback=None
        # Already authenticated map removals/remaps and cache effects are kept.

    def advance(self):
        if self.front.dead:raise Reject('fail-stop staged writeback')
        if self.state!='pending':return False
        if not self.entry.dirty or self.entry.version!=self.version or self.entry.payload!=self.value or not self.is_current(self.entry):
            self.cancel('candidate changed');return False
        before=self.front.backend.tree.t
        try:
            event=next(self.steps)
            need(self.front.backend.tree.t==before+1,'each advance commits exactly one backend slot')
            self.events.append(event)
            if event['type']=='data':
                # tick returned only after data, maintenance and ACK verification.
                need(self.entry.version==self.version and self.entry.payload==self.value and self.is_current(self.entry),'candidate changed during serial commit')
                self.entry.dirty=False;self.state='committed';self.front.metrics['dwb_completed']+=1
                self.steps.close();self.front.pending_writeback=None
            else:self.front.metrics['dwb_posmap_slots']+=1
            return True
        except Exception:
            self.front.dead=True;self.front.backend.tree.dead=True;self.state='failed'
            self.front.pending_writeback=None
            self.steps.close()
            raise


def identity():
    return dict(base=runtime.identity(),staged={n:sha(Path(__file__).parent/n) for n in ('dwb_staged_frontend.py','transfer_backend_fixed.py','fast_prf.py')})
