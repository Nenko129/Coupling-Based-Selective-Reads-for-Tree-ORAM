"""Exact two-block Path witness with Z4/L2: no capacity-one placement ties.

Secret initialization order and exclusion of each remotely requested target
are included. This remains an explicit adapted protocol, not native IR code.
"""
from common import *
from collections import defaultdict,Counter
from fractions import Fraction as F
import itertools,types
import ir_stash_runtime as rt
from ir_stash import StashTree
import heterogeneous_oram as h

L=2;Z=4;LEAVES=4


def nodes(leaf):return (1,2+(leaf>>1),4+leaf)


def place(records,opened,exclude):
    path=nodes(opened);pool={a:(u,l,-1) for a,(u,l,b) in records.items() if b==-1 or b in path}
    result={a:r for a,r in records.items() if a not in pool}
    for b in reversed(path):
        chosen=sorted((a for a,r in pool.items() if a!=exclude and b in nodes(r[1])),key=lambda a:pool[a][0])[:Z]
        for a in chosen:
            u,l,_=pool.pop(a);result[a]=(u,l,b)
    result.update(pool)
    assert all(r[2]==-1 or r[2] in nodes(r[1]) for r in result.values())
    assert all(sum(r[2]==b for r in result.values())<=Z for b in range(1,8))
    return result


def model_trial(queries,coins,order,skip):
    rs={};uid=0
    for i,a in enumerate(order):uid+=1;rs[a]=(uid,coins[i],-1);rs=place(rs,0,a)
    trace=[]
    for i,a in enumerate(queries):
        u,old,b=rs[a]
        if skip and b in (-1,1):opened=coins[2+i];exclude=None
        else:
            opened=old;uid+=1;rs[a]=(uid,coins[2+i],-1);exclude=a
        rs=place(rs,opened,exclude);trace.append(opened)
    return tuple(trace)


def exact(queries,skip):
    counts=Counter(model_trial(queries,coins,order,skip) for order in ((0,1),(1,0))
        for coins in itertools.product(range(LEAVES),repeat=2+len(queries)))
    count=2*LEAVES**(2+len(queries));return {k:F(v,count) for k,v in counts.items()}


def distance(a,b):return sum(abs(a.get(k,F(0))-b.get(k,F(0))) for k in a.keys()|b.keys())/2


def encrypted_trial(queries,coins,order,skip):
    rt.install(dict(seed=431,R=16,cached_levels=1,Z_by_depth=[],index_sets=2,index_ways=4,indexed=True))
    b=rt.Backend('path',L,2,B=64,Z=Z,A=3,S=1);b.tree.hold_address=None
    def placement(self,pool,view,gamma,constrained):
        held={u:r for u,r in list(pool.items()) if r.address==self.hold_address}
        for u in held:pool.pop(u)
        StashTree.placement(self,pool,view,gamma,constrained)
        for r in held.values():assert r.address not in self.stash;self.stash[r.address]=r
    b.tree.placement=types.MethodType(placement,b.tree);leaves=[None,None]
    for i,a in enumerate(order):
        b.tree.hold_address=a;leaves[a]=coins[i];b.tick(None,0,admit=(a,leaves[a],bytes([a])*64))
    openings=[]
    def observe(c,op,seq,stage,meta,request,response):
        if op==h.OPEN_FULL:
            ro,tree,sq,flags,body=h.parse_frame(request);assert (ro,tree,sq,flags)==(op,c.tree,seq,0)
            openings.append(int.from_bytes(body[:8],'big'))
        return response
    b.io.mutator=observe
    for i,a in enumerate(queries):
        prior_calls=len(openings);local=b.local_access(a,leaf=leaves[a]) if skip else None
        if local is None:
            b.tree.hold_address=a;answer=b.tick(a,leaves[a],replace=(coins[2+i],lambda p:p));leaves[a]=coins[2+i]
        else:
            answer=local[0];b.tree.hold_address=None;b.tick(None,coins[2+i])
        assert answer==bytes([a])*64 and len(openings)==prior_calls+1 and b.tree.t==b.tree.g==3+i
    return tuple(openings)


def main():
    source=rt.identity();rows=[]
    for skip in (False,True):
        for n in range(1,5):
            ds={q:exact(q,skip) for q in itertools.product((0,1),repeat=n)};maximum=F(0);witness=None
            for a,b in itertools.combinations(ds,2):
                d=distance(ds[a],ds[b])
                if d>maximum:maximum=d;witness=(a,b)
            row=dict(skip=skip,requests=n,max_tv=str(maximum))
            if witness:
                a,b=witness;row.update(left=list(a),right=list(b),left_pmf={str(k):str(v) for k,v in ds[a].items()},right_pmf={str(k):str(v) for k,v in ds[b].items()})
            rows.append(row)
        print(json.dumps(dict(skip=skip,max_tv=[r['max_tv'] for r in rows[-4:]])),flush=True)
    assert all(r['max_tv']=='0' for r in rows if not r['skip'])
    encrypted=[];executions=0
    for skip in (False,True):
        qs=[(0,0),(0,1)];pmfs=[]
        for query in qs:
            counts=Counter(encrypted_trial(query,coins,order,skip) for order in ((0,1),(1,0))
                for coins in itertools.product(range(4),repeat=4))
            executions+=512;actual={k:F(v,512) for k,v in counts.items()};assert actual==exact(query,skip)
            pmfs.append(actual);encrypted.append(dict(skip=skip,queries=list(query),executions=512,pmf={str(k):str(v) for k,v in actual.items()}))
        print(json.dumps(dict(skip=skip,encrypted_pair_tv=str(distance(*pmfs)))),flush=True)
    assert source==rt.identity() and executions==2048
    local_pdf=PACKAGE.parent/'细化准备_2026-09-15/literature/pdf/R12_ir_oram_path_access_type_based_memory_intensity.pdf'
    save(PACKAGE/'results/ir_z4_skip_projection.json',dict(status='projection_crosschecked',config=dict(kind='path',L=L,N=2,Z=Z,A=3,R=16,cached_levels=1),
        rows=rows,encrypted=encrypted,executions=executions,checker_sha256=sha(__file__),source_hashes=source,
        initialization_order='uniform secret permutation of both addresses',initialization_path_prefix=[0,0],
        prefix_probability_if_uniform_openings='1/16',target_hold='exclude current target from immediate remote-access or admission writeback',
        padding='independent uniform dummy path on local hit; no hit remap',
        randomness='one independent uniform leaf per slot: dummy leaf on a hit or fresh remap leaf on a miss; unused alternate coordinate integrated out',
        paper_pdf_sha256=sha(local_pdf),paper_url='https://mehrnoosh.net/research/IR-ORAM-HPCA%2722.pdf',
        native_paper_attack_claim=False,full_native_state_machine=False,security_admission=False,
        scope='Path-only first-remote-leaf projection, exact model n1..4, encrypted crosscheck of two-request witnesses; no target-scale extrapolation'))
    print(json.dumps(dict(status='projection_crosschecked',executions=executions,security_admission=False)),flush=True)


if __name__=='__main__':main()
