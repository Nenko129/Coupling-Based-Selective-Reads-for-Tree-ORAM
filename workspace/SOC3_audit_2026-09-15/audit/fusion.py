"""Real U/F protocol coupling, finite exchangeability and active-prefix tests."""
from pathlib import Path
import sys, json, hashlib, hmac, itertools, copy, random
from collections import Counter,defaultdict
from fractions import Fraction as F
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'research_20260914/optimization_v1/src'
sys.path.insert(0,str(SRC))
import optimized_oram as o

class EventTape(o.PRF):
    """Test-only semantic event coupling. Production code remains unchanged."""
    def __init__(self,key,contexts):super().__init__(key);self.contexts=contexts;self.events=Counter()
    def draw(self,ctx,event):
        label=(self.contexts[ctx],event);k=self.events[label];self.events[label]+=1;self.samples+=1
        return int.from_bytes(hmac.new(self.key,o.encode(b'COUPLED',o.ui(label[0]),event,o.ui(k)),hashlib.sha512).digest(),'big')
    def initial(self,ctx,address,L):
        return int.from_bytes(hmac.new(self.key,o.encode(b'COUPLED_INITIAL',o.ui(self.contexts[ctx]),o.ui(address)),hashlib.sha512).digest(),'big')&((1<<L)-1)

def client(configs,key):
    factory=o.PRF
    try:
        o.PRF=lambda k:EventTape(k,{c.context():c.tree for c in configs})
        return o.RecursiveORAM(configs,key)
    finally:o.PRF=factory

def snapshot(m):
    verifier=o.PRF(m.P.key);out=[]
    for t in m.trees:
        c=t.c;bs=[]
        for b in range(1,1<<(c.L+1)):
            if c.rootless and b==1:continue
            st=m.server.buckets[c.tree,b];pub=st.header[:o.PUBLIC]
            h=o.Header.decode(c,pub,verifier.decrypt(c.context(),t.oid(b),pub,st.header[o.PUBLIC:]))
            records=tuple((j,d.uid,d.address,d.leaf,verifier.decrypt(c.context(),t.oid(b,j),o.ui(h.w),st.slots[j])) for j,d in sorted(h.live.items()))
            bs.append((b,h.gamma,h.w,h.v,h.count,h.used,records))
        out.append((t.t,t.g,t.uid,tuple(sorted(t.stash.items())),tuple(bs)))
    return tuple(out),tuple(m.terminal_pos),m.P.nonces,m.P.samples,dict(m.P.events)

def synthetic(fused,where,Z=7,A=6,S=1):
    # Valid local invariants with two neutral buckets and a nonneutral bucket.
    c=o.Config('r0',3,6,16,Z=Z,A=A,S=S,R=30,fused=fused)
    m=client([c],hashlib.sha512(('fixture'+where).encode()).digest());t=m.trees[0];t.initialize()
    view=t.open_path(0,c.levels,'fixture');changes={}
    for d in c.levels:
        b=o.node(0,d,c.L);address=0 if (where=='neutral' and d==3) or (where=='other_bucket' and d==2) else d
        rec=o.Record(10+d,address,0,o.ui(100+address,c.B))
        h,hd,slots,local,D=t.prepare(b,view.headers[b],[rec],0)
        if d in (1,3):
            unused=[j for j in range(c.n) if j not in h.live][:S]
            h.count=S;h.used=o.bitmap(unused)
            fin=t.prepare(b,h,None);h,hd=fin[:2]
        changes[b]=(h,hd,slots,local,D)
    t.write(view,changes,'fixture');t.uid=100
    if where=='stash':t.stash[0]=o.Record(99,0,0,o.ui(100,16))
    m.terminal_pos[0]=0;m.ready=True;m.committed=m.anchor()
    return m

def directed_cases():
    cases=[]
    for Z,A,S in [(4,3,1),(7,6,1),(7,6,6)]:
        for where in ('neutral','other_bucket','stash','absent'):
            u=synthetic(False,where,Z,A,S);f=synthetic(True,where,Z,A,S)
            assert snapshot(u)==snapshot(f)
            starts=[len(x.io.events) for x in (u,f)];old_nonces=f.P.nonces;old_samples=f.P.samples
            assert u.access(0,o.ui(999,16))==f.access(0,o.ui(999,16))==o.ui(0 if where=='absent' else 100,16)
            assert snapshot(u)==snapshot(f)
            assert f.P.nonces-old_nonces==2*(Z+S+1)+3
            assert f.P.samples-old_samples==2*2+3+1 # one fresh REMAP
            assert not any(e['stage']=='early' for e in f.io.events[starts[1]:])
            for d in (1,3):
                row=next(x for x in snapshot(f)[0][0][-1] if x[0]==o.node(0,d,3))
                assert row[1]==0 and row[4]==1 and row[5].bit_count()==1
            cases.append(dict(Z=Z,A=A,S=S,target=where,full_completed_projection_equal=True,
                              rpc_unfused=len(u.io.events)-starts[0],rpc_fused=len(f.io.events)-starts[1]))
    return cases

def traces():
    result=[]
    for Z,A,S,mixed in [(4,3,1,False),(7,6,1,False),(7,6,6,False),(7,6,1,True)]:
        cs=[o.Config('r0',5,48,64,Z=Z,A=A,S=S,R=64,tree=0),
            o.Config('sde' if mixed else 'r0',3,12,16,Z=4 if mixed else Z,A=3 if mixed else A,S=1,R=20,tree=1)]
        key=hashlib.sha512(repr((Z,A,S,mixed)).encode()).digest()
        u=client([replace(c,fused=False) for c in cs],key);f=client(cs,key);counts=Counter()
        for t in f.trees:
            if not t.c.ring:continue
            original=t.fused_logical
            def watch(v,a,t=t,original=original):
                E={b for b,h in v.headers.items() if h.count==t.c.S}
                counts['neutral_buckets']+=len(E);counts['multiple_neutral_calls']+=len(E)>1
                counts['mixed_opening_calls']+=bool(E) and len(E)<len(v.headers)
                if E:
                    counts['target_neutral']+=any(d.address==a for b in E for d in v.headers[b].live.values())
                    counts['target_other_bucket']+=any(d.address==a for b in v.headers if b not in E for d in v.headers[b].live.values())
                    counts['target_stash']+=a in t.stash
                return original(v,a)
            t.fused_logical=watch
        for m in (u,f):m.initialize(lambda a:o.ui(a+1,64))
        assert snapshot(u)==snapshot(f)
        truth=[o.ui(a+1,64) for a in range(48)];rng=random.Random(731)
        for i in range(180):
            a=0 if i%9<3 else (i*17)%48 if i%9<6 else rng.randrange(48)
            value=o.ui(1000+i,64) if i%4==0 else None
            assert u.access(a,value)==f.access(a,value)==truth[a]
            if value is not None:truth[a]=value
            assert snapshot(u)==snapshot(f),('completed projection mismatch',Z,S,mixed,i)
            assert u.committed==u.anchor() and f.committed==f.anchor()
        assert counts['neutral_buckets'] and counts['mixed_opening_calls']
        result.append(dict(Z=Z,A=A,S=S,mixed=mixed,online_top_operations=180,completed_snapshots=181,coverage=dict(counts)))
    return result

def finite_distribution():
    checks=0;configurations=0
    # Uniform injections retain record identities. This also checks the
    # conditional distribution of the remaining permutation after j is public.
    for n in range(2,8):
        for r in range(min(4,n-1)+1):
            placements=list(itertools.permutations(range(n),r))
            for hit in (False,True):
                if hit and r==0:continue
                joint=defaultdict(F)
                for pos in placements:
                    choices=[pos[0]] if hit else [j for j in range(n) if j not in pos]
                    for j in choices:joint[j,pos[1:] if hit else pos]+=F(1,len(placements)*len(choices))
                remain=r-1 if hit else r;den=math_perm(n-1,remain)
                for j in range(n):
                    assert sum(v for (x,_),v in joint.items() if x==j)==F(1,n);checks+=1
                    for pos in itertools.permutations([x for x in range(n) if x!=j],remain):
                        assert joint[j,pos]==F(1,n*den);checks+=1
                configurations+=1
    return dict(n_max=7,identity_preserving_configurations=configurations,exact_equalities=checks)

def math_perm(n,k):
    ans=1
    for i in range(k):ans*=n-i
    return ans

def active_prefixes():
    cases=[]
    for case in ('header','first_slot','last_slot','dummy_slot','last_proof','truncate','surplus','wrong_sequence','write_ack','bad_transform'):
        m=synthetic(True,'stash',7,6,1);c=m.configs[0];anchor=m.committed;fired=[]
        def mutate(c,op,seq,stage,meta,request,response):
            if stage!='logical' or fired:return response
            wanted=o.OPEN_HEAD if case=='header' else o.WRITE if case=='write_ack' else o.READ_SLOTS
            if op!=wanted or case=='bad_transform':return response
            rop,tr,sq,flags,body=o.parse_frame(response);body=bytearray(body);before=m.P.decryptions
            if case=='header':body[o.PUBLIC+o.NONCE]^=1
            elif case=='write_ack':body+=b'bad'
            elif case=='truncate':body=body[:-1]
            elif case=='surplus':body+=b'bad'
            elif case=='wrong_sequence':sq+=1
            elif case=='last_proof':body[-1]^=1
            else:
                locations=[];offset=0
                for d,slots in zip(meta['depths'],meta['slots']):
                    b=o.node(meta['leaf'],d,c.L);st=m.server.buckets[c.tree,b];p=o.PRF(m.P.key)
                    pub=st.header[:o.PUBLIC];hd=o.Header.decode(c,pub,p.decrypt(c.context(),m.trees[0].oid(b),pub,st.header[o.PUBLIC:]))
                    for i,j in enumerate(slots):locations.append((offset+i*c.W+o.NONCE,j not in hd.live))
                    offset+=len(slots)*c.W+len(o.witnesses(c.n,tuple(slots)))*o.TAG
                at=locations[0][0] if case=='first_slot' else locations[-1][0] if case=='last_slot' else next(i for i,dummy in locations if dummy)
                body[at]^=1
            fired.append(before)
            return o.frame(rop,tr,sq,bytes(body),True)
        m.io.mutator=mutate
        try:m.access(0,b'x' if case=='bad_transform' else o.ui(101,16))
        except o.Reject:pass
        else:raise AssertionError('active mutation accepted '+case)
        assert m.dead and m.committed==anchor
        if case not in ('write_ack','bad_transform'):
            assert fired and m.P.decryptions==fired[0],('payload decrypted before all openings verified',case)
        before=len(m.io.events);nonce=m.P.nonces
        try:m.access(0)
        except o.Reject:pass
        else:raise AssertionError('continued after rejection')
        assert len(m.io.events)==before and m.P.nonces==nonce
        cases.append(dict(case=case,rejected=True,committed_anchor_unchanged=True,fail_stop_before_IO=True,
                          rejected_before_any_decryption_of_bad_response=case not in ('write_ack','bad_transform')))
    # Same sequencing obligations with a Z7 recursive map already advanced.
    cs=[o.Config('r0',4,24,64,Z=7,A=6,S=1,R=64,tree=0),o.Config('r0',2,6,16,Z=7,A=6,S=1,R=12,tree=1)]
    m=o.RecursiveORAM(cs,hashlib.sha512(b'Z7-recursive-abort').digest());m.initialize()
    anchor=m.committed;counts=[t.t for t in m.trees];fired=[]
    def parent_bad(c,op,seq,stage,meta,request,response):
        if c.tree==0 and op==o.OPEN_HEAD and stage=='logical':
            body=bytearray(o.parse_frame(response)[4]);body[-1]^=1;fired.append(m.P.decryptions)
            return o.frame(op,c.tree,seq,bytes(body),True)
        return response
    m.io.mutator=parent_bad
    try:m.access(0)
    except o.Reject:pass
    else:raise AssertionError('parent failure accepted')
    assert m.dead and m.committed==anchor and m.trees[1].t==counts[1]+1 and m.trees[0].t==counts[0]
    assert fired and m.P.decryptions==fired[0]
    before=len(m.io.events)
    try:m.access(1)
    except o.Reject:pass
    else:raise AssertionError('continued after recursive failure')
    assert len(m.io.events)==before
    cases.append(dict(case='Z7_parent_after_map_commit',map_working_state_advanced=True,committed_anchor_unchanged=True,fail_stop_before_IO=True))
    # A deliberately tiny stash tests rejection, not a certified performance profile.
    c=o.Config('r0',2,6,16,Z=7,A=6,S=1,R=0)
    m=o.RecursiveORAM([c],hashlib.sha512(b'Z7-overflow').digest());m.trees[0].initialize();m.initializing=True
    m.committed=m.anchor();anchor=m.committed
    try:m.access(0)
    except o.Overflow:pass
    else:raise AssertionError('stash overflow returned success')
    assert m.dead and m.committed==anchor
    before=len(m.io.events)
    try:m.access(0)
    except o.Reject:pass
    else:raise AssertionError('continued after overflow')
    assert len(m.io.events)==before
    cases.append(dict(case='Z7_stash_overflow',committed_anchor_unchanged=True,fail_stop_before_IO=True))
    return cases

def audit(out):
    result=dict(directed_cases=directed_cases(),paired_traces=traces(),finite_exchangeability=finite_distribution(),active_prefixes=active_prefixes(),
                production_protocol_changed=False,comparison='same compact format; exact completed projection under test-only independent semantic event tapes; ciphertext/root bytes intentionally excluded')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=audit(a.out);print('fusion PASS',len(r['directed_cases']),'directed cases; 720 online paired operations;',r['finite_exchangeability']['exact_equalities'],'rational equalities')
