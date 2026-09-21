"""Reduced-scale Z7/A6 execution and exact fusion/ablation accounting checks."""
from optimized_oram import *
from optimized_cost import invoice,expected_tree
from optimized_gate import OptimizedBank,OptimizedCertifiedORAM,ROOT,BASE
from variant_tests import Differential,verify_physical_snapshot
from fractions import Fraction as F
from dataclasses import replace
import random,json,hashlib,sys
sys.path.append(str(BASE/'src'))
import unified_cost as oldcost
import integrated_oram as oldoram

def new_execution():
    results=[]
    for label,cores,bs in [
        ('z7_pure',[('r0',7,6,6),('r0',7,6,5)],[4096,512]),
        ('z7_mixed',[('r0',7,6,6),('sde',4,3,3)],[4096,512]),
        ('z7_mixed_small',[('r0',7,6,6),('sde',4,3,3)],[4096,256]),
        ('z7_frequent_neutral',[('r0',7,6,1),('sde',4,3,3)],[256,64])]:
        ns=[384]
        for b in bs[1:]:ns.append((4*ns[-1]+b-1)//b)
        cs=[Config(k,next(L for L in range(1,31) if n<=A*(1<<(L-1))),n,b,Z=Z,A=A,S=S,R=192 if j==0 else n,tree=j)
            for j,((k,Z,A,S),n,b) in enumerate(zip(cores,ns,bs))]
        m=RecursiveORAM(cs,hashlib.sha512(label.encode()).digest());d=Differential(cs);counts=Counter()
        for t in m.trees:
            t.observer=d.observe
            original=t.fused_logical
            def observed(view,address,original=original,t=t):
                ns=[b for b,h in view.headers.items() if h.count==t.c.S]
                counts['neutral_buckets']+=len(ns)
                counts['neutral_with_target']+=sum(any(x.address==address for x in view.headers[b].live.values()) for b in ns)
                counts['multiple_neutrals']+=len(ns)>1
                counts['mixed_single_and_multi']+=bool(ns) and len(ns)<len(view.headers)
                return original(view,address)
            t.fused_logical=observed
        m.initialize(lambda a:ui(a+3,bs[0]));truth=[ui(a+3,bs[0]) for a in range(ns[0])];rng=random.Random(9102);start=len(m.io.events)
        for i in range(360):
            a=0 if i%9<3 else (i*37)%ns[0] if i%9<6 else rng.randrange(ns[0])
            value=ui(10000+i,bs[0]) if i%3==0 else None
            assert m.access(a,value)==truth[a]
            if value is not None:truth[a]=value
            assert m.anchor()==m.committed
        bill=invoice(cs,m.io.events);verify_physical_snapshot(m,d)
        assert counts['neutral_buckets']>0 and counts['mixed_single_and_multi']>0
        assert not any(e['stage']=='early' for e in m.io.events)
        results.append(dict(label=label,online_top_requests=360,layer_checks=d.accesses,token_depth_checks=d.depth_comparisons,
                            field_checks=d.field_comparisons,frames=bill['events_checked'],coverage=dict(counts),
                            observed_online_bytes=invoice(cs,m.io.events[start:])['total_bytes'],max_stash=[t.max_stash for t in m.trees]))
    return results

def fusion_invoice_identity():
    # Compare the executed fused read/write to a public-shape expansion into the
    # former neutral RPCs plus one logical read. Does not inspect byte lengths
    # to predict savings: independent invoice_event accounts every field.
    c=Config('r0',5,48,B=64,S=1,R=96);m=RecursiveORAM([c],bytes(range(64)));m.initialize()
    for i in range(500):m.access(i%48,ui(i,64))
    events=m.io.events;checks=0;saved=Counter();neutral_slots=0
    for i,e in enumerate(events):
        if e['stage']!='logical' or e['opcode']!=READ_SLOTS:continue
        ndepths=[d for d,s in zip(e['depths'],e['slots']) if len(s)==c.Z]
        if not ndepths:continue
        actual=invoice([c],[e,events[i+1]])
        assert events[i+1]['opcode']==WRITE and set(events[i+1]['full_depths'])==set(ndepths)
        # For neutral buckets, a hypothetical subsequent single-slot witness
        # may have any physical index. Enumerate every index to test the exact
        # shape identity, including the padded local tree's unequal paths.
        for chosen in range(c.n):
            expansion=[]
            for d in ndepths:
                inds=e['slots'][e['depths'].index(d)]
                expansion.extend([dict(opcode=READ_SLOTS,depths=[d],slots=[inds]),dict(opcode=WRITE,depths=[d],full_depths=[d])])
            logical=dict(opcode=READ_SLOTS,depths=e['depths'],slots=[[chosen] if d in ndepths else inds for d,inds in zip(e['depths'],e['slots'])])
            expansion.extend([logical,dict(opcode=WRITE,depths=e['depths'],full_depths=[])])
            from optimized_cost import invoice_event
            old=Counter()
            for x in expansion:old.update(invoice_event(c,x))
            delta=sum(old.values())-actual['total_bytes']
            expected=sum(c.W+c.H+(len(witnesses(c.n,(chosen,)))+d+2)*TAG+192 for d in ndepths)
            assert delta==expected,(delta,expected);checks+=1
        neutral_slots+=len(ndepths)
    return dict(exact_fusion_invoice_equalities=checks,covered_neutral_buckets=neutral_slots)

def cost_regressions():
    checks=0
    for kind in ('path','sde','ring','r0'):
        for L,B,S in [(5,64,1),(13,512,3),(23,4096,5)]:
            N=min(48,3*(1<<(L-1)))
            oc=oldoram.Config(kind,L,N,B,S=S)
            nc=Config(kind,L,N,B,S=S,compact=False,fused=False)
            assert oldcost.expected_tree(oc)['total']==expected_tree(nc)['total'];checks+=1
    return dict(unoptimized_cost_interval_regressions=checks)

def main():
    result=dict(new_profiles=new_execution(),fusion_invoice=fusion_invoice_identity(),cost_regressions=cost_regressions())
    (ROOT/'results/new_profile_tests.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
