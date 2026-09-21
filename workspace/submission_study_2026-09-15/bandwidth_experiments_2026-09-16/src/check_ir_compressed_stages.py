"""Cross-slot compressed reset ownership, serial equivalence and fail-stop."""
from common import *
import hmac
import ir_dwb_runtime as rt
import heterogeneous_oram as h
from frontends import FreecursiveFront,initial_payload
from dwb_compressed_frontend import StagedCompressedFront,CompressedWriteback as StagedWriteback,Reject
from dwb_staged_frontend import DirtyEntry
from ir_compressed_controller import identity
from audit_frontend_batches import check_bill


def create(kind,serial=False):
    rt.install(dict(seed=55,R=480,cached_levels=2,Z_by_depth=[4,4,2,2,3,4,4]))
    cls=FreecursiveFront if serial else StagedCompressedFront
    return cls(kind,N=64,B=64,X=8,beta=1,compressed=True,plb=3,seed=31,profile=(4,3,4))


def leaf(f,*parts):
    raw=b''.join(len(x).to_bytes(4,'big')+x for x in (str(v).encode() for v in parts))
    return int.from_bytes(hmac.new(f.leaves.key,raw,hashlib.sha512).digest(),'big')&((1<<f.L)-1)


def inventory(f,truth=None):
    b=f.backend;t=b.tree;c=b.c;P=h.PRF(b.p.key);records=dict(t.stash);uids={r.uid for r in records.values()}
    for (tree,node),stored in list(b.server.buckets.items())+list(b.io.local_buckets.items()):
        if c.rootless and node==1:continue
        bc=c.at(node);pub=stored.header[:h.PUBLIC]
        hd=h.Header.decode(bc,pub,P.decrypt(t.ctx,t.oid(node),pub,stored.header[h.PUBLIC:]))
        for j,d in hd.live.items():
            assert d.address not in records and d.uid not in uids
            value=P.decrypt(t.ctx,t.oid(node,j),h.ui(hd.w),stored.slots[j])
            records[d.address]=h.Record(d.uid,d.address,d.leaf,value);uids.add(d.uid)
            assert h.node(d.leaf,h.depth(node),c.L)==node
            if c.selective:assert h.depth(node) in h.gc(hd.gamma,d.leaf,c.L)
    assert not(set(records)&set(f.cache)) and set(records)|set(f.cache)==set(range(f.total))
    reset=getattr(f,'pending_reset',None)
    for level,count in enumerate(f.counts):
        for i in range(count):
            a=f.addr(level,i)
            actual=f.cache[a].parked_leaf if a in f.cache else records[a].leaf
            if level==len(f.counts)-1:expected=f.top[i]
            else:
                pi,j=divmod(i,f.X);pa=f.addr(level+1,pi)
                data=f.cache[pa].data if pa in f.cache else records[pa].payload
                group,counts=f.decode_map(data);counter=counts[j]
                if reset is not None and reset.parent.address==pa and j<reset.cursor:group+=1;counter=0
                expected=leaf(f,'compressed-leaf',a,group,counter)
            assert actual==expected,(level,i,actual,expected,f.reset_snapshot() if reset else None)
            if level==0 and truth is not None:assert records[a].payload==truth[a]
    if reset is not None:assert reset.parent.address in f.pinned and f.cache[reset.parent.address] is reset.parent
    return records


def main():
    source=identity();serial=[];interrupt=[];faults=[];kinds=('path','deferred','sde','ring','gc_ring','r0')
    for kind in kinds:
        f=create(kind);reference=create(kind,serial=True)
        seq=[0,0,0,8,16,24,32,40,48,56,0,8,16,24,32,40,48,56,0]*2
        for i,a in enumerate(seq):
            value=(i+1000).to_bytes(8,'big')+bytes(56)
            assert f.access(a,value)==reference.access(a,value)
            assert f.backend.io.snapshot()==reference.backend.io.snapshot(),(kind,'serialized execution differs',i)
            assert f.backend.p.calls==reference.backend.p.calls and f.backend.p.nonces==reference.backend.p.nonces
            assert f.cache==reference.cache and f.top==reference.top
            assert f.backend.tree.stash==reference.backend.tree.stash
            assert f.backend.tree.t==reference.backend.tree.t and f.backend.tree.g==reference.backend.tree.g
            assert f.pending_reset is None and not f.pinned
        assert f.metrics['group_resets']>0 and f.metrics['group_cached_rotations']>0
        inventory(f);check_bill(f.backend.io.snapshot())
        serial.append(dict(kind=kind,requests=len(seq),group_resets=f.metrics['group_resets'],cached_rotations=f.metrics['group_cached_rotations'],
            backend_reset_slots=f.metrics['group_backend_slots'],complete_transcript_equal=True,completed_state_equal=True))
        for pause in (0,1,4,7,8,9):
            f=create(kind);f.access(0);truth={a:initial_payload(a,64) for a in range(64)}
            entry=DirtyEntry(0,(888).to_bytes(8,'big')+bytes(56));current=[True]
            tx=StagedWriteback(f,entry,lambda e:current[0]);f.backend.io.reset_meter()
            for _ in range(pause):
                assert tx.advance()
                if tx.state=='committed':truth[0]=entry.payload
                inventory(f,truth)
            assert f.metrics['dwb_group_reset_slots']==sum(e['type']=='group_reset' for e in tx.events)
            assert f.metrics['dwb_posmap_slots']==sum(e['type']=='posmap' for e in tx.events)
            if pause<9:
                before=(f.backend.tree.t,f.backend.io.snapshot()['total_bytes']);current[0]=False
                assert not tx.advance() and tx.state=='cancelled' and entry.dirty
                assert before==(f.backend.tree.t,f.backend.io.snapshot()['total_bytes'])
                if f.pending_reset is not None:assert f.pinned=={f.pending_reset.parent.address} and list(f.pin_counts.values())==[1]
                else:assert not f.pinned
            else:assert tx.state=='committed' and not entry.dirty
            # Foreground ownership and map evictions remain valid after a reset
            # was cancelled halfway through; mandatory work is billed normally.
            for a in (8,16,24,32,40,48,56,0):assert f.access(a)==truth[a]
            inventory(f,truth);check_bill(f.backend.io.snapshot());assert not f.pinned
            interrupt.append(dict(kind=kind,pause=pause,result=tx.state,reset_and_parent_consistent=True))
        f=create(kind);f.access(0);entry=DirtyEntry(0,(901).to_bytes(8,'big')+bytes(56))
        tx=StagedWriteback(f,entry,lambda e:True);assert tx.advance() and f.pending_reset is not None
        entry.version+=1;entry.payload=(902).to_bytes(8,'big')+bytes(56)
        assert not tx.advance() and tx.state=='cancelled' and entry.dirty
        tx=StagedWriteback(f,entry,lambda e:True)
        while tx.state=='pending':assert tx.advance();inventory(f)
        assert f.access(0)==entry.payload and not entry.dirty
        interrupt.append(dict(kind=kind,case='version_change_mid_group_reset',only_latest_version_committed=True))
        # A new foreground access cancels the DWB intent, then completes the
        # remaining mandatory rotations rather than discarding the descriptor.
        f=create(kind);f.access(0);entry=DirtyEntry(0,(903).to_bytes(8,'big')+bytes(56))
        tx=StagedWriteback(f,entry,lambda e:True);assert tx.advance();assert f.pending_reset is not None
        assert f.access(8)==initial_payload(8,64) and tx.state=='cancelled' and entry.dirty
        assert f.access(0)==initial_payload(0,64);inventory(f)
        interrupt.append(dict(kind=kind,case='foreground_preemption_mid_group_reset',dirty_preserved=True))
    for phase in ('group_reset','final_data'):
        for kind,op in (('sde',h.OPEN_FULL),('sde',h.WRITE),('r0',h.OPEN_HEAD),('r0',h.READ_SLOTS),('r0',h.WRITE)):
            f=create(kind);f.access(0);entry=DirtyEntry(0,(999).to_bytes(8,'big')+bytes(56))
            tx=StagedWriteback(f,entry,lambda e:True)
            for _ in range(1 if phase=='group_reset' else 8):assert tx.advance()
            fired=[]
            def mutate(config,opcode,seq,stage,meta,request,response):
                if not fired and opcode==op and stage=='logical':
                    fired.append(f.backend.p.decryptions);return response[:-1]+bytes([response[-1]^1])
                return response
            f.backend.io.mutator=mutate
            try:tx.advance()
            except (Reject,h.Reject):pass
            else:raise AssertionError('tampered compressed stage accepted')
            assert fired and f.dead and f.backend.tree.dead and entry.dirty and tx.state=='failed'
            assert f.backend.p.decryptions==fired[0]
            before=f.backend.io.snapshot()['total_bytes']
            for call in (tx.advance,lambda:f.access(0),f.advance_reset):
                try:call()
                except (Reject,h.Reject):pass
                else:raise AssertionError('failed compressed transaction resumed')
            assert f.backend.io.snapshot()['total_bytes']==before
            faults.append(dict(kind=kind,phase=phase,opcode=op,dirty_preserved=True,no_retry=True))
    assert source==identity()
    save(PACKAGE/'results/ir_compressed_stage_checks.json',dict(status='passed',source_hashes=source,serial_equivalence=serial,
        interrupt_cases=interrupt,active_rejections=faults,checker_sha256=sha(__file__),
        scope='compressed counters and mandatory group-reset state over the existing authenticated depth-cache Transfer; not IR-Stash or a new capacity proof',
        adaptive_security_proof=False,capacity_certificate=False))
    print(json.dumps(dict(status='passed',serial=len(serial),interruptions=len(interrupt),active_failures=len(faults))),flush=True)


if __name__=='__main__':main()
