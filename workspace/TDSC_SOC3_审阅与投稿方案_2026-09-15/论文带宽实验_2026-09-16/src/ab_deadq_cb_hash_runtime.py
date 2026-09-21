"""Separately bound raw-map adapter using hash-only authenticated updates."""
from common import *
from composition_runtime import Schedule
import ab_paced_frontend as bootstrap
import ab_deadq_cb_runtime as base
from ab_deadq_cb_tree import TreeConfig
from ab_deadq_cb_hash_tree import HashRoutedCBTree
from ab_deadq_authenticated_store import need

SETTINGS={}


class Backend(base.Backend):
    def __init__(self,kind,L,N,B=64,Z=4,A=3,S=4,R=128,tree=0,key=None):
        need(tree==0,'unified recursive tree adapter');cfg=SETTINGS
        self.c=TreeConfig(kind,L,N,B,Z,A,S,Y=cfg['Y'],extra=cfg['extra'],component_cap=cfg['component_cap'],queue_cap=cfg['queue_cap'],R=cfg['R'])
        self.tree=HashRoutedCBTree(self.c,seed=cfg['seed']);self.tree.cb_metrics=self.tree.metrics
        self.tree.logical_calls=Schedule();self._channels=self.tree.take_transports()


def install(settings):
    global SETTINGS
    SETTINGS=dict(settings);bootstrap.Backend=Backend


def identity():
    names=('ab_deadq_cb_hash_runtime.py','ab_deadq_cb_hash_tree.py','ab_deadq_cb_hash_level.py','ab_deadq_cb_hash_store.py')
    return dict(preserved=base.identity(),hash_updates={n:sha(Path(__file__).parent/n) for n in names})
