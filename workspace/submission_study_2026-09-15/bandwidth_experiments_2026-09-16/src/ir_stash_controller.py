"""Fixed public slots with unclocked data-local completions.

A local hit cannot delete a public slot. Ready foreground work is completed
locally until one Transfer is needed; otherwise DWB or a dummy fills the slot.
"""
from ir_dwb_controller import Controller


class LocalHitController(Controller):
    def foreground_slot(self):
        before=self.front.backend.tree.t;old=self.metrics.copy()
        super().foreground_slot()
        delta=self.front.backend.tree.t-before;assert delta in (0,1)
        if delta==0:
            # The inherited state transitions (LLC fill, dirty victim removal,
            # answer delivery) are also correct for a serial local completion.
            self.metrics['foreground_slots']-=1
            self.metrics['foreground_data_slots']-=1
            assert self.metrics['foreground_data_slots']==old['foreground_data_slots']
            self.metrics['foreground_local_completions']+=1
        return bool(delta)

    def idle_slot(self):
        before=self.front.backend.tree.t;old=self.metrics.copy()
        super().idle_slot()
        delta=self.front.backend.tree.t-before;assert delta in (0,1)
        if delta==0:
            assert self.metrics['dwb_completed']==old['dwb_completed']+1
            self.metrics['dwb_data_slots']-=1
            assert self.metrics['dwb_data_slots']==old['dwb_data_slots']
            self.metrics['dwb_local_completions']+=1
            self.front.dummy();self.metrics['dummy_slots']+=1

    def tick(self,arrivals=()):
        if self.dead:raise RuntimeError('fail-stop local-hit controller')
        try:
            self.queue.extend(arrivals);before=self.front.backend.tree.t
            while True:
                self.prepare_foreground()
                if self.candidate is not None and not self.valid_candidate():self.drop_candidate('candidate_changed')
                if self.work is None:self.idle_slot();break
                if self.foreground_slot():break
                # Every zero-Transfer step completes either a dirty writeback
                # or one request; a finite queue makes this loop terminate.
            assert self.front.backend.tree.t==before+1
            self.metrics['public_slots']+=1;self.clock+=1
        except Exception:
            self.dead=True;self.front.dead=True;self.front.backend.tree.dead=True;raise
