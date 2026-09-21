"""Differential byte/transcript/complete-state checks plus active rejection."""
from common import *
import optimized_oram as ref
from optimized_oram import Config,RecursiveORAM,Transport,Reject,parse_frame,frame
from meter import StreamingTransport
from workloads import make_trace,payload

def execute(c,transport):
    ref.Transport=transport;model=RecursiveORAM([c],b'C'*64)
    if transport is StreamingTransport:model.io.capture_limit=100000
    model.initialize(lambda a:payload(a,0,c.B));truth=[0]*c.N
    for a,v in make_trace(c.N,32,710,'uniform'):
        old=model.access(a,None if v is None else payload(a,v,c.B));assert old==payload(a,truth[a],c.B)
        if v is not None:truth[a]=v
    return model

def main():
    rows=[]
    specs=[Config(k,3,8,64,S=3,R=64) for k in ('path','deferred','sde','ring','gc_ring','r0')]
    specs.extend(Config('r0',3,8,64,Z=7,A=6,S=6,R=64,compact=c,fused=f) for c,f in ((False,False),(False,True),(True,False),(True,True)))
    for c in specs:
        a=execute(c,Transport);b=execute(c,StreamingTransport)
        assert a.io.events==b.io.events and a.anchor()==b.anchor()
        assert a.server.buckets==b.server.buckets and a.server.global_tags==b.server.global_tags
        assert (a.P.calls,a.P.nonces,a.P.samples,a.P.decryptions)==(b.P.calls,b.P.nonces,b.P.samples,b.P.decryptions)
        rows.append(dict(kind=c.kind,compact=c.compact,fusion=c.fused,Z=c.Z,A=c.A,S=c.S,rpcs=len(a.io.events),
                         byte_identical_transcript=True,completed_state_identical=True,random_consumption_identical=True))
    attacks=[]
    for kind in ('sde','r0'):
        for variant in ('body_bitflip','replay_sequence','bad_ack'):
            m=execute(Config(kind,3,8,64,S=3,R=64),StreamingTransport)
            fired=[False]
            def corrupt(c,op,seq,stage,meta,request,response):
                if fired[0]:return response
                if variant=='bad_ack' and op!=ref.WRITE:return response
                fired[0]=True
                if variant=='body_bitflip':return response[:-1]+bytes([response[-1]^1])
                o,t,s,f,body=parse_frame(response)
                if variant=='replay_sequence':return frame(o,t,s-1,body,True)
                return frame(o,t,s,b'not-an-ack',True)
            m.io.mutator=corrupt;rejected=False
            try:m.access(0)
            except Reject:rejected=True
            assert fired[0] and rejected and m.dead
            seq=m.io.seq
            try:m.access(1)
            except Reject:pass
            else:raise AssertionError('fail-stop retry accepted')
            assert m.io.seq==seq
            attacks.append(dict(kind=kind,mutation=variant,rejected=True,no_retry_io=True))
    result=dict(status='passed',differential_configs=rows,active_rejections=attacks,source_hashes=source_identity())
    save(PACKAGE/'results/meter_regression.json',result)
    print(json.dumps(dict(status='passed',differential_configs=len(rows),active_rejections=len(attacks))))
if __name__=='__main__':main()
