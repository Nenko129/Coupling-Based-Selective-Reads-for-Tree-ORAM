"""Independent public-ownership checks; no ORAM timing/bandwidth claims."""
from common import *
import copy, itertools, random
from collections import deque
from ab_deadq_allocator_model import Allocator,Geometry,Rejected,reverse


def independently_check(a):
    g=a.g;expected=[None]*(g.buckets*g.base)
    adjacency=[set() for _ in range(g.buckets)]
    for b in range(g.buckets):
        for j,p in enumerate(a.maps[b]):
            if not a.valid[b][j]:continue
            assert expected[p] is None;expected[p]=(b,j)
            home=p//g.base;adjacency[b].add(home);adjacency[home].add(b)
    assert expected==a.owner
    for start in range(g.buckets):
        visited={start};todo=[start]
        while todo:
            b=todo.pop()
            for other in adjacency[b]-visited:visited.add(other);todo.append(other)
        assert len(visited)<=g.component_cap and visited==a.component(start)
    assert len(a.queue)<=g.queue_cap and len({p for p,v in a.queue})==len(a.queue)
    assert all(expected[p] is None and a.version[p]==v for p,v in a.queue)
    assert all(len(a.maps[b]) in (g.base,g.base+g.extra) for b in range(g.buckets))


def actions(a):
    for b in range(a.g.buckets):
        for j,valid in enumerate(a.valid[b]):
            if valid:yield ('consume',b,j)
        yield ('rebuild',b,False)
        yield ('gather',b)
    yield ('rebuild',reverse(a.scheduled%a.g.buckets,a.g.buckets.bit_length()-1),True)


def exhaustive(g,depth_limit=24,state_limit=18000):
    initial=Allocator(g);todo=deque([(initial,0)]);seen={initial.normalized()};transitions=0;expanded=0;collateral=0;depth_boundary=0
    while todo:
        a,depth=todo.popleft()
        if depth==depth_limit:depth_boundary+=1;continue
        for operation in actions(a):
            b=copy.deepcopy(a);e=b.apply(*operation);independently_check(b);transitions+=1
            if e['operation']=='rebuild':
                expanded+=e['result']=='expanded';collateral+=e['collateral_buckets']>0
                assert e['staged_public_slot_count']<=len(e['rebuilt'])*g.base
                assert len(e['physical_writes'])<=g.component_cap*g.base+g.extra
            b.events=[];key=b.normalized()
            if key not in seen:
                seen.add(key);todo.append((b,depth+1))
                assert len(seen)<=state_limit,'state bound reached; do not silently trim'
    return dict(geometry=g.__dict__,states=len(seen),transitions=transitions,depth_limit=depth_limit,
        depth_boundary_states=depth_boundary,full_normalized_graph_closed=depth_boundary==0,
        expansion_transitions=expanded,collateral_rebuild_transitions=collateral,
        scope='all enabled abstract actions through stated depth; generations alpha-renamed only after checking queue leases')


def witness():
    a=Allocator(Geometry(buckets=2,base=2,extra=1,component_cap=2,queue_cap=4))
    steps=[a.apply('rebuild',0,True),a.apply('rebuild',1,True)]
    assert all(e['result']=='warmup' for e in steps)
    steps.extend([a.apply('consume',0,0),a.apply('consume',0,1)])
    before=a.digest();q=list(a.queue);e=a.apply('rebuild',1,False);steps.append(e)
    assert e['result']=='expanded' and e['borrowed']==[0] and len(a.owner)==4
    assert a.owner[0]==(1,2) and a.valid[1][2]
    # Put a symbolic real record in the extra slot: overwriting the donor's
    # nominal home 0 would destroy a live borrower. No such write is executed.
    would_clobber=dict(naive_donor_bucket=0,physical=0,current_live_owner=list(a.owner[0]))
    c=a.prepare('rebuild',0,False)
    assert c['event']['rebuilt']==[0,1]
    assert (1,2,0) in [tuple(x) for x in c['event']['staged_logical_slots']]
    assert a.owner[0]==(1,2)  # Prepared state has not published any mutation.
    steps.append(a.commit(c['expected_state_digest']));independently_check(a)
    assert a.owner[0]==(0,0) and len(a.maps[1])==2
    return dict(initial_physical_slots=4,final_physical_slots=len(a.owner),extra_persistent_slots=0,
        expansion_from_dead_queue=q,naive_overwrite_risk=would_clobber,steps=steps,
        preserved_if_caller_stages_real_payloads=True,encrypted_execution=False)


def transaction_rejections():
    a=Allocator(Geometry(buckets=2,base=2,component_cap=2,queue_cap=4))
    old=a.digest();q=copy.deepcopy(a.queue);transaction=a.prepare('consume',0,0)
    assert a.digest()==old and a.queue==q and a.owner[0]==(0,0)
    a.commit(transaction['expected_state_digest']);assert a.queue==[(0,1)]
    out=['dead queue unpublished until verified commit boundary']
    b=Allocator(a.g);b.prepare('consume',0,0);old=b.digest()
    try:b.commit('invalid authenticated acknowledgement')
    except Rejected:pass
    else:raise AssertionError('bad ACK accepted')
    assert b.dead and b.digest()==old
    try:b.prepare('consume',0,1)
    except Rejected:out.append('bad ACK causes permanent stop without publishing lease')
    else:raise AssertionError('fail-stop resumed')
    b=Allocator(a.g);t=b.prepare('consume',0,0);b.commit(t['expected_state_digest'])
    b.prepare('consume',0,1)
    try:b.commit(t['expected_state_digest'])
    except Rejected:out.append('old state acknowledgement rejected after generation change')
    else:raise AssertionError('old ACK replay accepted')
    b=Allocator(a.g);b.apply('rebuild',0,True);b.apply('rebuild',1,True);b.apply('consume',0,0)
    p,v=b.queue[0];b.queue[0]=(p,v-1)
    try:b.prepare('rebuild',1,False)
    except Rejected:out.append('stale FIFO lease generation rejected')
    else:raise AssertionError('stale lease accepted')
    b=Allocator(Geometry(buckets=2,base=2,component_cap=1,queue_cap=4))
    b.apply('rebuild',0,True);b.apply('rebuild',1,True);b.apply('consume',0,0)
    q=list(b.queue);e=b.apply('rebuild',1,False)
    assert e['result']=='component_cap' and b.queue==q
    out.append('component-cap fallback preserves FIFO prefix')
    b=Allocator(Geometry(buckets=2,base=3,extra=2,component_cap=2,queue_cap=4))
    b.apply('rebuild',0,True);b.apply('rebuild',1,True);b.apply('consume',0,0)
    q=list(b.queue);e=b.apply('rebuild',1,False)
    assert e['result']=='empty_or_short_queue' and b.queue==q and len(b.maps[1])==3
    out.append('short queue does not partially grant a two-slot extension')
    b=Allocator(Geometry(buckets=2,base=2,extra=1,component_cap=2,queue_cap=4))
    b.apply('rebuild',0,True);b.apply('rebuild',1,True);b.apply('consume',0,0)
    old=b.digest();q=list(b.queue);tx=b.prepare('rebuild_consume',1,2,False)
    assert b.digest()==old and b.queue==q
    assert tx['event']['rebuild']['borrowed']==[0] and tx['event']['consume']['physical']==0
    expected_lease=(0,q[0][1]+2)  # Grant and virtual consumption each advance it.
    assert b.pending[1].queue==[expected_lease]
    b.commit(tx['expected_state_digest']);assert b.queue==[expected_lease] and b.owner[0] is None
    out.append('fused virtual consumption published only after the final commit')
    old=b.digest();q=list(b.queue);b.prepare('rebuild_consume',1,2,False)
    try:b.commit('wrong fused final ACK')
    except Rejected:pass
    else:raise AssertionError('bad fused ACK accepted')
    assert b.dead and b.digest()==old and b.queue==q
    out.append('failed fused commit never publishes a new reusable generation')
    b=Allocator(Geometry(buckets=2,base=2,extra=1,component_cap=2,queue_cap=2))
    b.apply('consume',0,0);b.apply('consume',0,1);b.apply('consume',1,0)
    assert [p for p,v in b.queue]==[0,1] and b.owner[2] is None
    b.apply('rebuild',0,False);assert b.queue==[]
    e=b.apply('gather',1);assert e['added']==[2] and b.queue==[(2,b.version[2])]
    out.append('gather recovers a dead slot previously skipped by a full FIFO')
    return out


def symbolic_payload_trials():
    """Separate opaque-record oracle checks staged rebuilds preserve real UIDs.

    Payload positions are privately shuffled among all new logical slots, so a
    real record can occupy a borrowed slot. No encryption is claimed here.
    """
    trials=[]
    for seed in range(5):
        rng=random.Random(701+seed);payload_rng=random.Random(1701+seed)
        g=Geometry(buckets=4,base=3,extra=2,component_cap=3,queue_cap=8)
        a=Allocator(g);payload={b*g.base:(b,hashlib.sha256(str(b).encode()).digest()) for b in range(4)}
        removed=set();count=0;expanded=0;collateral=0
        for turn in range(500):
            enabled=list(actions(a));op=enabled[rng.randrange(len(enabled))]
            before_payload=dict(payload)
            tx=a.prepare(*op);e=tx['event']
            if e['operation']=='consume':
                p=e['physical']
                if p in payload:removed.add(payload.pop(p)[0])
            elif e['operation']=='rebuild':
                staged={b:[] for b in e['rebuilt']}
                for b,j,p in e['staged_logical_slots']:
                    if p in payload:staged[b].append(payload[p])
                assert all(len(v)<=g.base for v in staged.values())
                # Clear all physical homes being rewritten only after staging.
                for p in e['physical_writes']:payload.pop(p,None)
                work=a.pending[1]
                for b,items in staged.items():
                    slots=list(work.maps[b]);payload_rng.shuffle(slots)
                    for p,record in zip(slots,items):
                        assert p not in payload;payload[p]=record
                assert {v[0] for v in before_payload.values()}=={v[0] for v in payload.values()}
                expanded+=e['result']=='expanded';collateral+=e['collateral_buckets']>0
            a.commit(tx['expected_state_digest']);independently_check(a);a.events=[];count+=1
            assert len({v[0] for v in payload.values()})==len(payload)
            assert {v[0] for v in payload.values()}|removed==set(range(4))
            assert all(a.owner[p] is not None for p in payload)
            # Refresh one symbolic real record at a rebuild, modeling caller
            # placement without choosing the public schedule from private data.
            if e['operation']=='rebuild':
                for b in e['rebuilt']:
                    if b in removed:
                        free=[p for p in a.maps[b] if p not in payload]
                        if free:payload[payload_rng.choice(free)]=(b,hashlib.sha256(str(b).encode()).digest());removed.remove(b)
        trials.append(dict(seed=701+seed,transitions=count,expansions=expanded,collateral_rebuilds=collateral))
    return trials


def main():
    cases=[Geometry(buckets=2,base=2,extra=1,component_cap=k,queue_cap=2) for k in (1,2)]
    reach=[exhaustive(g) for g in cases]
    w=witness();checks=transaction_rejections();payload=symbolic_payload_trials()
    source=PACKAGE.parent/'细化准备_2026-09-15/literature/pdf/R13_ab_oram_constructing_adjustable_buckets_for_space_reduction.pdf'
    out=dict(status='passed',reachability=reach,zero_extra_space_witness=w,transaction_checks=checks,
        symbolic_payload_trials=payload,source_pdf_sha256=sha(source),
        model_sha256=sha(Path(__file__).parent/'ab_deadq_allocator_model.py'),checker_sha256=sha(__file__),
        native_AB_reproduction=False,encrypted_ORAM_execution=False,security_proof=False,bandwidth_measurement=False,
        source_url="https://mehrnoosh.net/research/AB-ORAM-HPCA%2723.pdf",
        remaining=['authenticated physical-routing and metadata implementation','CB/selective engine integration and payload staging',
            'adaptive transcript simulation and green/stash capacity bound','same-space full-system repeated bandwidth measurements'])
    save(PACKAGE/'results/ab_deadq_allocator_model_checks.json',out)
    print(json.dumps(dict(status='passed',reachability=reach,transaction_checks=len(checks),
        symbolic_payload_transitions=sum(x['transitions'] for x in payload),zero_extra_space_expansion=True,
        encrypted_ORAM_execution=False,bandwidth_measurement=False)))


if __name__=='__main__':main()
