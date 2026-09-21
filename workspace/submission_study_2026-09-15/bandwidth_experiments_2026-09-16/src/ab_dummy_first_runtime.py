"""Separately bound dummy-first CB revision with unchanged geometry/controller."""
from common import *
import ab_cb_runtime as base
import ab_dummy_first_fusion as fusion
import ab_paced_frontend as bootstrap

SETTINGS={}


class TransferConfig(base.TransferConfig):
    def context(self):
        return base.engine.encode(b'SOC3-AB-DUMMY-FIRST-v1',super().context())


class TransferTree(base.TransferTree):
    def fused_logical(self,view,address):return fusion.fused_logical(self,view,address)


class Backend:
    def __init__(self,kind,L,N,B=64,Z=5,A=5,S=7,R=128,tree=0,key=b'T'*64):
        cfg=SETTINGS;bottom=cfg.get('bottom_dummy');y=cfg.get('Y',4)
        profile=() if bottom is None else tuple(S if d<L-2 else bottom+y for d in range(L+1))
        self.c=TransferConfig(kind=kind,L=L,N=N,B=B,Z=Z,A=A,S=S,Y=y,R=cfg.get('R',500),
            tree=tree,compact=True,fused=True,S_by_depth=profile)
        key=hashlib.sha512(b'SOC3-AB-CB-INTEGRATION-v1'+str(cfg['seed']).encode()+key).digest()
        self.p=base.make_fast_prf(base.engine)(key);base.cache.install({tree:cfg['cached_levels']})
        self.server=base.cache.RemoteServer([self.c]);self.io=base.cache.CachedTransport(self.server)
        self.tree=TransferTree(self.c,self.p,self.io);self.tree.logical_calls=base.DualSchedule();self.tree.initialize()
    def tick(self,*args,**kwargs):return self.tree.transfer(*args,**kwargs)


def install(settings):
    global SETTINGS
    SETTINGS=dict(settings);bootstrap.Backend=Backend


frontends=base.frontends


def identity():
    names=('ab_dummy_first_runtime.py','ab_dummy_first_fusion.py','ab_dummy_first_policy.py','ab_paced_frontend.py')
    return dict(preserved_runtime=base.identity(),revision={n:sha(Path(__file__).parent/n) for n in names})
