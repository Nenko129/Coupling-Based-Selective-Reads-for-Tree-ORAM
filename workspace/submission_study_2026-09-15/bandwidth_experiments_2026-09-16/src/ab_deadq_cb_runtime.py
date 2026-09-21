"""Bind the routed tree to the existing paced raw recursive-map frontend.

Wire recorders are transport instrumentation, never consulted for placement.
Only the root is locally cached in this new adapter; prior ABDF cache6 results
must not be mixed with it. Original runtime modules are not edited.
"""
from common import *
from composition_runtime import Schedule
import ab_paced_frontend as bootstrap
from ab_deadq_cb_tree import TreeConfig,RoutedCBTree

SETTINGS={}


class Backend:
    def __init__(self,kind,L,N,B=64,Z=4,A=3,S=4,R=128,tree=0,key=None):
        need=__import__('ab_deadq_authenticated_store').need
        need(tree==0,'unified recursive tree adapter')
        cfg=SETTINGS
        self.c=TreeConfig(kind,L,N,B,Z,A,S,Y=cfg['Y'],extra=cfg['extra'],component_cap=cfg['component_cap'],
            queue_cap=cfg['queue_cap'],R=cfg['R'])
        self.tree=RoutedCBTree(self.c,seed=cfg['seed']);self.tree.cb_metrics=self.tree.metrics
        self.tree.logical_calls=Schedule();self._channels=self.tree.take_transports()

    def take_channels(self):
        channels=self._channels;del self._channels;return channels

    def tick(self,remove,oldleaf,admit=None,*,replace=None):
        out=self.tree.transfer(remove,oldleaf,admit,replace=replace)
        admitted=remove if replace is not None else None if admit is None else admit[0]
        self.tree.logical_calls.append(dict(remove=remove,admit=admitted))
        return out


def install(settings):
    global SETTINGS
    SETTINGS=dict(settings);bootstrap.Backend=Backend


def identity():
    names=('ab_deadq_cb_runtime.py','ab_deadq_cb_tree.py','ab_deadq_cb_level.py','ab_deadq_routed_allocator.py',
        'ab_deadq_authenticated_store.py','ab_dummy_first_policy.py','cb_oram.py','ab_paced_frontend.py',
        'ab_cb_controller.py','ir_dwb_controller.py','dwb_staged_frontend.py','composition_runtime.py')
    return dict(runtime={n:sha(Path(__file__).parent/n) for n in names},frontend=sha(COMPOSITION/'frontends.py'))
