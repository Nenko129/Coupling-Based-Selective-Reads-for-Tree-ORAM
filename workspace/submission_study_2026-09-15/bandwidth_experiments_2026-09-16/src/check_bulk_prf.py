"""A standalone candidate check: never edits the active fast-v1 runner."""
from common import *
import optimized_oram as ref
import heterogeneous_oram as hetero
from fast_prf import make_fast_prf
from bulk_prf import make_bulk_prf
from check_fast_prf import primitives,execute,compare,counters
import check_fast_prf as prior
import time,random

def main():
    # Reuse the independent comparisons, substituting only the candidate factory.
    original=prior.make_fast_prf;prior.make_fast_prf=make_bulk_prf
    primitive={n:primitives(e) for n,e in [('core',ref),('heterogeneous',hetero)]}
    rng=random.Random(741);extra=[]
    for i in range(120):
        n=rng.randrange(0,17000);ctx=rng.randbytes(rng.randrange(0,500));oid=rng.randbytes(11);aad=rng.randbytes(rng.randrange(0,90))
        key=rng.randbytes(64);nonce=rng.randbytes(16);a=ref.PRF(key);b=make_bulk_prf(ref)(key)
        assert a.stream(ctx,oid,aad,nonce,n)==b.stream(ctx,oid,aad,nonce,n)
        assert counters(a)==counters(b);extra.append(n)
    configs=[ref.Config(k,3,8,4096,R=128) for k in sorted(ref.KINDS)]
    configs += [ref.Config('r0',3,8,4096,Z=7,A=6,S=6,R=128,compact=c,fused=f) for c,f in ((False,False),(False,True),(True,False),(True,True))]
    rows=[]
    for c in configs:
        a=execute(ref,[c],False);b=execute(ref,[c],True);compare(a,b)
        rows.append(dict(kind=c.kind,Z=c.Z,A=c.A,S=c.S,compact=c.compact,fused=c.fused,identical=True))
    for kind in ('sde','r0'):
        c=hetero.Config(kind,3,8,4096,R=128,S_by_depth=(3,2,1,3))
        a=execute(hetero,[c],False,2);b=execute(hetero,[c],True,2);compare(a,b,True)
        rows.append(dict(kind=kind,cached=True,identical=True))
    prior.make_fast_prf=original
    bench=[]
    for n in (64,256,4096):
        times={};checksum={}
        for name,Type in [('reference',ref.PRF),('prefix_v1',make_fast_prf(ref)),('bulk',make_bulk_prf(ref))]:
            p=Type(b'K'*64);before=time.perf_counter();digest_=hashlib.sha256()
            for _ in range(200):digest_.update(p.seal(b'C'*256,b'oid',b'A'*16,b'P'*n))
            times[name]=time.perf_counter()-before;checksum[name]=digest_.hexdigest()
        assert len(set(checksum.values()))==1;bench.append(dict(B=n,seconds=times))
    save(PACKAGE/'results/bulk_prf_checks.json',dict(status='passed',primitive=primitive,random_stream_lengths=extra,
        complete_runs=rows,benchmark=bench,source_hashes=source_identity(),bulk_sha256=sha(Path(__file__).parent/'bulk_prf.py'),
        prefix_sha256=sha(Path(__file__).parent/'fast_prf.py'),checker_sha256=sha(__file__),
        reference='RFC 8018 section 5.2: at c=1 each block is U1, with a four-octet block counter',
        benchmark_scope='harness computation only, not an ORAM algorithm speedup'))
    print(json.dumps(dict(status='passed',complete_runs=len(rows),random_cases=len(extra),benchmark=bench)))
if __name__=='__main__':main()
