"""Uniform differential check + heterogeneous state invariants and tampering."""
from common import *
import dataclasses
import optimized_oram as original
import heterogeneous_oram as h
from heterogeneous_meter import install
from workloads import make_trace,payload

def perform(engine,c,steps=48,audit=False):
    m=engine.RecursiveORAM([c],b'H'*64)
    if engine is h:m.io.capture_limit=100000
    m.initialize(lambda a:payload(a,0,c.B));truth=[0]*c.N;checks=0
    inspector=h.PRF(b'H'*64)
    for a,v in make_trace(c.N,steps,717,'uniform'):
        old=m.access(a,None if v is None else payload(a,v,c.B));assert old==payload(a,truth[a],c.B)
        if v is not None:truth[a]=v
        if audit:
            t=m.trees[0];seen={r.address:r for r in t.stash.values()};uids={r.uid for r in seen.values()}
            assert len(uids)==len(seen)
            for (tree,b),st in m.server.buckets.items():
                if c.rootless and b==1:continue
                bc=c.at(b);pub=st.header[:h.PUBLIC]
                hd=h.Header.decode(bc,pub,inspector.decrypt(c.context(),t.oid(b),pub,st.header[h.PUBLIC:]))
                assert len(hd.live)<=bc.Z
                if c.kind!='path':assert hd.gamma==h.generation(t.g,h.depth(b),b-(1<<h.depth(b)))
                for j,desc in hd.live.items():
                    assert desc.address not in seen and desc.uid not in uids
                    assert h.node(desc.leaf,h.depth(b),c.L)==b
                    if c.selective:assert h.depth(b) in h.gc(t.g,desc.leaf,c.L)
                    data=inspector.decrypt(c.context(),t.oid(b,j),h.ui(hd.w),st.slots[j])
                    seen[desc.address]=h.Record(desc.uid,desc.address,desc.leaf,data);uids.add(desc.uid)
            assert set(seen)==set(range(c.N))
            for address,r in seen.items():
                assert r.payload==payload(address,truth[address],c.B)
                assert r.leaf==m.terminal_pos[address]
            checks+=1
    return m,checks

def main():
    install(h);uniform=[]
    for kind in ('path','deferred','sde','ring','gc_ring','r0'):
        for fused in ([False,True] if kind in ('ring','r0') else [True]):
            kw=dict(kind=kind,L=4,N=16,B=64,Z=4,A=3,S=3,R=128,fused=fused)
            a,_=perform(original,original.Config(**kw));b,_=perform(h,h.Config(**kw))
            assert a.io.events==b.io.events and a.anchor()==b.anchor()
            assert (a.P.calls,a.P.nonces,a.P.samples)==(b.P.calls,b.P.nonces,b.P.samples)
            uniform.append(dict(kind=kind,fusion=fused,rpcs=len(a.io.events),exact_transcript_and_state=True))
    rows=[]
    for kind in ('path','deferred','sde','ring','gc_ring','r0'):
        for fused in ([False,True] if kind in ('ring','gc_ring','r0') else [True]):
            kwargs=dict(kind=kind,L=5,N=32,B=64,Z=4,A=3,S=4,R=128,fused=fused)
            if kind in ('path','deferred','sde'):kwargs['Z_by_depth']=(4,2,1,3,4,4)
            else:kwargs['S_by_depth']=(3,2,1,4,2,3)
            m,n=perform(h,h.Config(**kwargs),steps=256,audit=True)
            row=dict(kwargs,checked_complete_states=n,rpcs=m.io.rpc_count,invoice_matched=True)
            rows.append(row)
    attacks=[]
    for family in ('IR_Z','AB_S'):
        kwargs=dict(kind='sde' if family=='IR_Z' else 'r0',L=4,N=16,B=64,R=128)
        kwargs['Z_by_depth' if family=='IR_Z' else 'S_by_depth']=(4,2,1,3,4)
        m,_=perform(h,h.Config(**kwargs),steps=8)
        m.io.mutator=lambda c,op,seq,stage,meta,req,res:res[:-1]+bytes([res[-1]^1])
        try:m.access(0)
        except Exception:pass
        else:raise AssertionError('tampered response accepted')
        assert m.dead
        before=m.io.seq
        try:m.access(1)
        except h.Reject:pass
        else:raise AssertionError('fail-stop retried')
        assert m.io.seq==before
        attacks.append(dict(family=family,rejected=True,no_retry_io=True))
    out=dict(status='passed',uniform_differential=uniform,heterogeneous_configs=rows,active_rejections=attacks,
             total_complete_state_checks=sum(r['checked_complete_states'] for r in rows),
             scope='functional invariants/actual framing only; no nonuniform capacity certificate or native IR/AB closure',
             source_hashes={p.name:sha(p) for p in Path(__file__).parent.glob('*heterogen*.py')})
    save(PACKAGE/'results/heterogeneous_regression.json',out)
    print(json.dumps(dict(status='passed',uniform=len(uniform),heterogeneous=len(rows),complete_states=out['total_complete_state_checks'],tamper=len(attacks))))
if __name__=='__main__':main()
