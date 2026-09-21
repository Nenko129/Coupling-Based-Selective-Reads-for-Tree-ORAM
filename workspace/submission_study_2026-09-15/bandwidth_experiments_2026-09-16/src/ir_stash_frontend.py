"""Data-local-hit bridge with raw recursive maps and the existing PLB.

Map blocks still use the conventional exclusive PLB Transfer protocol. This
module therefore implements data lookup bypass, not full native IR-Stash for
every recursive map block. It does not import or modify a live experiment.
"""
from common import *
import heterogeneous_oram as h
from ir_dwb_controller import StepwiseFront


class StashDataFront(StepwiseFront):
    def _lookup_data_leaf(self,a):
        # A lookup must not reserve a new data leaf. Loading an absent parent
        # can commit map Transfers and yield; those map remaps remain valid.
        if len(self.counts)==1:return self.top[a],None,a
        parent_i,j=divmod(a,self.X)
        parent=yield from self._ensure_staged(1,parent_i)
        return int.from_bytes(parent.data[4*j:4*j+4],'big'),parent,j

    def _request_steps(self,a,value):
        h.need(0<=a<self.N,'data address')
        h.need(value is None or isinstance(value,bytes) and len(value)==self.B,'data payload')
        # F hits in both modes, S hits only in indexed mode: no PosMap lookup.
        hit=self.backend.local_access(a,value)
        if hit is not None:
            prior,where=hit;self.metrics['data_local_'+where+'_before_map']+=1
            yield dict(type='data',level=0,address=a,previous=prior,local=where,transfers=0)
            return
        old,parent,j=yield from self._lookup_data_leaf(a)
        # Parent-map Transfers may have moved data into the local region. Check
        # again using the committed leaf, without changing it on a local hit.
        hit=self.backend.local_access(a,value,leaf=old)
        if hit is not None:
            prior,where=hit;self.metrics['data_local_'+where+'_after_map']+=1
            yield dict(type='data',level=0,address=a,previous=prior,local=where,transfers=0)
            return
        new=self.leaves.fresh('raw-remap')
        if parent is None:self.top[j]=new
        else:parent.data=parent.data[:4*j]+new.to_bytes(4,'big')+parent.data[4*j+4:]
        # No yield, preemption or local probe is allowed between installing
        # the new leaf and committing its authenticated data replacement.
        prior=self.backend.tick(a,old,replace=(new,lambda p:p if value is None else value))
        self.metrics['data_remote_remaps']+=1
        yield dict(type='data',level=0,address=a,previous=prior,local=None,transfers=1)

    def step(self,a,value=None):
        if self.dead:raise h.Reject('fail-stop IR data-local frontend')
        before=self.backend.tree.t;steps=self._request_steps(a,value)
        try:
            h.need(self.pending_writeback is None,'use the serial LocalHitController DWB interface')
            event=next(steps);delta=self.backend.tree.t-before
            h.need(delta in (0,1),'local or exactly one Transfer')
            h.need(delta==1 or event['type']=='data' and event.get('local') in ('F','S'),'unclocked event type')
            event['transfers']=delta
            return event
        except Exception:
            self.dead=True;self.backend.tree.dead=True;raise
        finally:steps.close()

    def access(self,a,value=None):
        # Synchronous convenience method has no public padding policy; the
        # fixed-clock experiment must use LocalHitController instead.
        while True:
            event=self.step(a,value)
            if event['type']=='data':return event['previous']


def identity():
    import ir_stash_runtime
    return dict(backend=ir_stash_runtime.identity(),
        frontend={n:sha(Path(__file__).parent/n) for n in ('ir_stash_frontend.py','ir_stash_controller.py')})
