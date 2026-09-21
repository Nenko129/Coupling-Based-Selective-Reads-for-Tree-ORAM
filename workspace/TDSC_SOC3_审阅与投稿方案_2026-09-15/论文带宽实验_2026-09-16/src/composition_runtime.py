"""Bounded metering around the previously checked Transfer frontends."""
from common import *
sys.path.insert(0,str(COMPOSITION))
import frontends
from transfer_backend import TransferConfig,TransferTree,PRF,Server
from meter import StreamingTransport

ORAM_SEED=None
CORE_R=256
CAPTURE=0

class Schedule:
    def __init__(self):self.reset()
    def reset(self):self.hash=hashlib.sha256();self.count=0
    def append(self,event):
        self.hash.update(json.dumps([event['remove'],event['admit']],separators=(',',':')).encode()+b'\n');self.count+=1
    def snapshot(self):return dict(slots=self.count,remove_admit_sha256=self.hash.hexdigest())

class MeasuredBackend:
    def __init__(self,kind,L,N,B=64,Z=4,A=3,S=4,R=128,tree=0,key=b'T'*64):
        R=R if kind=='path' and tree==1 else CORE_R
        self.c=TransferConfig(kind=kind,L=L,N=N,B=B,Z=Z,A=A,S=S,R=R,tree=tree,compact=True,fused=True)
        if ORAM_SEED is not None:key=hashlib.sha512(b'SOC3-COMPOSITION-EVAL'+str(ORAM_SEED).encode()+key).digest()
        self.p=PRF(key);self.server=Server([self.c]);self.io=StreamingTransport(self.server);self.io.capture_limit=CAPTURE
        self.tree=TransferTree(self.c,self.p,self.io);self.tree.logical_calls=Schedule();self.tree.initialize()
    def tick(self,*args,**kwargs):return self.tree.transfer(*args,**kwargs)

def install(seed=None,R=256,capture=0):
    global ORAM_SEED,CORE_R,CAPTURE
    ORAM_SEED=seed;CORE_R=R;CAPTURE=capture;frontends.Backend=MeasuredBackend

def identity():
    paths=[COMPOSITION/'frontends.py',COMPOSITION/'transfer_backend.py']+[Path(__file__).parent/n for n in ('composition_runtime.py','run_composition.py')]
    return dict(core=source_identity(),composition={str(p.relative_to(ROOT)):sha(p) for p in paths})
