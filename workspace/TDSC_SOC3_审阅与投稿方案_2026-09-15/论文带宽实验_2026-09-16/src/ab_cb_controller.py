"""Public-slot CB controller with an explicit occupancy pressure policy.

Background slots are ordinary authenticated CB dummy Transfers, so they can
promote green records. This is NOT a reproduction of a strict dummy-only
background policy. The public slot count is never shortened by a private hit.
"""
from common import *
from collections import Counter
from ir_dwb_controller import Controller,StepwiseFront


class PressureController(Controller):
    def __init__(self,front,sets=8,ways=2,high=None,low=None):
        super().__init__(front,sets=sets,ways=ways,dwb=False)
        assert (high is None)==(low is None)
        if high is not None:assert 0<=low<high<front.backend.c.R
        self.high=high;self.low=low;self.draining=False;self.occupancies=Counter()

    def needs_background(self):
        if self.high is None:return False
        size=len(self.front.backend.tree.stash)
        if self.draining and size<=self.low:
            self.draining=False;self.metrics['background_episodes_completed']+=1
        if not self.draining and size>=self.high:
            self.draining=True;self.metrics['background_episodes_started']+=1
        return self.draining

    def tick(self,arrivals=()):
        if self.dead:raise RuntimeError('fail-stop CB pressure controller')
        try:
            if self.needs_background():
                self.queue.extend(arrivals);b=self.front.backend
                before=b.tree.t;green=b.tree.cb_metrics['green_promotions']
                self.front.dummy()
                assert b.tree.t==before+1
                self.metrics['background_green_promotions']+=b.tree.cb_metrics['green_promotions']-green
                self.metrics['background_slots']+=1;self.metrics['public_slots']+=1;self.clock+=1
            else:super().tick(arrivals)
            self.occupancies[len(self.front.backend.tree.stash)]+=1
        except Exception:
            self.dead=True;self.front.dead=True;self.front.backend.tree.dead=True;raise

    def run_window(self,requests,gap,slots):
        answers,metrics=super().run_window(requests,gap,slots)
        metrics['background_pending']=self.draining
        assert metrics['public_slots']==sum(metrics.get(k,0) for k in ('foreground_slots','dummy_slots','background_slots'))
        return answers,metrics
