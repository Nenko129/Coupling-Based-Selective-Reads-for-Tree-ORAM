"""Depth-layout Transfer plus real prefix cache for the staged DWB frontend."""
from common import *
import heterogeneous_oram as h
import cached_transport as cache
from ir_transfer import TransferConfig,TransferTree
from fast_prf import make_fast_prf
from composition_runtime import Schedule
import frontends

SETTINGS={}

class Backend:
    def __init__(self,kind,L,N,B=64,Z=4,A=3,S=4,R=128,tree=0,key=b'T'*64):
        cfg=SETTINGS
        z=tuple(cfg.get('Z_by_depth',[]));ss=tuple(cfg.get('S_by_depth',[]))
        self.c=TransferConfig(kind=kind,L=L,N=N,B=B,Z=Z,A=A,S=S,R=cfg.get('R',480),tree=tree,compact=True,fused=True,Z_by_depth=z,S_by_depth=ss)
        key=hashlib.sha512(b'SOC3-IR-DWB-EVAL'+str(cfg['seed']).encode()+key).digest()
        self.p=make_fast_prf(h)(key)
        cache.install({tree:cfg['cached_levels']})
        self.server=cache.RemoteServer([self.c]);self.io=cache.CachedTransport(self.server)
        self.tree=TransferTree(self.c,self.p,self.io);self.tree.logical_calls=Schedule();self.tree.initialize()
    def tick(self,*args,**kwargs):return self.tree.transfer(*args,**kwargs)

def install(settings):
    global SETTINGS
    SETTINGS=dict(settings);frontends.Backend=Backend

def identity():
    names=('ir_transfer.py','ir_dwb_runtime.py','ir_dwb_controller.py','dwb_staged_frontend.py','heterogeneous_oram.py',
           'heterogeneous_fusion.py','cached_transport.py','fast_prf.py','composition_runtime.py')
    return dict(base=source_identity(),runtime={n:sha(Path(__file__).parent/n) for n in names},frontend=sha(COMPOSITION/'frontends.py'))
