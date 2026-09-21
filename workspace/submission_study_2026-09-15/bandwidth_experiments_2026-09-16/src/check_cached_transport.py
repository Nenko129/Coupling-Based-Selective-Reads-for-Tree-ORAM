from common import *
import dataclasses
import heterogeneous_oram as h
import cached_transport as cache
from workloads import make_trace,payload

OriginalServer=h.Server;OriginalTransport=h.Transport

def execute(c,cut):
    if cut is None:h.Server=OriginalServer;h.Transport=OriginalTransport
    else:cache.install({0:cut})
    m=h.RecursiveORAM([c],b'K'*64)
    if cut is not None:m.io.capture_limit=100000
    m.initialize(lambda a:payload(a,0,c.B));truth=[0]*c.N
    for a,v in make_trace(c.N,96,889,'uniform'):
        got=m.access(a,None if v is None else payload(a,v,c.B));assert got==payload(a,truth[a],c.B)
        if v is not None:truth[a]=v
    return m

def main():
    results=[];models=[]
    for kind in ('path','deferred','sde','ring','gc_ring','r0'):
        for fused in ([False,True] if kind in ('ring','gc_ring','r0') else [True]):
            extra={'Z_by_depth':(4,2,1,3,4)} if not kind in ('ring','gc_ring','r0') else {'S_by_depth':(3,2,1,3,2)}
            c=h.Config(kind,4,16,64,Z=4,A=3,S=3,R=128,fused=fused,**extra)
            original=execute(c,None);hashes=[(e['request_sha256'],e['response_sha256']) for e in original.io.events]
            for cut in (0,1,2,4):
                m=execute(c,cut)
                assert m.io.logical_events==hashes and m.anchor()==original.anchor()
                assert (m.P.calls,m.P.nonces,m.P.samples,m.P.decryptions)==(original.P.calls,original.P.nonces,original.P.samples,original.P.decryptions)
                union=dict(m.server.buckets);union.update(m.io.local_buckets);assert union==original.server.buckets
                tags=dict(m.server.global_tags);tags.update(m.io.local_tags);assert tags==original.server.global_tags
                assert all(h.depth(b)>=cut for _,b in m.server.buckets)
                assert all(h.depth(b)<cut for _,b in m.io.local_buckets)
                if cut==0:
                    assert [(e['request_sha256'],e['response_sha256']) for e in m.io.events]==hashes
                results.append(dict(kind=kind,fusion=fused,cut=cut,logical_transcript_state_and_random_tape_identical=True,
                     remote_actual_bytes=m.io.up+m.io.down,full_reference_bytes=sum(e['request_bytes']+e['response_bytes'] for e in original.io.events),
                     local_cache=m.io.cache_storage(),remote_holds_no_cached_objects=True))
                if cut==2:models.append(m)
    attacks=[]
    for kind in ('sde','r0'):
        for attack in ('header','slots','ack','sequence'):
            c=h.Config(kind,4,16,64,R=128);m=execute(c,2);oldcache=dict(m.io.local_buckets);oldtags=dict(m.io.local_tags);trigger=[False]
            def mutate(c,op,seq,stage,meta,req,res):
                wanted=h.WRITE if attack=='ack' else h.READ_SLOTS if attack=='slots' else h.OPEN_HEAD if c.ring else h.OPEN_FULL
                if not c.ring and attack=='slots':wanted=h.OPEN_FULL
                if trigger[0] or op!=wanted:return res
                trigger[0]=True
                if attack=='sequence':return h.frame(op,c.tree,seq-1,h.parse_frame(res)[4],True)
                if attack=='ack':return h.frame(op,c.tree,seq,b'bad',True)
                return res[:-1]+bytes([res[-1]^1])
            m.io.mutator=mutate
            try:m.access(0)
            except h.Reject:pass
            else:raise AssertionError('tamper accepted')
            assert trigger[0] and m.dead
            # First access stage fails before its local object installation.
            assert m.io.local_buckets==oldcache and m.io.local_tags==oldtags
            seq=m.io.wire_seq
            try:m.access(1)
            except h.Reject:pass
            else:raise AssertionError('retry accepted')
            assert seq==m.io.wire_seq
            attacks.append(dict(kind=kind,mutation=attack,rejected=True,no_local_commit_on_bad_ack=True,no_retry_io=True))
    result=dict(status='passed',differential_configs=results,active_rejections=attacks,
         scope='static public tree-top representation, preserves remap/service policy; not native IR-Stash hit cancellation',
         source_hashes={p.name:sha(p) for p in (Path(__file__).parent/'cached_transport.py',Path(__file__).parent/'heterogeneous_oram.py',Path(__file__))})
    save(PACKAGE/'results/cached_transport_regression.json',result)
    print(json.dumps(dict(status='passed',differential_configs=len(results),active_rejections=len(attacks))))
if __name__=='__main__':main()
