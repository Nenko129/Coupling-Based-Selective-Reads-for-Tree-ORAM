"""Full read-only audit and independently recomputed B2 bytes/RPC effects."""
from common import *
from functools import lru_cache
import math,statistics
from run_fast import expected_identity
from analyze_ir_dwb import bill

def stats(values):
    assert len(values)==5
    mean=statistics.mean(values);half=2.7764451051977987*statistics.stdev(values)/math.sqrt(5)
    return dict(n=5,mean=mean,ci95=[mean-half,mean+half],per_seed=values)

@lru_cache(None)
def answer(path,trace_hash,N,B,seed,workload,Q):
    p=PACKAGE/path;assert sha(p)==trace_hash;t=json.loads(p.read_text())
    assert (t['N'],t['count'],t['seed'],t['workload'])==(N,Q,seed,workload)
    assert len(t['rows'])==Q
    versions=[0]*N;h=hashlib.sha256()
    for a,v in t['rows']:
        assert 0<=a<N
        h.update(hashlib.shake_256(b'SOC3-EVAL-PAYLOAD-v1'+a.to_bytes(8,'big')+versions[a].to_bytes(8,'big')).digest(B))
        if v is not None:assert isinstance(v,int) and v>=1;versions[a]=v
    return h.hexdigest()

def configs(s):
    N=s['N'];B=s['B'];cs=[];Z,A,S=s['profile']
    while True:
        L=1
        while N>A*2**(L-1):L+=1
        cs.append(dict(kind=s['kind'],L=L,N=N,B=B,Z=Z,A=A,S=S,R=s['R'],tree=len(cs),compact=s['compact'],fused=s['fusion']))
        if N*4<=s['terminal_bytes']:break
        B=s['map_B'];N=(N+B//4-1)//(B//4)
    return cs

def audit_run(r,s):
    assert r['status']=='passed'
    assert {k:v for k,v in r['spec'].items() if k not in ('id','experiment_class')}=={k:v for k,v in s.items() if k not in ('id','experiment_class')}
    assert r['source_hashes'] in (source_identity(),expected_identity())
    if r['source_hashes']==expected_identity():
        assert r['execution_revision']['name']=='hmac_prefix_reuse_v1'
        assert r['execution_revision']['proof_sha256']==sha(PACKAGE/'results/fast_prf_regression.json')
    assert r['configs']==configs(s)
    assert r['correctness_checked_requests']==s['warmup']+s['requests']
    assert r['answer_sha256']==answer(r['trace']['path'],r['trace']['sha256'],s['N'],s['B'],s['trace_seed'],s['workload'],s['warmup']+s['requests'])
    assert not r['latency_claim'] and not r['true_client_peak_measured']
    bill(r['setup']);assert r['setup']['first_sequence']==0;seq=r['setup']['next_sequence']
    for phase,Q in [('warmup',s['warmup']),('measurement',s['requests'])]:
        p=r['phases'][phase];bill(p);assert p['first_sequence']==seq;seq=p['next_sequence']
        assert p['requests']==Q and p['backend_requests']==[Q]*len(r['configs'])
    m=r['phases']['measurement']
    assert r['bytes_per_request']==m['total_bytes']/s['requests'] and r['rpc_per_request']==m['rpc']/s['requests']
    assert sum(w['bytes'] for w in r['measurement_windows'])==m['total_bytes']
    assert sum(w['rpc'] for w in r['measurement_windows'])==m['rpc']
    assert [w['through_request'] for w in r['measurement_windows']]==list(range(128,s['requests']+1,128))
    assert r['terminal_position_map_bytes']==4*r['configs'][-1]['N']
    initial=0
    for cfg,clock in zip(r['configs'],r['final_clock']):
        initial+=cfg['N']
        assert clock['t']==initial+s['warmup']+s['requests'] and clock['g']==clock['t']//cfg['A']
    storage=r['server_storage'];assert storage['total_bytes']==sum(storage['components'].values())
    return True

def main():
    planpath=PACKAGE/'formal_ablation_plan.json';plan=json.loads(planpath.read_text())
    entries=[dict(spec=s,source=f"results/formal_ablation/{s['id']}.json") for s in plan['specs']]+plan['aliases']
    rows={};raw=[];receipts=[]
    for x in entries:
        s=x['spec'];p=PACKAGE/x['source'];r=json.loads(p.read_text());audit_run(r,s)
        rows[s['id']]=r
        raw.append(dict(id=s['id'],physical_id=r['spec']['id'],spec=s,total_bytes=r['phases']['measurement']['total_bytes'],
            bytes_per_request=r['bytes_per_request'],rpc_per_request=r['rpc_per_request'],components=r['phases']['measurement']['components']))
        receipts.append(dict(id=s['id'],path=x['source'],sha256=sha(p)))
    assert len(rows)==45
    # Identical application answers and traces across all nine cells per seed.
    for seed in range(101,106):
        group=[r for r in rows.values() if r['spec']['trace_seed']==seed]
        assert len(group)==9 and all((r['trace'],r['answer_sha256'])==(group[0]['trace'],group[0]['answer_sha256']) for r in group)
    effects=[]
    pairs=[('fusion_without_compact_pct','cf00','cf01'),('fusion_with_compact_pct','cf10','cf11'),
           ('compact_without_fusion_pct','cf00','cf10'),('compact_with_fusion_pct','cf01','cf11')]
    for family in ('43','76'):
        for name,base,var in pairs:
            a=[rows[f'B2_R0_{family}_{base}_seed{s}'] for s in range(101,106)]
            b=[rows[f'B2_R0_{family}_{var}_seed{s}'] for s in range(101,106)]
            effects.append(dict(family=family,effect=name,
                bytes_saving=stats([100*(1-x['bytes_per_request']/y['bytes_per_request']) for y,x in zip(a,b)]),
                rpc_saving=stats([100*(1-x['rpc_per_request']/y['rpc_per_request']) for y,x in zip(a,b)])))
        interaction=[sum(sign*rows[f'B2_R0_{family}_cf{cell}_seed{s}']['bytes_per_request'] for cell,sign in [('00',1),('01',-1),('10',-1),('11',1)]) for s in range(101,106)]
        effects.append(dict(family=family,effect='interaction_bytes',bytes_saving=stats(interaction),rpc_saving=None))
    # Reconcile the previous analyzer; this code never imports its statistics.
    priorpath=PACKAGE/'results/ablation_measured.json';prior=json.loads(priorpath.read_text())
    assert prior['complete'] and prior['audited_observations']==45 and len(prior['effects'])==10
    def close(x,y):assert math.isclose(x,y,rel_tol=1e-11,abs_tol=1e-8),(x,y)
    for e in effects:
        previous=next(x for x in prior['effects'] if (x['family'],x['effect'])==(e['family'],e['effect']))
        for key in ('mean',):close(e['bytes_saving'][key],previous[key])
        for x,y in zip(e['bytes_saving']['ci95'],previous['ci95']):close(x,y)
    order=['43_large_map_cf00','43_cf00','43_cf10','43_cf11','76_cf11'];ladder=[]
    for before,after in list(zip(order,order[1:]))+[(order[0],order[-1])]:
        a=[rows[f'B2_R0_{before}_seed{s}'] for s in range(101,106)]
        b=[rows[f'B2_R0_{after}_seed{s}'] for s in range(101,106)]
        ladder.append(dict(before=before,after=after,
            bytes_saving=stats([100*(1-y['bytes_per_request']/x['bytes_per_request']) for x,y in zip(a,b)]),
            rpc_saving=stats([100*(1-y['rpc_per_request']/x['rpc_per_request']) for x,y in zip(a,b)])))
    cells=[]
    for cell in ['43_large_map_cf00']+[f'{f}_cf{c}' for f in ('43','76') for c in ('00','01','10','11')]:
        rs=[rows[f'B2_R0_{cell}_seed{s}'] for s in range(101,106)];values=[r['bytes_per_request'] for r in rs]
        cells.append(dict(cell=cell,n=5,bytes_per_request=stats(values),rpc_per_request=stats([r['rpc_per_request'] for r in rs]),
            cost_cv=statistics.stdev(values)/statistics.mean(values)))
    repeat=any(c['cost_cv']>.10 for c in cells) or any((e['bytes_saving']['ci95'][1]-e['bytes_saving']['ci95'][0])/2>5 for e in effects if e['effect']!='interaction_bytes')
    save(PACKAGE/'results/ablation_complete_audit.json',dict(status='passed',observations=45,unique_physical_runs=len(set(x['path'] for x in receipts)),
        plan_sha256=sha(planpath),prior_statistics_sha256=sha(priorpath),auditor_sha256=sha(__file__),receipts=receipts,raw=raw,cells=cells,effects=effects,ladder=ladder,
        repeat_gate_triggered=repeat,source_hashes=[source_identity(),expected_identity()],
        scope='application serialized bytes/RPC; complete B2 but not complete paper; no CPU, memory, latency or global tuning optimality claim'))
    print(json.dumps(dict(status='passed',observations=45,cells=9,effects=10,ladder=5,repeat_gate_triggered=repeat)))

if __name__=='__main__':main()
