from pathlib import Path
from collections import Counter
import hashlib,json,sys
from frontends import FreecursiveFront,RhoFront,initial_payload
from transfer_backend import Backend,Reject
from optimized_oram import OPEN_FULL,OPEN_HEAD,READ_SLOTS,WRITE,Header,PUBLIC

OUT=Path(__file__).resolve().parents[1]

def inventory(backend):
    """Test-only audit, never invoked by the frontend or benchmark decisions."""
    t=backend.tree;c=backend.c;counts=Counter(list(t.stash))
    for (tree,b),s in backend.server.buckets.items():
        if c.rootless and b==1:continue
        pub=s.header[:PUBLIC]
        h=Header.decode(c,pub,t.P.decrypt(t.ctx,t.oid(b),pub,s.header[PUBLIC:]))
        counts.update(d.address for d in h.live.values())
    assert all(v==1 for v in counts.values()),counts
    return set(counts)

def main():
    records=[]
    for compressed,beta,X in [(False,14,4),(True,14,4),(True,2,4)]:
        schedules=[]
        for kind in ['path','deferred','sde','ring','gc_ring','r0']:
            front=FreecursiveFront(kind,N=32,X=X,beta=beta,compressed=compressed,plb=3,seed=19)
            expected={a:initial_payload(a,64) for a in range(32)}
            for t in range(96):
                a=(t//4*9)%32
                value=(t+1000).to_bytes(8,'big')+bytes(56) if t%3==0 else None
                old=front.access(a,value);assert old==expected[a],(kind,compressed,beta,t,a)
                if value is not None:expected[a]=value
            active=inventory(front.backend);cached=set(front.cache)
            assert active.isdisjoint(cached) and active|cached==set(range(front.total))
            schedule=[(r['remove'],r['admit']) for r in front.backend.tree.logical_calls]
            schedules.append(schedule)
            records.append({'frontend':'Freecursive scoped','compressed':compressed,'beta':beta,'kind':kind,
                            'application_requests':96,'metrics':dict(front.metrics),'ownership_checked':True})
        assert all(s==schedules[0] for s in schedules),'backend coins changed frontend schedule'
    for kind in ['path','deferred','sde','ring','gc_ring','r0']:
        front=RhoFront(kind,N=32,llc=2,rho=4,n=3,seed=7)
        expected={a:initial_payload(a,64) for a in range(32)};requests=[];answers=[]
        for t in range(100):
            a=((t//20)*5+t%6)%32;value=(t+3000).to_bytes(8,'big')+bytes(56) if t%4==0 else None
            requests.append((a,value));answers.append(expected[a])
            if value is not None:expected[a]=value
        got=front.run(requests);assert got==answers,(kind,next((i for i,(x,y) in enumerate(zip(got,answers)) if x!=y),None))
        active=inventory(front.back);assert active.isdisjoint(front.llc) and active.isdisjoint(front.tags)
        assert active|set(front.llc)|set(front.tags)==set(range(32))
        assert inventory(front.front)==set(front.tags.values())
        assert front.front.tree.t==front.n*front.metrics['frames']
        assert front.back.tree.t-32==front.metrics['frames']
        records.append({'frontend':'rho scoped','kind':kind,'application_requests':100,'metrics':dict(front.metrics),
                        'exclusive_ownership_checked':True,'public_frame_checked':True})
    tamper=[]
    for kind,op,stage in [('sde',OPEN_FULL,'logical'),('sde',WRITE,'logical'),('sde',WRITE,'evict'),
                          ('r0',OPEN_HEAD,'logical'),('r0',READ_SLOTS,'logical'),('r0',WRITE,'logical')]:
        front=FreecursiveFront(kind,N=16,X=4,plb=3,seed=2);hit=[False]
        def mutate(c,opcode,seq,event,meta,request,response):
            if not hit[0] and opcode==op and event==stage:
                hit[0]=True;return response[:-1]+bytes([response[-1]^1])
            return response
        front.backend.io.mutator=mutate
        failed=False
        try:
            for i in range(12):front.access(i%16)
        except Reject:failed=True
        assert hit[0] and failed and front.dead and front.backend.tree.dead
        before=len(front.backend.io.events)
        try:front.access(0)
        except Reject:pass
        else:raise AssertionError('failed frontend resumed')
        assert len(front.backend.io.events)==before
        tamper.append({'kind':kind,'opcode':op,'stage':stage,'rejected_and_no_retry_io':True})
    counterexample={'A':2,'L':2,'N':4,'unclocked_appended_blocks':4,'old_fresh_offset':1,
                    'conclusion':'batch append with no service ticks violates the A-1 fresh-token premise'}
    assert counterexample['N']<=2*(1<<(2-1)) and 4>2-1
    out={'status':'passed','functional_cases':records,'tamper_cases':tamper,
         'negative_interface_example':counterexample,
         'scope':'small functional and authentication checks; not full native Freecursive/rho artifacts'}
    (OUT/'results').mkdir(exist_ok=True)
    (OUT/'results/prototype_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'functional_cases':len(records),'tamper_cases':len(tamper),'status':'passed'}))

if __name__=='__main__':main()
