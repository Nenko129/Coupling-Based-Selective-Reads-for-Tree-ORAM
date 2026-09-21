"""Whole-state oracle, encrypted payload and adversarial wire checks.

The runtime never calls this oracle. All whole-state scans below are harness
instrumentation and are not silently counted as ordinary client operations.
Wire micro-costs are diagnostic, not an AB/CB application benchmark.
"""
from common import PACKAGE,save,sha,digest
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import random
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from ab_deadq_allocator_model import Allocator,Geometry,reverse
from ab_deadq_routed_allocator import Layout,provision
from ab_deadq_authenticated_store import AuthenticationFailure


def payload(uid,B):return hashlib.shake_256(b'deadq-record'+struct.pack('>Q',uid)).digest(B)


def snapshot(client,wire):
    """Independent decoder, including independently assembled AEAD context."""
    g=client.g;rows=wire.server.committed.rows
    state=dict(maps=[],valid=[],epoch=[],owner=[],version=[],queue=[],scheduled=struct.unpack('>Q',rows[0])[0])
    for b in range(g.buckets):
        raw=rows[1+b];e,n=struct.unpack('>QI',raw[:12]);cells=[struct.unpack('>IB',raw[12+5*j:17+5*j]) for j in range(n)]
        state['epoch'].append(e);state['maps'].append([p for p,v in cells]);state['valid'].append([bool(v) for p,v in cells])
    for p in range(g.physical):
        b,j,v=struct.unpack('>IIQ',rows[1+g.buckets+p])
        state['owner'].append(None if b==2**32-1 else (b,j));state['version'].append(v)
    q=rows[1+g.buckets+g.physical];n=struct.unpack('>I',q[:4])[0]
    state['queue']=[struct.unpack('>IQ',q[4+12*j:16+12*j]) for j in range(n)]
    records={};remote=0
    for p,owner in enumerate(state['owner']):
        if owner is None:continue
        b,j=owner;e=state['epoch'][b];v=state['version'][p]
        raw=rows[2+g.buckets+g.physical+p]
        aad=b'DeadQ-data-v1\x00'+client.domain+struct.pack('>IIIQQ',b,j,p,e,v)
        plain=AESGCM(client.key).decrypt(raw[:12],raw[12:],aad)
        assert len(plain)==9+g.payload_bytes and plain[0] in (0,1)
        if plain[0]==0:assert plain==bytes(len(plain));continue
        uid=struct.unpack('>Q',plain[1:9])[0]
        assert uid not in records and plain[9:]==payload(uid,g.payload_bytes)
        records[uid]=(b,p);remote+=p//g.base!=b
    return state,records,remote


def check_state(client,wire,model,expected):
    state,records,remote=snapshot(client,wire)
    for name,value in state.items():assert value==getattr(model,name),name
    assert {uid:b for uid,(b,p) in records.items()}==expected
    assert client.cache is None and client.dirty is None and client.pending is None
    assert client.rows.work_root is None and client.rows.root==wire.server.committed.root
    assert set(vars(client))=={'rows','g','key','aead','domain','next_nonce','placement','cache','dirty','pending','last_workspace'}
    assert not any(isinstance(v,(list,dict,set)) for k,v in vars(client).items() if k!='last_workspace')
    return remote


def event_equal(actual,oracle):
    oracle={k:v for k,v in oracle.items() if k!='before_digest'}
    if oracle['operation']=='rebuild_consume':
        event_equal(actual['rebuild'],oracle['rebuild']);event_equal(actual['consume'],oracle['consume'])
    else:assert actual==oracle,(actual,oracle)


def wire_bill(frames,g):
    """Independent parser/accountant; no calls to runtime billing helpers."""
    depth=(g.count-1).bit_length();out=Counter();tx=None;step=0
    for request,response in frames:
        op=request[:1];out['rpc']+=1;out['request_bytes']+=len(request);out['response_bytes']+=len(response)
        if op==b'B':
            assert len(request)==len(response)==41 and response==b'b'+request[1:]
            assert tx is None;tx=struct.unpack('>Q',request[1:9])[0];step=0
            out['control_bytes']+=82;continue
        rid,sid=struct.unpack('>QI',request[1:13]);assert rid==tx and sid==step
        if op==b'C':
            assert len(request)==len(response)==45 and response==b'c'+request[1:]
            out['control_bytes']+=90;tx=None;out['commits']+=1;continue
        assert op in (b'G',b'U') and response[:17]==op.lower()+request[1:17]
        index=struct.unpack('>I',request[13:17])[0]
        length=struct.unpack('>I',response[17:21])[0]
        expected=(8 if index==0 else 12+5*(g.base+g.extra) if index<=g.buckets else
                  16 if index<1+g.buckets+g.physical else 4+12*g.queue_cap if index==1+g.buckets+g.physical else g.payload_bytes+37)
        assert length==expected
        body='data_record_bytes' if index>1+g.buckets+g.physical else 'metadata_bytes'
        out[body]+=length;out['proof_bytes']+=32*depth
        out['control_bytes']+=17+21
        assert len(response)==21+length+32*depth+(32 if op==b'U' else 0)
        if op==b'U':
            assert struct.unpack('>I',request[17:21])[0]==length and len(request)==21+length
            out[body]+=length;out['control_bytes']+=4+32;out['updates']+=1
        else:assert len(request)==17;out['reads']+=1
        step+=1
    assert tx is None
    out['total_bytes']=out['request_bytes']+out['response_bytes']
    assert out['total_bytes']==sum(out[k] for k in ('data_record_bytes','metadata_bytes','proof_bytes','control_bytes'))
    return dict(out)


def persist_wire(name,frames):
    raw=b''.join((json.dumps(dict(request=a.hex(),response=b.hex()),separators=(',',':'))+'\n').encode() for a,b in frames)
    path=PACKAGE/'results/ab_deadq_routed_wire'/f'{name}.jsonl.gz';path.parent.mkdir(exist_ok=True)
    path.write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    return dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path),uncompressed_sha256=hashlib.sha256(raw).hexdigest(),frames=len(frames))


class LastReal:
    def shuffle(self,items):items.sort(key=lambda v:v is not None)


def witness():
    g=Layout(2,2,1,2,4,64);records={1:[(91,payload(91,64))]}
    a,w=provision(g,records,key=hashlib.sha256(b'witness key').digest(),placement=LastReal())
    actions=[('rebuild',0,True),('rebuild',1,True),('consume',0,0),('consume',0,1),('rebuild',1,False),('rebuild',0,False)]
    steps=[]
    for op in actions:
        start=len(w.frames);root=a.rows.root;old_rows=list(w.server.committed.rows);e=a.prepare(*op)
        assert a.rows.root==root and w.server.committed.rows==old_rows
        event,result=a.commit();assert result is None
        state,real,remote=snapshot(a,w);assert set(real)=={91}
        steps.append(dict(action=op,event=event,records={str(k):v for k,v in real.items()},remote_real=remote,bill=wire_bill(w.frames[start:],g)))
    assert steps[-2]['records']['91']==(1,0) and steps[-1]['event']['rebuilt']==[0,1]
    assert steps[-1]['records']['91'][0]==1
    return dict(geometry=g.__dict__,physical_slots_before=4,physical_slots_after=g.physical,
        steps=steps,wire=persist_wire('zero_extra_encrypted_witness',w.frames),
        total_bill=wire_bill(w.frames,g),provisioned_row_bytes=sum(map(len,w.server.committed.rows)),
        server_merkle_tag_bytes=(2*w.server.committed.size-1)*32,
        trusted_serialized_root_key_domain_counters_bytes=32+32+32+12+8+4,
        memory_scope='selected persistent serialized fields only; excludes geometry, crypto runtime and transaction scratch; not actual peak')


def random_trial(seed,turns=200):
    g=Layout(4,3,2,3,8,64);rng=random.Random(seed);private=random.Random(seed+8000)
    a,w=provision(g,{b:[(b,payload(b,64))] for b in range(4)},key=hashlib.sha256(f'test key {seed}'.encode()).digest(),placement=private)
    model=Allocator(Geometry(4,3,2,3,8));expected={b:b for b in range(4)}
    out=Counter();nonces={row[:12] for row in w.server.committed.rows[g.queue_row+1:g.count]}
    assert len(nonces)==g.physical
    largest_workspace=0
    for turn in range(turns):
        actions=[]
        for b in range(4):
            actions.extend(('consume',b,j) for j,v in enumerate(model.valid[b]) if v)
            actions.extend([('rebuild',b,False),('gather',b),('rebuild_consume',b,0,False)])
        actions.append(('rebuild',reverse(model.scheduled%4,2),True))
        # Periodic forcing is public and independent of record content.
        op=('rebuild',reverse(model.scheduled%4,2),True) if turn%7==0 else actions[rng.randrange(len(actions))]
        admissions={}
        if op[0].startswith('rebuild'):
            for b in model.component(op[1]):
                if b not in expected:admissions[b]=[(b,payload(b,64))];expected[b]=b
        start=len(w.frames);root=a.rows.root;old=list(w.server.committed.rows)
        ae=a.prepare(*op,admissions=admissions);mt=model.prepare(*op)
        event_equal(ae,mt['event']);assert a.rows.root==root and w.server.committed.rows==old
        largest_workspace=max(largest_workspace,a.last_workspace['cached_serialized_bytes'])
        event,record=a.commit();model.commit(mt['expected_state_digest']);model.events=[]
        if record is not None:
            uid,body=record;assert body==payload(uid,64) and uid in expected;del expected[uid]
        out['remote_real_observations']+=check_state(a,w,model,expected)
        rebuild=event.get('rebuild') if op[0]=='rebuild_consume' else event if op[0]=='rebuild' else None
        if rebuild:
            out['expansions']+=rebuild['result']=='expanded';out['collateral_rebuilds']+=rebuild['collateral_buckets']>0
        out['fused_transactions']+=op[0]=='rebuild_consume';out['consumed_real_records']+=record is not None
        for req,rep in w.frames[start:]:
            if req[:1]==b'U' and struct.unpack('>I',req[13:17])[0]>g.queue_row:
                nonce=req[21:33];assert nonce not in nonces;nonces.add(nonce)
        # Fixture-internal all seals are installed; failure cases are separate.
        assert len(nonces)==a.next_nonce
    out.update(transitions=turns,seed=seed,nonce_count=len(nonces),largest_cached_serialized_rows=largest_workspace)
    return dict(out,geometry=g.__dict__,wire=persist_wire(f'trial_{seed}',w.frames),bill=wire_bill(w.frames,g),final_state_sha256=digest(snapshot(a,w)[0]))


def attacks():
    results=[]
    def fresh():return provision(Layout(2,2,1,2,4),key=hashlib.sha256(b'attack fixture').digest(),placement=random.Random(9))
    def rejection(name,a,w,action,expected_error=AuthenticationFailure):
        root=a.rows.root;n=len(w.frames)
        try:action()
        except expected_error as exc:
            assert a.dead and a.rows.root==root,(name,type(exc).__name__)
        else:raise AssertionError('attack accepted: '+name)
        n=len(w.frames)
        try:a.apply('gather',0)
        except AuthenticationFailure:pass
        else:raise AssertionError('resumed after '+name)
        assert len(w.frames)==n
        results.append(name)

    a,w=fresh()
    w.reply_filter=lambda req,rep:rep[:-1]+bytes([rep[-1]^1]) if req[:1]==b'G' else rep
    rejection('directory proof corruption',a,w,lambda:a.apply('consume',0,0))
    a,w=fresh();data_id=a.g.data_row(0)
    class NoDecrypt:
        def decrypt(self,*args):raise AssertionError('unauthenticated ciphertext reached AES-GCM')
    a.aead=NoDecrypt()
    w.reply_filter=lambda req,rep:rep[:22]+bytes([rep[22]^1])+rep[23:] if req[:1]==b'G' and struct.unpack('>I',req[13:17])[0]==data_id else rep
    rejection('ciphertext corruption caught by Merkle before decryption',a,w,lambda:a.apply('consume',0,0))
    a,w=fresh()
    w.reply_filter=lambda req,rep:rep[:-1]+bytes([rep[-1]^1]) if req[:1]==b'U' else rep
    rejection('incorrect post-update root',a,w,lambda:a.apply('consume',0,0))
    a,w=fresh()
    w.reply_filter=lambda req,rep:rep[:-1]+bytes([rep[-1]^1]) if req[:1]==b'C' else rep
    rejection('bad final commit root permanently stops client',a,w,lambda:a.apply('rebuild_consume',0,0,False))
    a,w=fresh();a.apply('consume',0,0);ack=w.frames[-1][1]
    w.reply_filter=lambda req,rep:ack if req[:1]==b'C' else rep
    rejection('previous transaction commit replay',a,w,lambda:a.apply('consume',0,1))
    a,w=fresh();a.apply('consume',0,0)
    prior=next(rep for req,rep in w.frames if req[:1]==b'G' and struct.unpack('>I',req[13:17])[0]==a.g.queue_row)
    w.reply_filter=lambda req,rep:rep[:17]+prior[17:] if req[:1]==b'G' and struct.unpack('>I',req[13:17])[0]==a.g.queue_row else rep
    rejection('old FIFO opening with rewritten response context',a,w,lambda:a.apply('consume',0,1))
    # Consistently anchored but incorrectly sealed records isolate AES-GCM AAD
    # checks from Merkle checks. These are implementation-fault fixtures, not a
    # claim that an attacker can change the trusted root.
    for field in ('domain','logical_bucket','logical_slot','physical','epoch','generation'):
        a,w=fresh();g=a.g;p=0;b=0;j=0;e=0;v=0;domain=a.domain
        if field=='domain':domain=bytes([domain[0]^1])+domain[1:]
        elif field=='logical_bucket':b=1
        elif field=='logical_slot':j=1
        elif field=='physical':p=1
        elif field=='epoch':e=1
        else:v=1
        aad=b'DeadQ-data-v1\x00'+domain+struct.pack('>IIIQQ',b,j,p,e,v)
        nonce=(a.next_nonce).to_bytes(12,'big');a.next_nonce+=1
        raw=nonce+AESGCM(a.key).encrypt(nonce,bytes(9+g.payload_bytes),aad)
        w.server.committed.update(g.data_row(0),raw);a.rows.root=w.server.committed.root
        rejection('AEAD context mismatch: '+field,a,w,lambda:a.apply('consume',0,0),InvalidTag)
    a,w=fresh();a.prepare('rebuild',0,False);burned=a.next_nonce
    w.reply_filter=lambda req,rep:rep+b'\x00' if req[:1]==b'C' else rep
    rejection('abort burns allocated nonces; no rollback/retry',a,w,a.commit)
    assert a.next_nonce==burned
    return results


def public_shape_check():
    """Fixed public actions, two private payload/placement fixtures; not proof."""
    g=Layout(4,3,2,3,8);model=Allocator(Geometry(4,3,2,3,8));rng=random.Random(3401)
    pairs=[provision(g,{b:[(100*i+b,payload(100*i+b,64))] for b in range(4)} if i else {},
        key=hashlib.sha256(f'shape key {i}'.encode()).digest(),placement=random.Random(4500+i)) for i in (0,1)]
    ops=[]
    for turn in range(120):
        b=rng.randrange(4)
        slots=[j for j,v in enumerate(model.valid[b]) if v]
        if turn%5==0:op=('rebuild',reverse(model.scheduled%4,2),True)
        elif turn%3==0:op=('rebuild_consume',b,0,False)
        elif slots:op=('consume',b,slots[rng.randrange(len(slots))])
        else:op=('gather',b)
        model.apply(*op);model.events=[];ops.append(op)
        for a,w in pairs:a.apply(*op)
    def shape(w):
        return [(req[:1].decode(),len(req),len(rep),struct.unpack('>I',req[13:17])[0] if req[:1] in (b'G',b'U') else None) for req,rep in w.frames]
    assert shape(pairs[0][1])==shape(pairs[1][1])
    return dict(public_operations=120,equal_address_length_shapes=True,frames=len(pairs[0][1].frames),
        inputs='all dummy versus one real per bucket, different test keys and private shuffles',
        security_proof=False,trace_sha256=digest(ops))


def main():
    witness_result=witness();trials=[random_trial(seed) for seed in range(901,906)];negative=attacks();shape=public_shape_check()
    out=dict(status='passed',witness=witness_result,trials=trials,negative_checks=negative,
        public_shape_check=shape,
        encrypted_allocator=True,external_authenticated_directory=True,native_AB=False,CB_integration=False,
        security_proof=False,bandwidth_improvement_claim=False,actual_peak_memory_measured=False,
        provisioning_excluded_from_transaction_bills=True,serialized_microbenchmark_only=True,
        runtime_hashes={n:sha(Path(__file__).parent/n) for n in ('ab_deadq_authenticated_store.py','ab_deadq_routed_allocator.py')},
        oracle_sha256=sha(Path(__file__).parent/'ab_deadq_allocator_model.py'),checker_sha256=sha(__file__))
    save(PACKAGE/'results/ab_deadq_routed_checks.json',out)
    print(json.dumps(dict(status='passed',encrypted_transitions=sum(t['transitions'] for t in trials),negative_checks=len(negative),
        expansions=sum(t['expansions'] for t in trials),collateral_rebuilds=sum(t['collateral_rebuilds'] for t in trials),
        witness_bill=witness_result['total_bill'],native_AB=False,bandwidth_improvement_claim=False)))


if __name__=='__main__':main()
