"""Concrete active-response checks for classical core profiles, including n16."""
from common import *
from dataclasses import asdict
import optimized_oram as e
from meter import StreamingTransport


def trial(kind,z,a,s,fused,fault):
    c=e.Config(kind,3,8,64,z,a,s,256,0,True,fused)
    old_transport=e.Transport;e.Transport=StreamingTransport
    try:model=e.RecursiveORAM([c],b'A'*64)
    finally:e.Transport=old_transport
    model.initialize(lambda x:bytes([x])*64)
    opening=e.OPEN_FULL if kind=='path' else e.OPEN_HEAD
    previous=[]
    def capture(config,op,seq,stage,meta,request,response):
        if op==opening:previous.append(response)
        return response
    model.io.mutator=capture
    assert model.access(0)==bytes(64) and previous
    committed=model.committed;events=[]
    wanted=e.READ_SLOTS if fault=='payload_proof' else (e.WRITE if fault=='ack_route' else opening)
    def alter(config,op,seq,stage,meta,request,response):
        if op!=wanted or events:return response
        events.append(dict(opcode=op,sequence=seq,decryptions_before_rejection=model.P.decryptions))
        if fault=='replay':return previous[0]
        result=bytearray(response)
        result[12 if fault=='ack_route' else -1]^=1
        return bytes(result)
    model.io.mutator=alter
    try:model.access(1,bytes([99])*64)
    except e.Reject as ex:reason=str(ex)
    else:raise AssertionError('active corruption accepted')
    assert len(events)==1 and model.dead and not model.busy
    assert model.committed==committed
    assert model.P.decryptions==events[0]['decryptions_before_rejection']
    serial=model.io.seq
    try:model.access(2)
    except e.Reject:pass
    else:raise AssertionError('client resumed after rejection')
    assert model.io.seq==serial
    return dict(config=asdict(c),fault=fault,event=events[0],reason=reason,
                no_decryption_after_corrupt_response=True,committed_anchor_unchanged=True,
                no_further_rpc=True,remote_rollback_claim=False)


def main():
    identity=source_identity();rows=[]
    for kind,z,a,s in [('path',4,3,3),('path',5,3,3),('ring',4,3,3),('ring',7,6,9)]:
        for fused in ((True,) if kind=='path' else (False,True)):
            for fault in (('opening','ack_route','replay') if kind=='path'
                          else ('opening','payload_proof','ack_route','replay')):
                rows.append(trial(kind,z,a,s,fused,fault))
    assert len(rows)==22 and identity==source_identity()
    save(PACKAGE/'results/classical_active_failstop_checks.json',dict(status='passed',rows=rows,
        source_hashes=identity,checker_sha256=sha(__file__),cases=len(rows),
        scope='single-tree concrete corrupt/replayed response and fail-stop regressions, including Path Z5 and Ring n16',
        full_adaptive_simulation_proof=False,cryptographic_assumption_verified=False))
    print(json.dumps(dict(status='passed',cases=len(rows))))


if __name__=='__main__':main()
