"""Isolated backend for the native-behavior IR-Stash extension."""
from common import *
import hashlib
import heterogeneous_oram as h
import cached_transport as cache
from ir_stash import StashConfig,StashTree,AnchoredTransport
from fast_prf import make_fast_prf
from composition_runtime import Schedule
import frontends

SETTINGS={}
class Backend:
    def __init__(self,kind,L,N,B=64,Z=4,A=3,S=3,R=128,tree=0,key=b'T'*64):
        s=SETTINGS
        self.c=StashConfig(kind=kind,L=L,N=N,B=B,Z=Z,A=A,S=S,R=s.get('R',480),tree=tree,compact=True,fused=True,
            Z_by_depth=tuple(s.get('Z_by_depth',[])),index_sets=s['index_sets'],index_ways=s['index_ways'],indexed=s['indexed'])
        key=hashlib.sha512(b'IR-STASH-EVAL-v1'+str(s['seed']).encode()+key).digest()
        self.p=make_fast_prf(h)(key);cache.install({tree:s['cached_levels']})
        self.server=cache.RemoteServer([self.c]);self.io=AnchoredTransport(self.server)
        self.tree=StashTree(self.c,self.p,self.io);self.tree.logical_calls=Schedule();self.tree.initialize()
    def tick(self,*args,**kwargs):return self.tree.transfer(*args,**kwargs)
    def local_access(self,*args,**kwargs):return self.tree.local_access(*args,**kwargs)
def install(settings):
    global SETTINGS
    SETTINGS=dict(settings);frontends.Backend=Backend
def identity():
    import ir_compressed_controller
    return dict(base=ir_compressed_controller.identity(),
        frozen_transfer=sha(COMPOSITION/'transfer_backend.py'),
        new={n:sha(Path(__file__).parent/n) for n in ('ir_stash.py','ir_stash_runtime.py')})

