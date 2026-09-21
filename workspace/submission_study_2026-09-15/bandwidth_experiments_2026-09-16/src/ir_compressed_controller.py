"""Fixed-slot LLC/DWB scheduler including mandatory compressed group resets."""
from common import *
from ir_dwb_controller import Controller,Line
import ir_dwb_runtime as base


class CompressedController(Controller):
    def tick(self,arrivals=()):
        if self.dead:raise RuntimeError('fail-stop compressed controller')
        try:
            if self.front.pending_reset is not None:
                self.queue.extend(arrivals);arrivals=()
                self.prepare_foreground()
                if self.candidate is not None and not self.valid_candidate():self.drop_candidate('candidate_changed')
                before=self.front.backend.tree.t;event=self.front.advance_reset()
                if event is not None:
                    assert self.front.backend.tree.t==before+1 and event['type']=='group_reset'
                    self.metrics['maintenance_reset_slots']+=1;self.metrics['public_slots']+=1;self.clock+=1
                    return
            super().tick(arrivals)
        except Exception:
            self.dead=True;self.front.dead=True;self.front.backend.tree.dead=True;raise

    def run_window(self,requests,gap,slots):
        answers,metrics=super().run_window(requests,gap,slots)
        metrics['group_reset_pending']=self.front.pending_reset is not None
        metrics['group_reset_slots']=sum(metrics.get(k,0) for k in ('foreground_group_reset_slots','dwb_group_reset_slots','maintenance_reset_slots'))
        assert metrics['public_slots']==sum(metrics.get(k,0) for k in ('foreground_slots','dwb_posmap_slots','dwb_data_slots',
            'dwb_group_reset_slots','maintenance_reset_slots','dummy_slots'))
        return answers,metrics


def identity():
    names=('dwb_compressed_frontend.py','ir_compressed_controller.py')
    return dict(base=base.identity(),compressed={n:sha(Path(__file__).parent/n) for n in names})
