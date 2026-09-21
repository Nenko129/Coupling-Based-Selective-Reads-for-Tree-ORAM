"""Joint profiles and like-for-like framed-byte comparisons, with exact budgets."""
from optimized_gate import OptimizedBank,ROOT,BASE,upper
from optimized_oram import Config,TAG,local_indices
from optimized_cost import expected_tree,sum_rows,early_interval,probabilities
from fractions import Fraction as F
from functools import lru_cache
from dataclasses import asdict
import json,sys

N0=12582912;ONLINE=(1<<64)-N0-12288;MEMORY=1425408

def min_height(N,A):return next(L for L in range(1,31) if N<=A*(1<<(L-1)))
@lru_cache(None)
def evaluated(c):return expected_tree(c)
def amount(c):return float(evaluated(c)['total']['upper'])
def path_workspace(cs):return max((c.Z*len(c.levels)+1)*c.B for c in cs)

def build(bank,cores,Bs,original_kind,compact=True,fused=True):
    ns=[N0]
    for b in Bs[1:]:ns.append((4*ns[-1]+b-1)//b)
    # For two layers, preserve each original layer's numerical lifetime bound.
    # Three layers divide the old map contribution over the two new map layers.
    oldoff=2 if original_kind=='sde' else 6
    olddata=(ONLINE+N0)*bank.grids[4,3][24,192-oldoff]
    oldmap=(ONLINE+N0+12288)*bank.grids[4,3][14,144-oldoff]
    allocations=[olddata]+[oldmap/(len(Bs)-1)]*(len(Bs)-1)
    cs=[]
    for j,((kind,Z,A),B,N,budget) in enumerate(zip(cores,Bs,ns,allocations)):
        L=min_height(N,A);Q=ONLINE+sum(ns[:j+1]);offset=A-1+(Z if kind=='r0' else 0)
        r=next(r for r in range(281) if Q*bank.grids[Z,A][L+1,r]<=budget);R=min(N,r+offset)
        candidates=[Config(kind,L,N,B,Z=Z,A=A,S=S,R=R,tree=j,compact=compact,fused=fused)
                    for S in (range(1,14-Z) if kind=='r0' else [3])]
        cs.append(min(candidates,key=amount))
    return cs,olddata+oldmap

def profile(cs,label,bank=None,limit=None):
    rows=[evaluated(c) for c in cs];result=sum_rows(rows);server=0;rpc=0
    for c in cs:
        nodes=(1<<(c.L+1))-1
        server+=((nodes-1)*(c.n*c.W+c.H+(len(local_indices(c.n))+2)*TAG)+2*TAG) if c.rootless else nodes*(c.n*c.W+c.H+(len(local_indices(c.n))+2 if c.ring else 2)*TAG)
        if c.kind=='path':rpc+=2
        elif not c.ring:rpc+=2+2/c.A
        else:
            rpc+=3+3/c.A
            if not c.fused:
                pp=probabilities(c.L) if c.selective else (F(1),)*(c.L+1)
                rpc+=2*sum(float(early_interval(c.A*(1<<d),pp[d]/(1<<d),c.S).hi)/c.A for d in c.levels)
    result.update(label=label,configs=[asdict(c) for c in cs],layer_bytes=[float(x['total']['upper']) for x in rows],
                  bytes=float(result['total']['upper']),payload_plus_terminal=sum(c.R*c.B for c in cs)+4*cs[-1].N,
                  terminal_map_bytes=4*cs[-1].N,server_bytes=server,expected_RPC=rpc)
    result['report_path_payload_workspace']=path_workspace(cs)
    result['persistent_plus_report_path_payload']=result['payload_plus_terminal']+path_workspace(cs)
    if bank:
        result['capacity_plan']=bank.plan(cs,ONLINE,limit)
        result['original_numeric_stash_bound_preserved']=True
    return result

def main():
    sealed='--sealed' in sys.argv;bank=OptimizedBank(verify_variant=sealed)
    old=json.loads((BASE/'results/unified_cost_table.json').read_text())['table']
    original={k:float(old[k]['total']['upper']) for k in ('path','ring','sde','r0')}
    variants=[]
    families={
      'SDE-v3':([('sde',4,3),('sde',4,3)],'sde'),
      'R0-v3-Z4':([('r0',4,3),('r0',4,3)],'r0'),
      'Hybrid-v3-Z4':([('r0',4,3),('sde',4,3)],'r0'),
      'R0-v3-Z7':([('r0',7,6),('r0',7,6)],'r0'),
      'Hybrid-v3-Z7':([('r0',7,6),('sde',4,3)],'r0')}
    grid=[]
    for label,(cores,orig) in families.items():
        cs,limit=build(bank,cores,[4096,512],orig)
        variants.append(profile(cs,label+'-512',bank,limit))
        candidates=[]
        for B1 in range(128,4097,4):
            cc,budget=build(bank,cores,[4096,B1],orig)
            memory=sum(c.R*c.B for c in cc)+4*cc[-1].N
            if memory<=MEMORY:candidates.append((sum(amount(c) for c in cc),cc,budget))
        _,cc,budget=min(candidates,key=lambda x:x[0])
        variants.append(profile(cc,label+'-best-two',bank,budget))
        if any(core[1:]==(7,6) for core in cores):
            peaklimit=MEMORY+93*4096
            strict=[x for x in candidates if sum(c.R*c.B for c in x[1])+4*x[1][-1].N+path_workspace(x[1])<=peaklimit]
            _,cc,budget=min(strict,key=lambda x:x[0])
            variants.append(profile(cc,label+'-best-with-path-budget',bank,budget))
        grid.append(dict(family=label,feasible_profiles=len(candidates),B1=[128,4096,4]))
    # Cost baselines receive the same map-block, header and fusion optimizations.
    # Their stash failure bounds are not asserted by the selective gate.
    fair=[]
    for label,kind,Z,A,maxS in [('Path-Z4','path',4,3,1),('Path-Z5','path',5,3,1),
                                ('Ring-Z4A3','ring',4,3,10),('Ring-Z7A6','ring',7,6,10)]:
        cs=[]
        for j,(N,B) in enumerate([(N0,4096),(98304,512)]):
            L=min_height(N,A)
            choices=[Config(kind,L,N,B,Z=Z,A=A,S=s,R=192 if j==0 else 160,tree=j) for s in range(1,maxS+1)]
            cs.append(min(choices,key=amount))
        fair.append(profile(cs,label+'-common-opts-512'))
    # A fair Ring-data/SDE-map hybrid gives the competing data-tree protocol
    # the identical optimized map, and can be compared layer by layer.
    template=next(v for v in variants if v['label']=='Hybrid-v3-Z7-512')
    mapc=Config(**template['configs'][1]);choices=[Config('ring',22,N0,4096,Z=7,A=6,S=s,R=192,tree=0) for s in range(1,11)]
    fair.append(profile([min(choices,key=amount),mapc],'Ring-Z7A6/SDE-map-512'))
    for v in variants:
        v['reduction_vs_original_percent']={k:100*(1-v['bytes']/x) for k,x in original.items()}
        v['reduction_vs_fair_percent']={x['label']:100*(1-v['bytes']/x['bytes']) for x in fair}
    result=dict(original_bytes=original,variants=variants,fair_baselines=fair,grid=grid,
        frozen_reference='SOC2 report table, Path Z4 and full-read lazy-neutral Ring, B4096/4096.',
        comparison_scope='All costs include data/header/auth/control. Common-opts baselines use B4096/512, compact headers, and Ring fusion with per-tree S search; they are not globally optimized cache/XOR baselines and their stash guarantees are not certified by the selective gate.',
        security_budget='Each variant preserves the corresponding original numerical stash lifetime upper bound, including setup, and passes the new conservative conditional cryptographic budget.',
        measurement='Application-frame periodic expectations, not network throughput, storage page-rounded I/O, or 48GiB execution. Client memory column excludes metadata, transient workspaces and runtime.')
    (ROOT/'results/profile_comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('ORIGINAL',original)
    for v in variants:print(v['label'],round(v['bytes'],2),[(c['B'],c['Z'],c['A'],c['S'],c['L'],c['R']) for c in v['configs']],v['payload_plus_terminal'],v['expected_RPC'],{k:round(x,2) for k,x in v['reduction_vs_original_percent'].items()})
    for v in fair:print('FAIR',v['label'],round(v['bytes'],2),[(c['Z'],c['A'],c['S']) for c in v['configs']])

if __name__=='__main__':main()
