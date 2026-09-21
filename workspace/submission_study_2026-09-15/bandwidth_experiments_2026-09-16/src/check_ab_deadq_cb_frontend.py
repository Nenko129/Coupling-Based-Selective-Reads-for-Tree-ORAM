"""Actual recursive map/PLB/LLC execution through the CB+DeadQ tree."""
from common import *
from collections import Counter
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import ab_deadq_cb_runtime as rt
from ab_paced_frontend import PacedGeometryStepwiseFront
from ab_cb_controller import PressureController
from ab_deadq_authenticated_store import AuthenticationFailure
from cb_oram import Record
from check_ab_deadq_cb_tree import inventory,wire_audit,persist
from workloads import make_trace,payload
from frontends import initial_payload


def create(kind,S,Y,high=None,low=None):
    rt.install(dict(seed=911,R=128,Y=Y,extra=1,component_cap=3,queue_cap=8))
    f=PacedGeometryStepwiseFront(kind,N=64,B=64,X=8,plb=3,seed=911,profile=(4,3,S))
    channels=f.backend.take_channels()
    return PressureController(f,sets=4,ways=2,high=high,low=low),channels


def decode_records(tree,wires):
    records=dict(tree.stash)
    if tree.root is not None:
        for r in tree.root.records():assert r.address not in records;records[r.address]=r
    for d,c in tree.levels.items():
        g=c.g;rows=wires[d].server.committed.rows
        for b in range(g.buckets):
            routing=rows[1+b];epoch,n=struct.unpack('>QI',routing[:12]);raw=rows[g.original_count+b]
            plain=AESGCM(c.key).decrypt(raw[:12],raw[12:],b'DeadQ-CB-header-v1\x00'+c.domain+struct.pack('>I',b)+routing)
            m=int.from_bytes(plain[20:24],'big')
            for k in range(m):
                x=plain[24+30*k:54+30*k];uid=int.from_bytes(x[:16],'big');a=int.from_bytes(x[16:24],'big')
                leaf=int.from_bytes(x[24:28],'big');j=int.from_bytes(x[28:30],'big')
                p,v=struct.unpack('>IB',routing[12+5*j:17+5*j]);assert v==1
                ob,oj,version=struct.unpack('>IIQ',rows[1+g.buckets+p]);assert (ob,oj)==(b,j)
                raw=rows[g.queue_row+1+p]
                decoded=AESGCM(c.key).decrypt(raw[:12],raw[12:],b'DeadQ-data-v1\x00'+c.domain+struct.pack('>IIIQQ',b,j,p,epoch,version))
                assert a not in records;records[a]=Record(uid,a,leaf,decoded[29:])
    return records


def ownership(controller,wires,truth):
    f=controller.front;tree=f.backend.tree;records=decode_records(tree,wires)
    assert not(set(records)&set(f.cache)) and set(records)|set(f.cache)==set(range(f.total))
    assert len(f.cache)<=f.capacity and not f.memory_payload_bound()['full_private_posmap_present']
    for level,count in enumerate(f.counts):
        for i in range(count):
            a=f.offsets[level]+i;actual=f.cache[a].parked_leaf if a in f.cache else records[a].leaf
            if level==len(f.counts)-1:expected=f.top[i]
            else:
                pi,j=divmod(i,f.X);pa=f.offsets[level+1]+pi
                parent=f.cache[pa].data if pa in f.cache else records[pa].payload
                expected=int.from_bytes(parent[4*j:4*j+4],'big')
            assert actual==expected,(level,i,actual,expected)
    llc={a:x for group in controller.sets for a,x in group.items()}
    for a,value in truth.items():
        if a in llc:
            assert llc[a].payload==value
            if not llc[a].dirty:assert records[a].payload==value
        else:assert records[a].payload==value
    return inventory(tree,wires,{a:r.payload for a,r in records.items()},{a:r.leaf for a,r in records.items()})


def trial(kind,S,Y):
    c,wires=create(kind,S,Y);f=c.front;b=f.backend;truth={a:initial_payload(a,64) for a in range(64)}
    ownership(c,wires,truth);phases=[];seq=make_trace(64,80,919,'uniform');offset=0
    ends={d:len(w.frames) for d,w in wires.items()};answer=hashlib.sha256()
    for phase,part in [('warmup',seq[:16]),('measurement',seq[16:])]:
        requests=[];expected=[];b.tree.logical_calls.reset();cb_before=b.tree.metrics.copy()
        for i,(a,v) in enumerate(part):
            value=None if v is None else payload(a,v,64)
            requests.append(dict(id=offset+i,address=a,value=value));expected.append((offset+i,truth[a]))
            if value is not None:truth[a]=value
        actual,metrics=c.run_window(requests,8,len(part)*16)
        assert [(i,v) for i,v,t in actual]==expected
        for i,v,t in actual:answer.update(v)
        extra=ownership(c,wires,truth);invoice=Counter();by_level=[]
        for d,w in wires.items():
            frames=w.frames[ends[d]:];first=int.from_bytes(frames[0][0][1:9],'big')
            bill=wire_audit(frames,b.tree.levels[d].g,first_tx=first);invoice.update(bill)
            by_level.append(dict(depth=d,bill=bill,start_frame=ends[d],end_frame=len(w.frames)));ends[d]=len(w.frames)
        phases.append(dict(phase=phase,requests=len(part),slots=len(part)*16,total_bill=dict(invoice),by_level=by_level,
            controller_metrics=metrics,cb_metrics=dict(b.tree.metrics-cb_before),schedule=b.tree.logical_calls.snapshot(),inventory=dict(extra)))
        offset+=len(part)
    refs=[]
    for d,w in wires.items():
        g=b.tree.levels[d].g;refs.append(dict(depth=d,geometry=g.__dict__,wire=persist(f'frontend_{kind}_S{S}_Y{Y}_d{d}',w.frames),
            bill=wire_audit(w.frames,g),server_rows=sum(len(x) for x in w.server.committed.rows[:g.count]),merkle_bytes=(2*w.server.committed.size-1)*32))
    return dict(kind=kind,S=S,Y=Y,N=64,B=64,population=f.total,L=f.L,map_counts=f.counts,PLB=f.capacity,LLC_sets=4,LLC_ways=2,
        setup_slots=f.total*3,phases=phases,wire=refs,answer_sha256=answer.hexdigest(),max_stash=b.tree.max_stash,
        frontend_memory=f.memory_payload_bound(),trusted_cache='root only for Ring/GC-Ring; R0 root omitted',
        formal_performance_sample=False,native_AB=False)


def active_check():
    c,wires=create('r0',3,3);hit=[]
    for w in wires.values():
        def mutate(req,rep):
            if not hit and req[:1]==b'C':hit.append(True);return rep[:-1]+bytes([rep[-1]^1])
            return rep
        w.reply_filter=mutate
    try:c.tick([dict(id=1,address=0,value=b'z'*64)])
    except AuthenticationFailure:pass
    else:raise AssertionError('accepted recursive commit corruption')
    assert hit and c.dead and c.front.dead and c.front.backend.tree.dead and not c.returned
    count=sum(len(w.frames) for w in wires.values())
    try:c.tick()
    except RuntimeError:pass
    else:raise AssertionError('resumed recursive controller')
    assert sum(len(w.frames) for w in wires.values())==count
    return dict(commit_error_before_application_result=True,permanent_stop=True)


def main():
    source=rt.identity();rows=[]
    for S,Y in ((3,3),(4,2)):
        for kind in ('ring','gc_ring','r0'):
            row=trial(kind,S,Y);rows.append(row)
            print(json.dumps(dict(kind=kind,S=S,Y=Y,bytes=row['phases'][1]['total_bill']['total_bytes'],
                expansions=row['phases'][1]['cb_metrics'].get('expansions',0))),flush=True)
    for S,Y in ((3,3),(4,2)):
        group=[r for r in rows if (r['S'],r['Y'])==(S,Y)]
        assert len({r['answer_sha256'] for r in group})==1
        for i in (0,1):
            assert all(r['phases'][i]['schedule']==group[0]['phases'][i]['schedule'] for r in group)
            assert all(r['phases'][i]['controller_metrics']==group[0]['phases'][i]['controller_metrics'] for r in group)
    bad=active_check();assert source==rt.identity()
    save(PACKAGE/'results/ab_deadq_cb_frontend_checks.json',dict(status='passed',source_hashes=source,checker_sha256=sha(__file__),
        tree_checker_sha256=sha(Path(__file__).with_name('check_ab_deadq_cb_tree.py')),cases=rows,active_check=bad,
        recursive_raw_map=True,inclusive_LLC=True,pressure_enabled=False,compressed_map=False,
        native_AB=False,formal_bandwidth_comparison=False,security_admission=False,true_peak_measured=False))
    print(json.dumps(dict(status='passed',cases=len(rows),application_answers=6*80)))


if __name__=='__main__':main()
