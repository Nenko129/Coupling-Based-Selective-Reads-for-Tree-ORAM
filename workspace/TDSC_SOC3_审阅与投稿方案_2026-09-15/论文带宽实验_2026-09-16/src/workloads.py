"""Fixed input traces, independent of ORAM coins; not a YCSB engine."""
from common import *
import random,bisect,math

def make_trace(N,count,seed,workload):
    rng=random.Random(seed);rw=random.Random(seed+2000000);perm=list(range(N));random.Random(314159).shuffle(perm)
    cdf=[]
    if workload=='zipf09':
        total=0.0
        for a in range(N):total+=(a+1)**(-0.9);cdf.append(total)
    rows=[];hot=max(1,N//100)
    for t in range(count):
        if workload=='uniform':a=rng.randrange(N)
        elif workload=='hot90':a=perm[rng.randrange(hot) if rng.random()<0.9 else rng.randrange(hot,N)]
        elif workload=='zipf09':a=perm[min(N-1,bisect.bisect_left(cdf,rng.random()*cdf[-1]))]
        elif workload=='scan':a=t%N
        else:raise ValueError(workload)
        rows.append((a,t+1 if rw.random()<0.5 else None))
    return rows

def payload(address,version,B):
    return hashlib.shake_256(b'SOC3-EVAL-PAYLOAD-v1'+address.to_bytes(8,'big')+version.to_bytes(8,'big')).digest(B)

def stored_trace(N,count,seed,workload):
    rows=make_trace(N,count,seed,workload)
    info=dict(N=N,count=count,seed=seed,workload=workload,write_probability=0.5,format='address, write-version or null; initial version=0',
              payload='SHAKE256(domain || uint64be(address) || uint64be(version)), B output bytes',rows=rows)
    path=PACKAGE/'traces'/f'{workload}_N{N}_Q{count}_seed{seed}.json'
    if path.exists():assert json.loads(path.read_text(encoding='utf-8'))==json.loads(json.dumps(info))
    else:save(path,info)
    return rows,dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path))
