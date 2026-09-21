from common import *
sys.path.insert(0,str(COMPOSITION))
import transfer_backend as old
import transfer_backend_fixed as new
from workloads import payload

def instance(module):
    c=module.TransferConfig(kind='path',L=1,N=2,B=64,Z=1,A=2,S=0,R=64)
    p=module.PRF(b'F'*64);server=module.Server([c]);io=module.Transport(server);tree=module.TransferTree(c,p,io);tree.initialize()
    return tree,io

def main():
    findings=[]
    for module in (old,new):
        t,io=instance(module)
        t.transfer(None,0,admit=(0,1,payload(0,0,64)))
        t.transfer(None,0,admit=(1,1,payload(1,0,64)))
        assert 1 in t.stash
        rejected=False
        try:answer=t.transfer(1,1,admit=(1,0,payload(1,1,64)))
        except old.Reject:rejected=True
        if module is old:assert rejected and t.dead
        else:
            assert not rejected and answer==payload(1,0,64)
            answer=t.transfer(1,0,replace=(1,lambda p:p));assert answer==payload(1,1,64)
            assert t.births==4 and t.removals==2
        findings.append(dict(implementation=module.__name__,reachable_stash_replacement_rejected=rejected))
    # True duplicate in the live Path pool must still be rejected.
    t,io=instance(new);t.transfer(None,0,admit=(0,1,payload(0,0,64)))
    try:t.transfer(None,1,admit=(0,0,payload(0,1,64)))
    except old.Reject:pass
    else:raise AssertionError('true duplicate accepted')
    assert t.dead
    # Previously successful traces must retain all bytes and random events.
    differential=[]
    for kind in ('path','deferred','sde','ring','r0'):
        a=old.Backend(kind,3,8,B=64,Z=4,A=3,S=4,R=128);b=new.Backend(kind,3,8,B=64,Z=4,A=3,S=4,R=128)
        for address in range(8):
            leaf=address
            for x in (a,b):x.tick(None,address,admit=(address,leaf,payload(address,0,64)))
        pos=list(range(8))
        for i in range(48):
            address=i%8;before=pos[address];after=(i*3+1)%8;pos[address]=after
            aa=a.tick(address,before,replace=(after,lambda p:p));bb=b.tick(address,before,replace=(after,lambda p:p));assert aa==bb
        assert a.io.events==b.io.events
        assert (a.tree.root,a.tree.stash,a.tree.g,a.tree.t)==(b.tree.root,b.tree.stash,b.tree.g,b.tree.t)
        differential.append(dict(kind=kind,rpcs=len(a.io.events),exact_transcript=True))
    save(PACKAGE/'results/transfer_fix_regression.json',dict(status='passed',reachable_counterexample=findings,
         true_duplicate_still_rejected=True,successful_trace_differential=differential,source_sha256=sha(Path(__file__).parent/'transfer_backend_fixed.py')))
    print(json.dumps(dict(status='passed',counterexample_reproduced_and_fixed=True,successful_trace_differential=len(differential))))
if __name__=='__main__':main()
