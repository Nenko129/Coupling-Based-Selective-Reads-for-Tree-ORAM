"""Semantic coupling witness, accounting checks, and tamper/fail-stop checks.

This tests a projected state relation, not equality of nonces/count/used/roots.
The shared remap tape below is a test instrument, never a production shortcut.
"""
from minimal_runtime import *
from workloads import make_trace,payload

class RemapTape(h.PRF):
    def __init__(self,key):super().__init__(key);self.remaps=0
    def draw(self,ctx,event):
        if event==b'REMAP':
            self.remaps+=1
            return int.from_bytes(self.F(b'CHECK-ONLY-REMAP',b'COMMON-TAPE',h.ui(self.remaps)),'big')
        return super().draw(ctx,event)

def projection(m):
    t=m.trees[0];c=t.c;inspect=h.PRF(m.P.key);out={}
    for r in t.stash.values():out[r.address]=('stash',r.uid,r.leaf,r.payload.hex())
    for (tree,b),st in m.server.buckets.items():
        pub=st.header[:h.PUBLIC]
        hd=h.Header.decode(c.at(b),pub,inspect.decrypt(c.context(),t.oid(b),pub,st.header[h.PUBLIC:]))
        assert hd.gamma==h.generation(t.g,h.depth(b),b-(1<<h.depth(b)))
        assert len(hd.live)<=c.at(b).Z
        for j,x in hd.live.items():
            assert x.address not in out
            assert h.node(x.leaf,h.depth(b),c.L)==b and h.depth(b) in h.gc(t.g,x.leaf,c.L)
            plain=inspect.decrypt(c.context(),t.oid(b,j),h.ui(hd.w),st.slots[j])
            out[x.address]=(b,x.uid,x.leaf,plain.hex())
    return (out,tuple(m.terminal_pos),t.t,t.g,t.uid)

def main():
    source=identity();original_prf=h.PRF;rows=[];faults=[]
    cache.install({0:0})
    try:
        h.PRF=RemapTape
        for family in ('IR','AB'):
            for layout in ('uniform','depth'):
                kw=dict(kind='sde' if family=='IR' else 'gc_ring',L=4,N=16,B=64,Z=4,A=3,S=2,R=128,compact=False,fused=False)
                if layout=='depth':kw['Z_by_depth' if family=='IR' else 'S_by_depth']=(4,2,1,3,4)
                a=h.RecursiveORAM([FullProbeConfig(**kw)],b'K'*64);b=h.RecursiveORAM([h.Config(**kw)],b'K'*64)
                for m in (a,b):m.initialize(lambda addr:payload(addr,0,64));m.io.reset_meter()
                assert projection(a)==projection(b)
                truth=[0]*16
                for addr,v in make_trace(16,192,313,'uniform'):
                    value=None if v is None else payload(addr,v,64)
                    aa=a.access(addr,value);bb=b.access(addr,value)
                    assert aa==bb==payload(addr,truth[addr],64)
                    if v is not None:truth[addr]=v
                    assert projection(a)==projection(b)
                bills=[m.io.snapshot() for m in (a,b)]
                assert all(sum(x['components'].values())==x['total_bytes'] for x in bills)
                rows.append(dict(family=family,layout=layout,boundaries=193,full_probe_bytes=bills[0]['total_bytes'],selective_bytes=bills[1]['total_bytes'],
                    saving_pct=100*(1-bills[1]['total_bytes']/bills[0]['total_bytes']),projected_state_equal=True,
                    exact_ciphertext_state_equal=False))
                for label,m in [('full_probe',a),('selective',b)]:
                    m.io.mutator=lambda c,op,seq,stage,meta,req,res:res[:-1]+bytes([res[-1]^1])
                    try:m.access(0)
                    except Exception:pass
                    else:raise AssertionError('corrupt opening accepted')
                    assert m.dead;before=m.io.wire_seq
                    try:m.access(1)
                    except h.Reject:pass
                    else:raise AssertionError('fail-stop retry accepted')
                    assert before==m.io.wire_seq
                    faults.append(dict(family=family,layout=layout,arm=label,rejected=True,no_retry_io=True))
    finally:h.PRF=original_prf
    assert source==identity()
    result=dict(status='passed',coupling_cases=rows,complete_boundary_checks=sum(r['boundaries'] for r in rows),active_faults=faults,
                source_hashes=source,scope='finite projected-state regression and authentication failure checks, not universal proof or tail certificate')
    save(HOME/'results/minimal_contract_checks.json',result)
    print(json.dumps(dict(status='passed',boundaries=result['complete_boundary_checks'],faults=len(faults))),flush=True)
if __name__=='__main__':main()
