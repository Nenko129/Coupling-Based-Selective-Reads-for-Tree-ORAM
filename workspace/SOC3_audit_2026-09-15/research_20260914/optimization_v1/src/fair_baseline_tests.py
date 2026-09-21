"""Wire/correctness checks for re-tuned Ring with 16 slots and a non-power-of-two map."""
from optimized_oram import *
from optimized_cost import invoice
from optimized_gate import ROOT
from variant_tests import verify_physical_snapshot
import json,hashlib

out=[]
for kind,S,B1 in [('ring',9,512),('r0',5,404)]:
    N=384;N1=(4*N+B1-1)//B1
    cs=[Config(kind,7,N,4096,Z=7,A=6,S=9 if kind=='ring' else 6,R=192),
        Config(kind,1,N1,B1,Z=7,A=6,S=S,R=16,tree=1)]
    m=RecursiveORAM(cs,hashlib.sha512(f'{kind}:{B1}'.encode()).digest());m.initialize(lambda a:ui(a,4096));truth=[ui(a,4096) for a in range(N)]
    for i in range(180):
        a=(i*100+i//7)%N;v=ui(i+10000,4096) if i%3==0 else None
        assert m.access(a,v)==truth[a]
        if v is not None:truth[a]=v
    bill=invoice(cs,m.io.events);verify_physical_snapshot(m)
    out.append(dict(kind=kind,S=S,B1=B1,online_requests=180,frames=bill['events_checked'],passes=True))
(ROOT/'results/fair_baseline_tests.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
