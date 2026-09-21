"""Encrypted tree checks; whole-state decoding is external test instrumentation."""
from common import *
from collections import Counter
import gzip,random,struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ab_deadq_cb_tree import RoutedCBTree,TreeConfig
from ab_deadq_cb_level import CBLayout,provision_cb
from ab_deadq_authenticated_store import AuthenticationFailure
from cb_oram import Record,gc,generation
from audit_ab_deadq_routed_evidence import root_of


def data(a,v,B):return hashlib.shake_256(b'CB-DeadQ-check'+struct.pack('>II',a,v)).digest(B)


def inventory(tree,wires,truth,pos):
    found={};uids=set();counts=Counter()
    def add(r,depth,b,physical=None):
        assert r.address not in found and r.uid not in uids
        assert r.payload==truth[r.address] and r.leaf==pos[r.address]
        if depth is not None:
            assert r.leaf>>(tree.c.L-depth)==b
            if tree.c.selective:assert depth in gc(tree.g,r.leaf,tree.c.L)
        found[r.address]=r;uids.add(r.uid)
    for r in tree.stash.values():add(r,None,None)
    if tree.root is not None:
        assert tree.root.header.gamma==tree.g
        for r in tree.root.records():add(r,0,0)
    for depth,client in tree.levels.items():
        g=client.g;rows=wires[depth].server.committed.rows;active={};header_records={};scheduled=int.from_bytes(rows[0],'big')
        assert scheduled==tree.g and client.cache is None and not client.headers and not client.cover_records
        assert not client.maintenance_inputs and client.pending is None and client.prepared_result is None
        assert client.rows.root==wires[depth].server.committed.root
        for b in range(g.buckets):
            routing=rows[1+b];epoch,n=struct.unpack('>QI',routing[:12]);assert n in (g.base,g.base+g.extra)
            cells=[struct.unpack('>IB',routing[12+5*j:17+5*j]) for j in range(n)]
            assert all(0<=p<g.physical and v in (0,1) for p,v in cells)
            count=sum(not v for p,v in cells);assert count<=n-g.Z+g.Y
            raw=rows[g.original_count+b]
            aad=b'DeadQ-CB-header-v1\x00'+client.domain+struct.pack('>I',b)+routing
            plain=AESGCM(client.key).decrypt(raw[:12],raw[12:],aad)
            gamma=int.from_bytes(plain[:16],'big');green,m=struct.unpack('>II',plain[16:24])
            assert gamma==generation(scheduled,depth,b) and 0<=green<=min(g.Y,count) and m<=g.Z
            assert plain[24+30*m:]==bytes(len(plain)-24-30*m)
            desc={}
            for k in range(m):
                x=plain[24+30*k:54+30*k];uid=int.from_bytes(x[:16],'big');a=int.from_bytes(x[16:24],'big')
                leaf=int.from_bytes(x[24:28],'big');j=int.from_bytes(x[28:30],'big')
                assert j<n and cells[j][1] and j not in desc;desc[j]=(uid,a,leaf)
            for j,(p,valid) in enumerate(cells):
                if not valid:continue
                assert p not in active;active[p]=(b,j)
                owner=struct.unpack('>IIQ',rows[1+g.buckets+p]);assert owner[:2]==(b,j)
                raw=rows[g.queue_row+1+p]
                plain=AESGCM(client.key).decrypt(raw[:12],raw[12:],
                    b'DeadQ-data-v1\x00'+client.domain+struct.pack('>IIIQQ',b,j,p,epoch,owner[2]))
                assert len(plain)==9+g.payload_bytes
                if plain[0]==0:assert j not in desc and plain==bytes(len(plain));continue
                assert plain[0]==1 and j in desc
                uid=(int.from_bytes(plain[9:17],'big')<<64)|int.from_bytes(plain[1:9],'big')
                a=int.from_bytes(plain[17:25],'big');leaf=int.from_bytes(plain[25:29],'big');payload=plain[29:]
                assert (uid,a,leaf)==desc[j];add(Record(uid,a,leaf,payload),depth,b,p)
                counts['remote_real_observations']+=p//g.base!=b
        owners={}
        for p in range(g.physical):
            b,j,v=struct.unpack('>IIQ',rows[1+g.buckets+p]);owner=None if b==2**32-1 else (b,j)
            assert owner==active.get(p);owners[p]=(owner,v)
        q=rows[g.queue_row];nq=int.from_bytes(q[:4],'big');assert nq<=g.queue_cap
        queue=[struct.unpack('>IQ',q[4+12*j:16+12*j]) for j in range(nq)]
        assert len({p for p,v in queue})==nq
        assert all(owners[p]==(None,v) for p,v in queue)
        for b in range(g.buckets):
            group={b}
            while True:
                before=len(group)
                for p,(owner,v) in owners.items():
                    if owner is not None and (p//g.base in group or owner[0] in group):group.update((p//g.base,owner[0]))
                if len(group)==before:break
            assert len(group)<=g.component_cap
    assert set(found)==set(truth)
    return counts


def wire_audit(frames,g,first_tx=1):
    count=2+g.buckets+2*g.physical+g.buckets;depth=(count-1).bit_length();qindex=1+g.buckets+g.physical
    original=count-g.buckets;root=None;tx=None;step=0;last=first_tx-1;total=Counter();nonces=set()
    for request,response in frames:
        total['rpc']+=1;total['request_bytes']+=len(request);total['response_bytes']+=len(response);op=request[:1]
        if op==b'B':
            assert tx is None and len(request)==len(response)==41 and response==b'b'+request[1:]
            tx=struct.unpack('>Q',request[1:9])[0];assert tx==last+1;last=tx;step=0
            if root is not None:assert request[9:]==root
            root=request[9:];total['control_bytes']+=82;continue
        assert struct.unpack('>QI',request[1:13])==(tx,step)
        if op==b'C':
            assert len(request)==len(response)==45 and request[13:]==root and response==b'c'+request[1:]
            tx=None;total['commits']+=1;total['control_bytes']+=90;continue
        assert op in (b'G',b'U') and response[:17]==op.lower()+request[1:17]
        i=struct.unpack('>I',request[13:17])[0];assert 0<=i<count
        if i>=original:length=((24+30*g.Z+31)//32)*32+28;category='private_header_bytes'
        elif i>qindex:length=g.payload_bytes+37;category='data_record_bytes'
        else:
            length=8 if i==0 else 12+5*(g.base+g.extra) if i<=g.buckets else 16 if i<qindex else 4+12*g.queue_cap
            category='routing_metadata_bytes'
        assert struct.unpack('>I',response[17:21])[0]==length
        start=21+length;assert len(response)==start+32*depth+(32 if op==b'U' else 0)
        proof=[response[start+32*j:start+32*(j+1)] for j in range(depth)]
        assert root_of(i,response[21:start],proof)==root
        total[category]+=length;total['proof_bytes']+=32*depth;total['control_bytes']+=38
        if op==b'G':assert len(request)==17;total['reads']+=1
        else:
            assert len(request)==21+length and struct.unpack('>I',request[17:21])[0]==length
            root=root_of(i,request[21:],proof);assert root==response[-32:]
            total[category]+=length;total['control_bytes']+=36;total['updates']+=1
            if i>qindex:
                nonce=request[21:33];assert nonce not in nonces;nonces.add(nonce)
        step+=1
    assert tx is None;total['total_bytes']=total['request_bytes']+total['response_bytes']
    assert total['total_bytes']==sum(total[k] for k in ('private_header_bytes','data_record_bytes','routing_metadata_bytes','proof_bytes','control_bytes'))
    return dict(total)


def persist(name,frames):
    raw=b''.join((json.dumps(dict(request=q.hex(),response=r.hex()),separators=(',',':'))+'\n').encode() for q,r in frames)
    path=PACKAGE/'results/ab_deadq_cb_wire'/f'{name}.jsonl.gz';path.parent.mkdir(exist_ok=True)
    path.write_bytes(gzip.compress(raw,mtime=0))
    return dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path),raw_sha256=hashlib.sha256(raw).hexdigest(),frames=len(frames))


def trial(kind,S,Y,seed,requests=96):
    c=TreeConfig(kind,3,8,B=64,Z=4,A=3,S=S,Y=Y,extra=1,component_cap=3,queue_cap=8,R=64)
    tree=RoutedCBTree(c,seed=seed);wires=tree.take_transports();rng=random.Random(seed+2000);truth={};pos={};extra=Counter()
    for a in range(c.N):
        pos[a]=rng.randrange(1<<c.L);truth[a]=data(a,0,c.B)
        tree.transfer(None,rng.randrange(1<<c.L),admit=(a,pos[a],truth[a]));extra.update(inventory(tree,wires,truth,pos))
    setup_ends={d:len(w.frames) for d,w in wires.items()};answer=hashlib.sha256()
    for i in range(requests):
        a=rng.randrange(c.N);newleaf=rng.randrange(1<<c.L);prior=truth[a]
        new=data(a,i+1,c.B) if i%2 else prior
        value=tree.transfer(a,pos[a],replace=(newleaf,lambda old:new));assert value==prior
        truth[a]=new;pos[a]=newleaf;answer.update(value);extra.update(inventory(tree,wires,truth,pos))
    raw=[];aggregate=Counter();setup_total=Counter();measurement_total=Counter()
    for d,w in wires.items():
        g=tree.levels[d].g;b=wire_audit(w.frames,g);aggregate.update(b)
        setup=wire_audit(w.frames[:setup_ends[d]],g);setup_total.update(setup)
        first=struct.unpack('>Q',w.frames[setup_ends[d]][0][1:9])[0]
        measured=wire_audit(w.frames[setup_ends[d]:],g,first);measurement_total.update(measured)
        assert b['total_bytes']==setup['total_bytes']+measured['total_bytes']
        raw.append(dict(depth=d,geometry=g.__dict__,wire=persist(f'{kind}_S{S}_Y{Y}_seed{seed}_d{d}',w.frames),bill=b,
            setup_frames=setup_ends[d],setup_bill=setup,measurement_bill=measured,
            server_row_bytes=sum(len(x) for x in w.server.committed.rows[:g.count]),merkle_bytes=(2*w.server.committed.size-1)*32))
    return dict(config=c.__dict__,seed=seed,requests=requests,completed_boundaries=tree.t,answer_sha256=answer.hexdigest(),
        metrics=dict(tree.metrics),inventory=dict(extra),max_stash=tree.max_stash,wire=raw,total_bill=dict(aggregate),
        setup_bill=dict(setup_total),measurement_bill=dict(measurement_total),bytes_per_request=measurement_total['total_bytes']/requests,
        setup_provisioning_excluded=True,formal_performance_sample=False)


def high_uid_check():
    g=CBLayout(2,4,1,2,4,84,Z=3,Y=2,address_bound=8,leaf_bits=1,depth=1)
    records={0:[Record(2**80+1,0,0,b'a'*64),Record(2**81+1,1,0,b'b'*64)]}
    level,wire=provision_cb(g,records,key=b'U'*32,placement=random.Random(12))
    level.apply_cb('scheduled',0)
    event,out=level.apply_cb('logical',0,address=0);assert out['target']==records[0][0]
    event,out=level.apply_cb('logical',0,address=1);assert out['target']==records[0][1]
    return dict(shared_low64_uid=True,full128_uid_preserved=True)


def attacks():
    outcomes=[]
    def fixture():
        tree=RoutedCBTree(TreeConfig('r0',2,4,R=64),seed=33);wires=tree.take_transports()
        for a in range(4):tree.transfer(None,0,admit=(a,a,data(a,0,64)))
        return tree,wires
    for name,op,which in [('header opening proof',b'G','header'),('slot opening proof',b'G','data'),
                           ('write updated root',b'U','any'),('final ACK',b'C','any')]:
        tree,wires=fixture();hit=[]
        for d,wire in wires.items():
            g=tree.levels[d].g
            def mutate(req,rep,g=g):
                if hit or req[:1]!=op:return rep
                if op!=b'C':
                    i=int.from_bytes(req[13:17],'big')
                    if which=='header' and i<g.original_count:return rep
                    if which=='data' and not g.queue_row<i<g.original_count:return rep
                hit.append(True);return rep[:-1]+bytes([rep[-1]^1])
            wire.reply_filter=mutate
        before_t=tree.t
        try:tree.transfer(0,0,replace=(1,lambda old:old))
        except AuthenticationFailure:pass
        else:raise AssertionError('accepted '+name)
        assert hit and tree.dead and tree.t==before_t and all(x.dead for x in tree.levels.values())
        count=sum(len(w.frames) for w in wires.values())
        try:tree.transfer(None,0)
        except AuthenticationFailure:pass
        else:raise AssertionError('continued '+name)
        assert sum(len(w.frames) for w in wires.values())==count;outcomes.append(name)
    return outcomes


def main():
    paths=('ab_deadq_cb_level.py','ab_deadq_cb_tree.py','ab_deadq_authenticated_store.py','ab_deadq_routed_allocator.py','ab_dummy_first_policy.py','cb_oram.py')
    hashes={n:sha(Path(__file__).parent/n) for n in paths};rows=[]
    for S,Y in ((3,3),(4,2)):
        for seed in (701,702):
            for kind in ('ring','gc_ring','r0'):
                r=trial(kind,S,Y,seed);rows.append(r)
                print(json.dumps(dict(kind=kind,S=S,Y=Y,seed=seed,expansions=r['metrics'].get('expansions',0),
                    collateral=r['metrics'].get('collateral_buckets',0),green=r['metrics'].get('green_promotions',0),bytes_per_request=r['bytes_per_request'])),flush=True)
    assert sum(r['metrics'].get('expansions',0) for r in rows)>0
    assert sum(r['metrics'].get('collateral_buckets',0) for r in rows)>0
    assert sum(r['metrics'].get('green_promotions',0) for r in rows)>0
    assert sum(r['inventory'].get('remote_real_observations',0) for r in rows)>0
    high=high_uid_check();bad=attacks()
    assert hashes=={n:sha(Path(__file__).parent/n) for n in paths}
    save(PACKAGE/'results/ab_deadq_cb_tree_checks.json',dict(status='passed',runtime_hashes=hashes,checker_sha256=sha(__file__),
        root_auditor_sha256=sha(Path(__file__).parent/'audit_ab_deadq_routed_evidence.py'),cases=rows,uid_check=high,active_rejections=bad,
        real_CB_DeadQ_tree_execution=True,recursive_frontend=False,native_AB=False,security_admission=False,
        formal_bandwidth_comparison=False,true_peak_measured=False,latency_claim=False))
    print(json.dumps(dict(status='passed',cases=len(rows),boundaries=sum(r['completed_boundaries'] for r in rows),active_rejections=len(bad))))


if __name__=='__main__':main()
