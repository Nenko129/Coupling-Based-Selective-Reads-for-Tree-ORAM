"""Interruptible compressed position maps with persistent bounded group reset.

One committed Transfer per step. A cancelled DWB may leave a mandatory group
reset, which must finish before another map lookup; cancellation never rolls
back a remap. The reset descriptor and pinned parent define the mapping of
already processed children until the group header is committed locally.
"""
from common import *
from collections import Counter
from dataclasses import dataclass
from frontends import FreecursiveFront,CachedMap
from transfer_backend import need,Reject
from dwb_staged_frontend import StagedWriteback


@dataclass
class GroupReset:
    level:int
    parent_i:int
    parent:CachedMap
    group:int
    cursor:int=0


class StagedCompressedFront(FreecursiveFront):
    def __init__(self,*args,**kwargs):
        kwargs['compressed']=True
        super().__init__(*args,**kwargs)
        self.pending_writeback=None;self.pending_reset=None;self.pin_counts=Counter()

    def _pin(self,a):
        self.pin_counts[a]+=1;self.pinned.add(a)

    def _unpin(self,a):
        need(self.pin_counts[a]>0,'unbalanced compressed-map pin')
        self.pin_counts[a]-=1
        if not self.pin_counts[a]:del self.pin_counts[a];self.pinned.remove(a)

    def _start_reset(self,level,parent_i,parent):
        need(self.pending_reset is None,'nested group reset')
        group,counts=self.decode_map(parent.data)
        need(group<(1<<64)-1,'group counter exhausted before I/O')
        self._pin(parent.address)
        self.pending_reset=GroupReset(level,parent_i,parent,group)
        self.metrics['group_resets']+=1

    def advance_reset(self):
        """Return an event iff one real Transfer committed, else no I/O occurred.

        Local cached-child rotations are unclocked client work. A real-child
        rotation is followed immediately by descriptor cursor advancement; the
        authenticated parent payload stays at its old group until completion.
        """
        if self.dead:raise Reject('fail-stop compressed reset')
        reset=self.pending_reset
        if reset is None:return None
        try:
            parent=reset.parent
            need(self.cache.get(parent.address) is parent and parent.address in self.pinned,'reset parent ownership')
            group,counts=self.decode_map(parent.data);need(group==reset.group,'reset group changed')
            stop=min(self.X,self.counts[reset.level]-reset.parent_i*self.X)
            while reset.cursor<stop:
                j=reset.cursor;a=self.addr(reset.level,reset.parent_i*self.X+j)
                old=self.leaves.named('compressed-leaf',a,group,counts[j])
                new=self.leaves.named('compressed-leaf',a,group+1,0)
                event=None
                if a in self.cache:
                    need(self.cache[a].parked_leaf==old,'cached group leaf mismatch')
                    self.cache[a].parked_leaf=new;self.metrics['group_cached_rotations']+=1
                else:
                    before=self.backend.tree.t
                    self.backend.tick(a,old,replace=(new,lambda p:p))
                    need(self.backend.tree.t==before+1,'reset rotation must occupy one Transfer')
                    self.metrics['group_backend_slots']+=1
                    event=dict(type='group_reset',level=reset.level,address=a)
                reset.cursor+=1
                if reset.cursor==stop:
                    parent.data=self.encode_map(reset.level+1,reset.parent_i,group+1,[0]*self.X)
                    self.pending_reset=None;self._unpin(parent.address);self.metrics['group_resets_completed']+=1
                if event is not None:return event
            return None
        except Exception:
            self.dead=True;self.backend.tree.dead=True;raise

    def _reserve_staged(self,level,i):
        if level==len(self.counts)-1:
            old=self.top[i];new=self.leaves.fresh('top-remap');self.top[i]=new
            return old,new
        parent_i,j=divmod(i,self.X)
        parent=yield from self._ensure_staged(level+1,parent_i)
        self._pin(parent.address)
        try:
            group,counts=self.decode_map(parent.data)
            if counts[j]==(1<<self.beta)-1:
                self._start_reset(level,parent_i,parent)
                while self.pending_reset is not None:
                    event=self.advance_reset()
                    if event is not None:yield event
                group,counts=self.decode_map(parent.data)
            a=self.addr(level,i);old=self.leaves.named('compressed-leaf',a,group,counts[j])
            counts[j]+=1;new=self.leaves.named('compressed-leaf',a,group,counts[j])
            parent.data=self.encode_map(level+1,parent_i,group,counts)
            # No suspension before the child Transfer using this reservation.
            return old,new
        finally:self._unpin(parent.address)

    def _ensure_staged(self,level,i):
        a=self.addr(level,i)
        if a in self.cache:
            self.metrics['plb_hits']+=1;self.cache.move_to_end(a);return self.cache[a]
        self.metrics['plb_misses']+=1
        old,new=yield from self._reserve_staged(level,i)
        victim=None
        if len(self.cache)>=self.capacity:
            candidates=[k for k in self.cache if k not in self.pinned]
            need(bool(candidates),'PLB space for compressed recursion')
            victim=self.cache.pop(candidates[0]);self.metrics['plb_evictions']+=1
        admission=None if victim is None else (victim.address,victim.parked_leaf,victim.data)
        value=self.backend.tick(a,old,admit=admission)
        entry=CachedMap(a,value,new);self.cache[a]=entry
        need(len(self.cache)<=self.capacity,'PLB capacity')
        yield dict(type='posmap',level=level,address=a)
        return entry

    def _request_steps(self,a,value):
        while self.pending_reset is not None:
            event=self.advance_reset()
            if event is not None:yield event
        old,new=yield from self._reserve_staged(0,a)
        prior=self.backend.tick(a,old,replace=(new,(lambda p:p) if value is None else (lambda p:value)))
        yield dict(type='data',level=0,address=a,previous=prior)

    def _writeback_steps(self,a,value):return self._request_steps(a,value)

    def step(self,a,value=None):
        if self.dead:raise Reject('fail-stop compressed frontend')
        need(0<=a<self.N and (value is None or len(value)==self.B),'compressed request bounds')
        gen=self._request_steps(a,value);before=self.backend.tree.t
        try:
            event=next(gen)
            need(self.backend.tree.t==before+1,'each compressed step commits exactly one Transfer')
            return event
        except Exception:
            self.dead=True;self.backend.tree.dead=True;raise
        finally:gen.close()

    def access(self,a,value=None):
        if self.pending_writeback is not None:self.pending_writeback.cancel('foreground')
        while True:
            event=self.step(a,value)
            if event['type']=='data':
                self.metrics['application_requests']+=1;return event['previous']

    def dummy(self):
        """One slot; pending reset work takes priority over a fresh dummy."""
        if self.dead:raise Reject('fail-stop compressed frontend')
        try:
            event=self.advance_reset()
            if event is not None:return event
            self.backend.tick(None,self.padding.fresh('public-scheduler-idle'))
            return dict(type='dummy')
        except Exception:
            self.dead=True;self.backend.tree.dead=True;raise

    def reset_snapshot(self):
        r=self.pending_reset
        return None if r is None else dict(level=r.level,parent_i=r.parent_i,parent_address=r.parent.address,group=r.group,cursor=r.cursor)

    def memory_payload_bound(self):
        return dict(super().memory_payload_bound(),reset_descriptors_max=1,reset_scalar_fields=5,
            reset_additional_payload_bytes=0,reset_parent_payload_in_plb=True)


class CompressedWriteback(StagedWriteback):
    """Same cancellation/commit rules, with reset work classified separately."""
    def advance(self):
        performed=super().advance()
        if performed and self.events[-1]['type']=='group_reset':
            self.front.metrics['dwb_posmap_slots']-=1
            self.front.metrics['dwb_group_reset_slots']+=1
        return performed
