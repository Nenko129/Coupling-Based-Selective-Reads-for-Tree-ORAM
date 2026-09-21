#!/usr/bin/env python3
"""Integrated execution, proof-interface, malicious-server and invoice tests.
Legacy plaintext models are EXTERNAL differential oracles, never used by the
integrated client's path/placement/slot decisions.
"""
from __future__ import annotations
from pathlib import Path
import sys,json,random,hashlib,hmac,copy,itertools,time
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'legacy'))
from core_state_tests import Core,Shadow,Token,pack
from integrated_oram import *
from unified_cost import invoice,mean_local_witnesses,expected_tree,early_interval
from fractions import Fraction
from reduction_checks import recursion as field_recursion
ROOT=Path(__file__).resolve().parents[1]

class Differential:
    """External test observer: maintains no inputs used by the implementation."""
    def __init__(self,configs):
        self.cores=[Core(c.L,c.Z,c.A,c.S,c.kind if c.kind in ('sde','r0') else 'ring',900+i) for i,c in enumerate(configs)]
        self.shadows=[Shadow(c.L,c.Z,c.A,c.rootless) for c in configs]
        self.physical=[{b:() for b in core.slots} for core in self.cores]
        self.accesses=0;self.depth_comparisons=0;self.postprocess_comparisons=0
        self.last_layer_events=[];self.field_comparisons=0
    def observe(self,event,j,a,b):
        if event=='header':
            self.physical[j][a]=tuple(sorted(d.uid for d in b.live.values()));return
        address,oldleaf,newleaf,previous,updated=a;tree=b;ref=self.cores[j]
        got=ref.access(address,int.from_bytes(updated,'big'),newleaf,oldleaf,lookup_leaf=oldleaf)
        assert got==int.from_bytes(previous,'big')
        refview=ref.view();actualview=tuple((v,self.physical[j][v]) for v in sorted(self.physical[j])),tuple(sorted(r.uid for r in tree.stash.values()))
        assert refview==actualview,('projection mismatch',j,address)
        sh=self.shadows[j];sh.access(tree.uid,address,newleaf,int.from_bytes(updated,'big'))
        assert len(tree.stash)<=len(sh.stash)
        actualdepth={r.uid:-1 for r in tree.stash.values()}
        for v,ids in self.physical[j].items():
            for u in ids:assert u not in actualdepth;actualdepth[u]=depth(v)
        shadowdepth={u:-1 for u in sh.stash}
        for v,ids in sh.tree.items():
            for u in ids:shadowdepth[u]=depth(v)
        for u,d in actualdepth.items():
            assert d>=shadowdepth[u],('per-current depth domination failed',j,u,d,shadowdepth[u])
            self.depth_comparisons+=1
        assert (sh.tree,sh.stash)==pack(sh.tokens,sh.g,sh.L,sh.Z,sh.rootless)
        field=[0]*((1<<(sh.L+1))-1);fresh=0
        for tok in sh.tokens.values():
            if tok.home<0:fresh+=1
            else:field[node(tok.leaf,tok.home,sh.L)-1]+=1
        F=sum(field_recursion(field,sh.g,sh.L,sh.Z,sh.rootless))
        assert F+fresh==len(sh.stash) and fresh<=sh.A-1
        if sh.rootless:assert 0<=F-sum(field_recursion(field,sh.g,sh.L,sh.Z,False))<=sh.Z
        self.field_comparisons+=1
        self.postprocess_comparisons+=1;self.accesses+=1
        self.last_layer_events.append((j,address))


def verify_physical_snapshot(m:RecursiveORAM,diff:Differential|None=None):
    """Test-only whole-server audit with a separate verifier/counter object.
    It is never called by the protocol, never supplies path inputs and is not
    included in the online communication/primitive measurement.
    """
    p=PRF(m.P.key);counts=[]
    for j,c in enumerate(m.configs):
        tree=m.trees[j];tags={};physical={};ctx=c.context()
        for b in range((1<<(c.L+1))-1,0,-1):
            st=m.server.buckets[j,b]
            if c.rootless and b==1:bt=p.F(b'EMPTY_ROOT',ctx)
            else:
                if c.ring:
                    lt=local_make(c,p,b,st.slots)
                    assert lt==st.local;D=lt[1]
                else:D=p.F(b'FULL_DATA',ctx,ui(b,8),b''.join(st.slots))
                bt=p.F(b'BUCKET',ctx,ui(b,8),st.header,D)
                pub=st.header[:PUBLIC]
                hd=Header.decode(c,pub,p.decrypt(ctx,b'H'+ui(b,8),pub,st.header[PUBLIC:]))
                physical[b]=tuple(sorted(d.uid for d in hd.live.values()))
            assert hmac.compare_digest(bt,st.bucket_tag)
            gt=p.F(b'GLOBAL_NODE',ctx,ui(b,8),bt,tags.get(2*b,ZERO),tags.get(2*b+1,ZERO))
            assert gt==m.server.global_tags[j,b];tags[b]=gt
        assert tags[1]==tree.root
        if diff:assert physical==diff.physical[j]
        counts.append(len(tags))
    return counts


def integrated_runs():
    runs=[];total=Counter();ledger_samples=[]
    for kind in ('sde','r0'):
        for seed in range(3):
            cs=[Config(kind,5,48,B=256,tree=0,R=64),Config(kind,3,12,B=16,tree=1,R=32)]
            m=RecursiveORAM(cs,hashlib.sha512(f'{kind}:{seed}'.encode()).digest());d=Differential(cs)
            for tree in m.trees:tree.observer=d.observe
            m.initialize(lambda a:ui(a+100,256));truth=[ui(a+100,256) for a in range(48)]
            setup_counts=[t.t for t in m.trees];assert setup_counts==[48,60]
            start=len(m.io.events);startprf=m.P.calls;nonce_start=m.P.nonces;before=time.perf_counter()
            r=random.Random(seed)
            for i in range(400):
                a=0 if i%11<3 else i%48 if i%11<7 else r.randrange(48)
                val=ui(r.randrange(1<<64),256) if i%3==0 else None
                counts=[t.t for t in m.trees];k=len(d.last_layer_events);got=m.access(a,val)
                assert got==truth[a]
                if val is not None:truth[a]=val
                assert [t.t-counts[j] for j,t in enumerate(m.trees)]==[1,1]
                assert [j for j,a in d.last_layer_events[k:]]==[1,0]
                assert m.committed==m.anchor()
            elapsed=time.perf_counter()-before;online=m.io.events[start:]
            bill=invoice(cs,online);whole=invoice(cs,m.io.events)
            assert whole['total']==dict(Counter(m.io.total)) or all(whole['total'][k]==m.io.total[k] for k in whole['total'])
            snapshot=verify_physical_snapshot(m,d)
            total.update(dict(top_requests=400,layer_accesses=d.accesses,per_token_depth_comparisons=d.depth_comparisons,
                              canonical_comparisons=d.postprocess_comparisons,field_recurrence_comparisons=d.field_comparisons,frames_checked=whole['events_checked'],whole_snapshot_nodes=sum(snapshot)))
            runs.append(dict(kind=kind,seed=seed,requests=400,setup_layer_accesses=setup_counts,
                online_layer_accesses=[t.t-setup_counts[j] for j,t in enumerate(m.trees)],invoice=bill,
                primitive_calls_online=m.P.calls-startprf,nonce_allocations_online=m.P.nonces-nonce_start,
                max_stash=[t.max_stash for t in m.trees],elapsed_including_test_oracle_seconds=elapsed,
                timer_warning='Not a performance benchmark: includes external shadow and assertion work.'))
            if seed==0:ledger_samples+=online[:200]
    # Main payload and terminal map dimensions, at a smaller number of records.
    for kind in ('sde','r0'):
        cs=[Config(kind,7,192,B=4096,tree=0),Config(kind,1,1,B=4096,tree=1,R=4)]
        m=RecursiveORAM(cs,hashlib.sha512((kind+'4k').encode()).digest());m.initialize(lambda a:ui(a,4096))
        start=len(m.io.events)
        for i in range(150):assert m.access(i%192)==ui(i%192,4096)
        bill=invoice(cs,m.io.events[start:]);invoice(cs,m.io.events);verify_physical_snapshot(m)
        runs.append(dict(kind=kind,payload_4096=True,requests=150,invoice=bill,terminal_position_bytes=4))
        total['top_requests']+=150;total['frames_checked']+=len(m.io.events)
    (ROOT/'results/integrated_ledger_sample.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in ledger_samples))
    return {'totals':dict(total),'runs':runs}


def mutation_runs():
    results=[]
    cases=[('header_flip',OPEN_HEAD),('proof_flip',OPEN_HEAD),('slot_flip',READ_SLOTS),('header_truncate',OPEN_HEAD),('replay',OPEN_HEAD),('parent_after_map_commit',OPEN_HEAD),('write_ack',WRITE),('blind_cover_flip',READ_SLOTS)]
    for kind in ('sde','r0'):
        for case,op0 in cases:
            cs=[Config(kind,4,24,B=64,tree=0,R=64),Config(kind,2,6,B=16,tree=1,R=32)]
            m=RecursiveORAM(cs,hashlib.sha512((kind+case).encode()).digest());m.initialize(lambda a:ui(a,64))
            oldanchor=m.committed;oldcounts=[t.t for t in m.trees];fired=[];prevresp=[]
            wanted=op0 if kind=='r0' else (OPEN_FULL if op0 in (OPEN_HEAD,READ_SLOTS) else op0)
            targettree=0 if case=='parent_after_map_commit' else 1
            def change(c,op,seq,stage,meta,request,response):
                if c.tree!=targettree or op!=wanted or stage not in ('logical','evict'):return response
                if fired:return response
                before=m.P.decryptions
                rop,tr,sq,fl,body=parse_frame(response);body=bytearray(body)
                if case=='header_truncate':body=body[:-1]
                elif case=='write_ack':body+=b'bad'
                elif case=='replay':
                    # Replaying a response frame from a different request sequence
                    # must be rejected even before authentication.
                    response=frame(rop,tr,max(0,sq-1),bytes(body),True);fired.append((before,stage));return response
                else:
                    if case=='header_flip':index=PUBLIC+NONCE
                    elif case in ('slot_flip','explicit_dummy') and kind=='r0':index=NONCE
                    elif case=='explicit_dummy':
                        # Nonexistent target is NOT needed: find an authenticated
                        # selected bucket with a dummy physical slot externally.
                        index=c.H+NONCE
                    else:index=len(body)-1
                    body[index]^=1
                fired.append((before,stage));return frame(rop,tr,sq,bytes(body),True)
            m.io.mutator=change
            try:m.access(7,ui(999,64))
            except Reject:pass
            else:raise AssertionError(('attack accepted',kind,case))
            assert fired and m.dead and m.committed==oldanchor
            if wanted!=WRITE:assert m.P.decryptions==fired[0][0],(kind,case,'decrypted bad opening')
            if case=='parent_after_map_commit':assert m.trees[1].t==oldcounts[1]+1 and m.trees[0].t==oldcounts[0]
            before=len(m.io.events)
            try:m.access(0)
            except Reject:pass
            else:raise AssertionError('continued after failed transaction')
            assert len(m.io.events)==before
            results.append(dict(kind=kind,case=case,unchanged_committed_anchor=True,fail_stop=True,
                                corrupt_opening_rejected_before_decryption=wanted!=WRITE))
    # Header-only replay with correct outer response id: stash-hit requests keep
    # the same mapped leaf because the test pins newleaf in this direct Tree API.
    for kind in ('sde','r0'):
        c=Config(kind,3,1,B=32,R=20);P=PRF(hashlib.sha512(kind.encode()).digest());io=Transport(Server([c]));t=Tree(c,P,io);t.initialize()
        saved=[]
        def save(c,op,seq,stage,meta,request,response):
            if op in (OPEN_FULL,OPEN_HEAD) and stage=='logical' and not saved:saved.append(parse_frame(response)[4])
            return response
        io.mutator=save;t.access(0,0,0,lambda p:ui(1,32));io.mutator=None
        def replay(c,op,seq,stage,meta,request,response):
            if op in (OPEN_FULL,OPEN_HEAD) and stage=='logical':return frame(op,c.tree,seq,saved[0],True)
            return response
        io.mutator=replay;before=P.decryptions
        try:t.access(0,0,0,lambda p:p)
        except Reject:pass
        else:raise AssertionError('stale authenticated snapshot accepted')
        assert P.decryptions==before
        results.append(dict(kind=kind,case='current_root_vs_replayed_header_body',rejected_before_decryption=True))
    for kind in ('sde','r0'):
        c=Config(kind,3,1,B=32,R=20);P=PRF(hashlib.sha512(('dummy'+kind).encode()).digest());io=Transport(Server([c]));t=Tree(c,P,io);t.initialize()
        t.access(0,0,0,lambda p:ui(11,32));assert 0 in t.stash and t.t==1 and t.g==0
        fired=[]
        def corrupt_dummy(c,op,seq,stage,meta,request,response):
            wanted=READ_SLOTS if c.ring else OPEN_FULL
            if stage!='logical' or op!=wanted or fired:return response
            rop,tr,sq,fl,body=parse_frame(response);body=bytearray(body)
            at=NONCE if c.ring else c.H+NONCE
            body[at]^=1;fired.append(P.decryptions)
            return frame(op,c.tree,seq,bytes(body),True)
        io.mutator=corrupt_dummy
        try:t.access(0,0,0,lambda p:p)
        except Reject:pass
        else:raise AssertionError('corrupted guaranteed dummy accepted')
        assert fired and P.decryptions==fired[0]
        results.append(dict(kind=kind,case='guaranteed_dummy_stash_hit',no_eviction_yet=True,rejected_before_payload_decryption=True))
    return {'cases':results,'count':len(results)}


def slot_exchangeability():
    checks=0
    # Enumerate unread-slot layouts, semantic real sets and dummy padding.
    # Every fixed Z-subset must have probability 1/C(n,Z), regardless of r.
    for n in range(4,10):
        Z=4
        for r in range(Z+1):
            weights={s:Fraction(0) for s in itertools.combinations(range(n),Z)}
            for real in itertools.combinations(range(n),r):
                dummy=[j for j in range(n) if j not in real]
                for extra in itertools.combinations(dummy,Z-r):
                    s=tuple(sorted(real+extra));weights[s]+=Fraction(1,math.comb(n,r)*math.comb(n-r,Z-r))
            assert set(weights.values())=={Fraction(1,math.comb(n,Z))};checks+=len(weights)
    return {'exact_subset_probabilities_checked':checks,'request_order':'ascending physical slots, encoded by bitmap'}


def slot_proofs_and_sampler():
    checks=0
    for n in range(5,10):
        c=Config('r0',2,2,B=16,Z=4,S=n-4,R=10)
        P=PRF(bytes(range(64)));slots=[P.seal(c.context(),b'TEST'+ui(j),b'',bytes([j])*16) for j in range(n)]
        tags=local_make(c,P,3,slots)
        for k in range(1,n+1):
            for inds in itertools.combinations(range(n),k):
                proof={p:tags[p] for p in witnesses(n,inds)}
                assert local_open_root(c,P,3,{j:slots[j] for j in inds},proof)==tags[1];checks+=1
        for k in range(n+1):
            expected=list(itertools.combinations(range(n),k))
            assert [choose_rank(list(range(n)),k,r) for r in range(len(expected))]==expected
    return {'local_openings_checked':checks,'all_combination_ranks_checked':True}


def exact_binomial_intervals():
    cases=0
    for n in range(1,25):
        for p in [Fraction(1,2),Fraction(1,4),Fraction(1,8)]:
            if n*p>3:continue
            for S in (1,2,3,5):
                exact=sum((Fraction(math.comb(n,k))*p**k*(1-p)**(n-k)*max(0,(k-1)//S) for k in range(n+1)),Fraction())
                got=early_interval(n,p,S)
                assert Fraction(got.lo)<=exact<=Fraction(got.hi);cases+=1
    return {'exact_binomial_interval_cases':cases}


def baseline_ledgers():
    rows=[]
    for kind in ('path','deferred','sde','ring','gc_ring','r0'):
        cs=[Config(kind,5,48,B=256,tree=0,R=64),Config(kind,3,12,B=16,tree=1,R=32)]
        m=RecursiveORAM(cs,hashlib.sha512(('unified:'+kind).encode()).digest());m.initialize(lambda a:ui(a,256))
        truth=[ui(a,256) for a in range(48)];start=len(m.io.events)
        for i in range(1000):
            a=(i*17+(i//31))%48;v=ui(1000+i,256) if i%5==0 else None
            assert m.access(a,v)==truth[a]
            if v is not None:truth[a]=v
        bill=invoice(cs,m.io.events[start:]);verify_physical_snapshot(m)
        rows.append(dict(kind=kind,requests=1000,invoice=bill,average_framed_bytes=bill['total_bytes']/1000,
                         comparison='Same public geometry/serializer; no claim of equal certified Path-Z4 failure or optimized cache/XOR baseline.'))
    return {'rows':rows,'same_frame_serializer':True,'wall_clock_benchmark':False}


def main():
    start=time.perf_counter()
    sections={'integrated':integrated_runs,'active_attacks':mutation_runs,
         'slot_exchangeability':slot_exchangeability,'local_proofs':slot_proofs_and_sampler,
         'cost_intervals':exact_binomial_intervals,'unified_measured_ledgers':baseline_ledgers}
    selected=sys.argv[1:] or list(sections)
    for key in selected:
        result=sections[key]();(ROOT/f'results/{key}.json').write_text(json.dumps(result,indent=2));print(key,'PASS',flush=True)
    if not all((ROOT/f'results/{key}.json').exists() for key in sections):return
    out={key:json.loads((ROOT/f'results/{key}.json').read_text()) for key in sections}
    out['elapsed_seconds_including_test_oracles']=time.perf_counter()-start
    (ROOT/'results/integrated_chain_tests.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({'integrated':out['integrated']['totals'],'attacks':out['active_attacks']['count'],
          'slots':out['local_proofs'],'cost_intervals':out['cost_intervals'],'baseline_requests':6000,
          'elapsed_seconds':out['elapsed_seconds_including_test_oracles']},indent=2))
if __name__=='__main__':main()
