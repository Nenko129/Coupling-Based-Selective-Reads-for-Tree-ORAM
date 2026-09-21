from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_frontend_minimal import *

def main():
    rt.MeasuredBackend=MinimalBackend;rows=[]
    for kind in ('deferred','sde'):
        rt.install(717,256)
        f=rt.frontends.FreecursiveFront(kind,N=64,B=64,beta=2,plb=4,seed=717,profile=(4,3,4))
        b=f.backend;b.io.reset_meter();b.tree.logical_calls.reset();answers=[]
        for i in range(96):
            addr=i%2;old=f.access(addr)
            assert old==rt.frontends.initial_payload(addr,64);answers.append(old)
        assert f.metrics['group_resets']>0 and f.metrics['group_backend_slots']>0
        assert not b.c.fused and not b.c.compact and not b.c.rootless
        rows.append(dict(kind=kind,answers_sha256=hashlib.sha256(b''.join(answers)).hexdigest(),metrics=dict(f.metrics),
            schedule=b.tree.logical_calls.snapshot(),bill=b.io.snapshot(),source_hashes=source()))
    assert rows[0]['schedule']==rows[1]['schedule'] and rows[0]['metrics']==rows[1]['metrics'] and rows[0]['answers_sha256']==rows[1]['answers_sha256']
    save(HOME/'results/frontend_reset_checks.json',dict(status='passed',rows=rows,scope='minimal unfused/full-header Freecursive-style beta2 group rollover; 96 application requests per arm'))
    print(json.dumps(dict(status='passed',group_resets=rows[0]['metrics']['group_resets'],backend_slots=rows[0]['schedule']['slots'])))
if __name__=='__main__':main()
