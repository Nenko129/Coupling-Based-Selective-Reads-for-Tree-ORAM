"""Freecursive/rho interface experiments without compact/fusion/root removal."""
from minimal_runtime import *
import argparse,traceback
import composition_runtime as rt
import run_composition as rc
import transfer_backend_fixed as fixed

ORIGINAL_IDENTITY=rt.identity

class MinimalBackend:
    def __init__(self,kind,L,N,B=64,Z=4,A=3,S=4,R=128,tree=0,key=b'T'*64):
        assert kind in ('path','deferred','sde','ring','gc_ring')
        R=R if kind=='path' and tree==1 else rt.CORE_R
        self.c=rt.TransferConfig(kind=kind,L=L,N=N,B=B,Z=Z,A=A,S=S,R=R,tree=tree,compact=False,fused=False)
        assert not self.c.rootless and not self.c.compact and not self.c.fused
        if rt.ORAM_SEED is not None:key=hashlib.sha512(b'SELECTIVE-MINIMAL-FRONT'+str(rt.ORAM_SEED).encode()+key).digest()
        self.p=rt.PRF(key);self.server=rt.Server([self.c]);self.io=rt.StreamingTransport(self.server);self.io.capture_limit=0
        self.tree=rt.TransferTree(self.c,self.p,self.io);self.tree.logical_calls=rt.Schedule();self.tree.initialize()
    def tick(self,*args,**kwargs):return self.tree.transfer(*args,**kwargs)

def source():return dict(minimal=identity(),frontend=ORIGINAL_IDENTITY(),fixed_transfer=sha(EVAL/'src/transfer_backend_fixed.py'))

def run(s):
    assert s['compact'] is False and s['fusion'] is False and s['root_retained'] is True
    assert s['family'] in ('free_compressed','rho') and s['kind'] in ('deferred','sde','ring','gc_ring')
    rt.MeasuredBackend=MinimalBackend;rt.identity=source
    if s['family']=='rho':rt.TransferTree=fixed.TransferTree
    row=rc.run(s)
    assert all(not c['compact'] and not c['fused'] and c['kind']!='r0' for c in row['configs'])
    row['minimal_contract']='host frontend held fixed; full headers, unfused, root retained, fixed Z4/A3; no SOC3 retuning'
    save(HOME/'results'/s['suite']/f"{s['id']}.json",row)
    return row

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();s=json.loads(Path(a.spec).read_text(encoding='utf-8'))
    try:run(s)
    except Exception:
        save(HOME/'results/failures'/f"{s['id']}.json",dict(status='failed',spec=s,error=traceback.format_exc()));raise
