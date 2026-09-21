"""Cross-slot ownership, cancellation, billing and fail-stop checks for DWB."""
from common import *
import composition_runtime as runtime
import transfer_backend_fixed as fixed
import optimized_oram as engine
from optimized_oram import OPEN_FULL,OPEN_HEAD,READ_SLOTS,WRITE,Reject
from fast_prf import make_fast_prf
from dwb_staged_frontend import StagedRawMapFront,StagedWriteback,DirtyEntry,identity
from frontends import initial_payload,FreecursiveFront
from check_prototypes import inventory
from audit_frontend_batches import check_bill


def create(kind):
    runtime.PRF=make_fast_prf(engine);runtime.TransferTree=fixed.TransferTree
    runtime.install(312,256)
    return StagedRawMapFront(kind,N=64,B=64,X=8,plb=3,seed=21,profile=(4,3,4))


def value(n):return n.to_bytes(8,'big')+bytes(56)


def check_owners(f):
    # Only a test oracle decrypts the remote inventory. It never drives choices.
    active=inventory(f.backend);cached=set(f.cache)
    assert not(active&cached) and active|cached==set(range(f.total))
    assert not f.pinned


def main():
    cases=[];tamper=[];size_pairs=[];serial=[]
    for kind in ('path','deferred','sde','ring','gc_ring','r0'):
        for pause in (0,1,2,3):
            f=create(kind);entry=DirtyEntry(0,value(888));current=[True]
            tx=StagedWriteback(f,entry,lambda e:current[0]);f.backend.io.reset_meter()
            for _ in range(pause):assert tx.advance();check_owners(f)
            bill=f.backend.io.snapshot();check_bill(bill)
            if pause<3:
                before=(f.backend.tree.t,f.backend.tree.g,f.backend.p.calls,bill['total_bytes'])
                current[0]=False;assert not tx.advance() and tx.state=='cancelled'
                after=(f.backend.tree.t,f.backend.tree.g,f.backend.p.calls,f.backend.io.snapshot()['total_bytes'])
                assert before==after and entry.dirty
                # Read after cancelling PosMap work must still reach old data.
                assert f.access(0)==initial_payload(0,64)
            else:
                assert tx.state=='committed' and not entry.dirty
                assert f.access(0)==value(888)
            # Exercise parked-map eviction and subsequent reload, not only cached hits.
            expected={a:initial_payload(a,64) for a in range(64)}
            if pause==3:expected[0]=value(888)
            for a in [8,16,24,32,40,48,56,0,9,17,25,33,41,49,57,0]:
                assert f.access(a)==expected[a]
            check_owners(f)
            cases.append(dict(kind=kind,completed_stages=pause,status=tx.state,stage_types=[e['type'] for e in tx.events],billed_bytes=bill['total_bytes'],ownership_after_each_stage=True))
        f=create(kind);e=DirtyEntry(0,value(901));tx=StagedWriteback(f,e,lambda e:True)
        assert tx.advance();e.payload=value(902);e.version+=1
        assert not tx.advance() and tx.state=='cancelled' and e.dirty
        tx2=StagedWriteback(f,e,lambda e:True)
        while tx2.state=='pending':assert tx2.advance()
        assert f.access(0)==value(902) and not e.dirty
        cases.append(dict(kind=kind,case='dirty_version_changed_then_restarted',ownership_after_each_stage=True))
        f=create(kind);e=DirtyEntry(0,value(903));tx=StagedWriteback(f,e,lambda e:True);assert tx.advance()
        assert f.access(8)==initial_payload(8,64) and tx.state=='cancelled' and e.dirty
        check_owners(f);cases.append(dict(kind=kind,case='foreground_preemption'))
        # Compare the data stage with one dummy at the SAME endpoint/state.
        # This is a conditional size check, not a new security coupling theorem.
        f=create(kind);e=DirtyEntry(0,value(904));tx=StagedWriteback(f,e,lambda e:True)
        assert tx.advance() and tx.advance()
        parent=f.cache[f.addr(1,0)];oldleaf=int.from_bytes(parent.data[:4],'big')
        control=create(kind);control_e=DirtyEntry(0,value(904));control_tx=StagedWriteback(control,control_e,lambda e:True)
        assert control_tx.advance() and control_tx.advance()
        assert control.backend.io.snapshot()['transcript_sha256']==f.backend.io.snapshot()['transcript_sha256']
        control_tx.cancel('conditional size control');dummy=control.backend
        dummy.io.reset_meter();f.backend.io.reset_meter()
        dummy.tick(None,oldleaf);assert tx.advance()
        a=dummy.io.snapshot();b=f.backend.io.snapshot();check_bill(a);check_bill(b)
        for k in ('rpc','total_bytes','request_bytes','response_bytes','components','by_stage','by_tree','opcode_counts'):assert a[k]==b[k],(kind,k)
        size_pairs.append(dict(kind=kind,bytes=a['total_bytes'],rpc=a['rpc'],conditional_dummy_vs_data_size_equal=True))
        f=create(kind);e=DirtyEntry(0,value(905));tx=StagedWriteback(f,e,lambda e:True)
        while tx.state=='pending':assert tx.advance()
        control=FreecursiveFront(kind,N=64,B=64,X=8,plb=3,seed=21,profile=(4,3,4),compressed=False)
        assert control.access(0,value(905))==initial_payload(0,64)
        assert f.backend.io.snapshot()==control.backend.io.snapshot()
        assert f.backend.p.calls==control.backend.p.calls
        assert f.backend.tree.t==control.backend.tree.t and f.backend.tree.g==control.backend.tree.g
        assert f.cache==control.cache and f.top==control.top
        serial.append(dict(kind=kind,complete_transcript_and_counts_equal=True,completed_state_equal=True))
    for kind,opcode in [('sde',OPEN_FULL),('sde',WRITE),('r0',OPEN_HEAD),('r0',READ_SLOTS),('r0',WRITE)]:
        f=create(kind);e=DirtyEntry(0,value(999));tx=StagedWriteback(f,e,lambda e:True)
        assert tx.advance() and tx.advance();hit=[False]
        def mutate(c,op,seq,event,meta,request,response):
            if not hit[0] and op==opcode and event=='logical':
                hit[0]=True;return response[:-1]+bytes([response[-1]^1])
            return response
        f.backend.io.mutator=mutate
        try:tx.advance()
        except Reject:pass
        else:raise AssertionError('corrupt final stage accepted')
        assert hit[0] and e.dirty and tx.state=='failed' and f.dead and f.backend.tree.dead
        billed=f.backend.io.snapshot()['total_bytes']
        for call in (tx.advance,lambda:f.access(0)):
            try:call()
            except Reject:pass
            else:raise AssertionError('failed DWB resumed')
        assert f.backend.io.snapshot()['total_bytes']==billed
        tamper.append(dict(kind=kind,opcode=opcode,dirty_preserved=True,no_retry_io=True))
    save(PACKAGE/'results/dwb_stage_checks.json',dict(status='passed',functional=cases,active_rejection=tamper,conditional_size_pairs=size_pairs,serial_equivalence=serial,
        source_identity=identity(),checker_sha256=sha(__file__),
        scope='authenticated raw-map staged DWB interface; no native IR-Stash/Alloc composition, compressed counters, CPU timing or performance claim'))
    print(json.dumps(dict(status='passed',functional=len(cases),active_rejection=len(tamper),conditional_size_pairs=len(size_pairs),serial_equivalence=len(serial))))

if __name__=='__main__':main()
