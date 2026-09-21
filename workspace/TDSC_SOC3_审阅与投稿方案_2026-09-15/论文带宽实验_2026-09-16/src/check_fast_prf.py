"""Differential crypto, budget rejection, complete frames and cached states."""
from common import *
import optimized_oram as ref
import heterogeneous_oram as hetero
import cached_transport as cache
from fast_prf import make_fast_prf
from meter import StreamingTransport
from workloads import make_trace, payload
import dataclasses, time


def counters(p):
    return p.calls, p.nonces, p.samples, p.decryptions, p.max_input


def primitives(engine):
    Base = engine.PRF; Fast = make_fast_prf(engine); rows = []
    for n in (0, 1, 15, 16, 31, 63, 64, 65, 128, 4096, 8193):
        a, b = Base(b'K'*64), Fast(b'K'*64)
        plain = hashlib.shake_256(str(n).encode()).digest(n)
        for k in range(3):
            args = b'ctx'+bytes([k]), b'oid', bytes(k)
            x, y = a.seal(*args, plain), b.seal(*args, plain)
            assert x == y and counters(a) == counters(b)
            assert a.decrypt(*args, x) == b.decrypt(*args, y) == plain
            assert counters(a) == counters(b)
            assert a.draw(args[0], b'event') == b.draw(args[0], b'event')
        rows.append(dict(length=n, ciphertext_and_counters_equal=True))
    cases = []
    for method in ('stream', 'seal', 'decrypt'):
        for remaining in (0, 1, 2, 3):
            values = []
            for Type in (Base, Fast):
                p = Type(b'K'*64); p.calls = (1 << 96)-remaining; p.max_input = 10
                args = (b'c', b'o', b'a')
                try:
                    if method == 'stream': value = p.stream(*args, b'N'*16, 129)
                    elif method == 'seal': value = p.seal(*args, b'P'*129)
                    else: value = p.decrypt(*args, b'N'*16+b'C'*129)
                    out = ('ok', value)
                except engine.Reject as e: out = (type(e).__name__, str(e))
                values.append((out, counters(p)))
            assert values[0] == values[1], (method, remaining)
            cases.append(dict(method=method, calls_remaining=remaining, identical=True))
    for case in ('nonce_limit', 'short_ciphertext'):
        vals=[]
        for Type in (Base,Fast):
            p=Type(b'K'*64)
            try:
                if case=='nonce_limit':
                    p.nonces=1<<128; p.seal(b'c',b'o',b'a',b'x')
                else:p.decrypt(b'c',b'o',b'a',b'x')
                raise AssertionError('expected rejection')
            except engine.Reject as e: vals.append((type(e).__name__,str(e),counters(p)))
        assert vals[0]==vals[1];cases.append(dict(case=case,identical=True))
    return dict(lengths=rows,boundary_cases=cases)


def execute(engine, configs, fast, cut=None):
    Base = engine.PRF
    if fast: engine.PRF = make_fast_prf(engine)
    if cut is None: engine.Transport = StreamingTransport
    else: cache.install({0:cut})
    try:
        m=engine.RecursiveORAM(configs,b'F'*64); m.io.capture_limit=100000
        B=configs[0].B; N=configs[0].N
        m.initialize(lambda a:payload(a,0,B));truth=[0]*N
        for a,v in make_trace(N,36,929,'uniform'):
            got=m.access(a,None if v is None else payload(a,v,B)); assert got==payload(a,truth[a],B)
            if v is not None:truth[a]=v
        return m
    finally: engine.PRF=Base


def compare(a,b, cached=False):
    assert a.io.events==b.io.events and a.anchor()==b.anchor()
    assert a.server.buckets==b.server.buckets and a.server.global_tags==b.server.global_tags
    assert counters(a.P)==counters(b.P)
    assert a.terminal_pos==b.terminal_pos
    for x,y in zip(a.trees,b.trees):
        assert (x.stash,x.root,x.t,x.g,x.uid)==(y.stash,y.root,y.t,y.g,y.uid)
    if cached:
        assert a.io.local_buckets==b.io.local_buckets and a.io.local_tags==b.io.local_tags
        assert a.io.logical_events==b.io.logical_events


def main():
    primitive={name:primitives(eng) for name,eng in [('core',ref),('heterogeneous',hetero)]}
    rows=[]
    configs=[[ref.Config(k,3,8,B,R=128)] for B in (64,4096) for k in sorted(ref.KINDS)]
    configs += [[ref.Config('r0',3,8,64,Z=7,A=6,S=6,R=128,compact=c,fused=f)]
                for c,f in ((False,False),(False,True),(True,False),(True,True))]
    configs += [[ref.Config(k,3,8,256,R=128),ref.Config(k,1,1,64,R=128,tree=1)] for k in ('sde','r0')]
    for cs in configs:
        start=time.perf_counter();a=execute(ref,cs,False);old=time.perf_counter()-start
        start=time.perf_counter();b=execute(ref,cs,True);new=time.perf_counter()-start
        compare(a,b)
        rows.append(dict(configs=[dataclasses.asdict(c) for c in cs],exact_frames_state_randomness=True,
                         original_harness_seconds=old,optimized_harness_seconds=new))
    cached=[]
    for k in ('sde','r0'):
        extra=dict(Z_by_depth=(4,2,3,4)) if k=='sde' else dict(S_by_depth=(3,2,2,3))
        for B in (64,4096):
            c=hetero.Config(k,3,8,B,R=128,**extra)
            a=execute(hetero,[c],False,2);b=execute(hetero,[c],True,2);compare(a,b,True)
            cached.append(dict(config=dataclasses.asdict(c),exact_remote_and_local_states=True))
    attacks=[]
    for kind in ('sde','r0'):
        for variant in ('body_bitflip','replay_sequence','bad_ack'):
            pair=[]
            for fast in (False,True):
                m=execute(ref,[ref.Config(kind,3,8,64,R=128)],fast); fired=[False]
                def mutate(c,op,seq,stage,meta,req,res):
                    if fired[0] or (variant=='bad_ack' and op!=ref.WRITE):return res
                    fired[0]=True
                    if variant=='body_bitflip':return res[:-1]+bytes([res[-1]^1])
                    o,t,s,f,body=ref.parse_frame(res)
                    return ref.frame(o,t,s-1 if variant=='replay_sequence' else s,
                                     body if variant=='replay_sequence' else b'bad',True)
                m.io.mutator=mutate
                try:m.access(0)
                except ref.Reject:pass
                else:raise AssertionError('tamper accepted')
                assert fired[0] and m.dead
                seq=m.io.seq
                try:m.access(1)
                except ref.Reject:pass
                else:raise AssertionError('retry accepted')
                assert m.io.seq==seq;pair.append(m)
            compare(*pair);attacks.append(dict(kind=kind,attack=variant,exact_failed_prefix=True))
    report=dict(status='passed',primitive=primitive,complete_runs=rows,cached_runs=cached,attacks=attacks,
                source_hashes=source_identity(),accelerator_sha256=sha(Path(__file__).parent/'fast_prf.py'),
                checker_sha256=sha(__file__),heterogeneous_sha256=sha(Path(__file__).parent/'heterogeneous_oram.py'),
                timing_scope='harness implementation only; not an ORAM latency result')
    save(PACKAGE/'results/fast_prf_regression.json',report)
    print(json.dumps(dict(status='passed',complete_runs=len(rows),cached_runs=len(cached),attacks=len(attacks))),flush=True)

if __name__=='__main__':main()
