"""Recursive-map binding for authenticated CB and a real prefix cache."""
from common import *
import cb_oram as engine
import cached_transport as cache
from cb_transfer import TransferConfig,TransferTree
from fast_prf import make_fast_prf
from composition_runtime import Schedule
import frontends
import ab_geometry_frontend as geometry

SETTINGS={}


class DualSchedule(Schedule):
    def __init__(self):
        self.useful=Schedule();super().__init__()
    def reset(self):
        super().reset();self.useful.reset()
    def append(self,event):
        super().append(event)
        if event['remove'] is not None or event['admit'] is not None:self.useful.append(event)


class Backend:
    def __init__(self,kind,L,N,B=64,Z=5,A=5,S=7,R=128,tree=0,key=b'T'*64):
        cfg=SETTINGS;bottom=cfg.get('bottom_dummy')
        y=cfg.get('Y',4)
        profile=() if bottom is None else tuple(S if d<L-2 else bottom+y for d in range(L+1))
        self.c=TransferConfig(kind=kind,L=L,N=N,B=B,Z=Z,A=A,S=S,Y=y,R=cfg.get('R',500),
            tree=tree,compact=True,fused=True,S_by_depth=profile)
        key=hashlib.sha512(b'SOC3-AB-CB-INTEGRATION-v1'+str(cfg['seed']).encode()+key).digest()
        self.p=make_fast_prf(engine)(key);cache.install({tree:cfg['cached_levels']})
        self.server=cache.RemoteServer([self.c]);self.io=cache.CachedTransport(self.server)
        self.tree=TransferTree(self.c,self.p,self.io);self.tree.logical_calls=DualSchedule();self.tree.initialize()
    def tick(self,*args,**kwargs):return self.tree.transfer(*args,**kwargs)


def install(settings):
    global SETTINGS
    SETTINGS=dict(settings);frontends.Backend=Backend;geometry.Backend=Backend


def identity():
    names=('ab_cb_runtime.py','ab_cb_controller.py','ab_geometry_frontend.py','cb_oram.py','cb_fusion.py','cb_transfer.py',
        'cached_transport.py','heterogeneous_oram.py','fast_prf.py','composition_runtime.py',
        'ir_dwb_controller.py','dwb_staged_frontend.py')
    return dict(base=source_identity(),runtime={n:sha(Path(__file__).parent/n) for n in names},
        frozen_frontend={n:sha(COMPOSITION/n) for n in ('frontends.py','transfer_backend.py')})
