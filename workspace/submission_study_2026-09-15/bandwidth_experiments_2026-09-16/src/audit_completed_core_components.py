"""Independent answers/ledgers and paired effects for completed B1/static runs.

Cached AB is static Y0, and cached IR excludes native hit skipping and DWB.
Performance completion never supplies a missing security admission.
"""
from common import *
import math,statistics
from collections import defaultdict
from audit_completed_ablation import answer,configs,stats
from analyze_ir_dwb import bill
from run_fast import expected_identity


def audit_run(r,s,cached):
    assert r['status']=='passed' and r['spec']==s
    assert r['source_hashes'] in (source_identity(),expected_identity())
    if r['source_hashes']==expected_identity():
        assert r['execution_revision']['name']=='hmac_prefix_reuse_v1'
        assert r['execution_revision']['proof_sha256']==sha(PACKAGE/'results/fast_prf_regression.json')
    expected=configs(s)
    if cached:
        for i,c in enumerate(expected):
            c.update(Z_by_depth=s.get('Z_by_depth',[]) if i==0 else [],S_by_depth=s.get('S_by_depth',[]) if i==0 else [])
        hashes=r['cache_and_heterogeneous_sources']
        assert set(hashes)=={'heterogeneous_oram.py','heterogeneous_fusion.py','cached_transport.py','cached_cost.py','run_cached_component.py'}
        assert all(sha(Path(__file__).parent/n)==v for n,v in hashes.items())
        assert r['cache_representation']['bytes']>0
    assert r['configs']==expected
    assert r['correctness_checked_requests']==s['warmup']+s['requests']
    assert r['answer_sha256']==answer(r['trace']['path'],r['trace']['sha256'],s['N'],s['B'],s['trace_seed'],s['workload'],s['warmup']+s['requests'])
    assert not r['latency_claim'] and not r['true_client_peak_measured']
    bill(r['setup']);assert r['setup']['first_sequence']==0;seq=r['setup']['next_sequence']
    for phase,Q in [('warmup',s['warmup']),('measurement',s['requests'])]:
        p=r['phases'][phase];bill(p);assert p['first_sequence']==seq;seq=p['next_sequence']
        assert p['requests']==Q and p['backend_requests']==[Q]*len(expected)
    m=r['phases']['measurement']
    assert r['bytes_per_request']==m['total_bytes']/s['requests'] and r['rpc_per_request']==m['rpc']/s['requests']
    assert sum(w['bytes'] for w in r['measurement_windows'])==m['total_bytes']
    assert sum(w['rpc'] for w in r['measurement_windows'])==m['rpc']
    assert [w['through_request'] for w in r['measurement_windows']]==list(range(128,s['requests']+1,128))
    assert r['terminal_position_map_bytes']==4*expected[-1]['N']
    initial=0
    for c,clock in zip(expected,r['final_clock']):
        initial+=c['N'];t=initial+s['warmup']+s['requests']
        assert clock['t']==t and clock['g']==(t if c['kind']=='path' else t//c['A'])
    assert r['server_storage']['total_bytes']==sum(r['server_storage']['components'].values())


def main():
    plans=['formal_core_plan.json','formal_cached_component_plan.json','formal_cached_admitted_plan.json']
    rows=[];receipts=[];cells=defaultdict(list)
    for name in plans:
        plan=json.loads((PACKAGE/name).read_text(encoding='utf-8'))
        for s in plan['specs']:
            if name=='formal_cached_component_plan.json' and s['family']!='AB':continue
            # The admitted plan also aliases the same AB IDs. Audit those
            # physical observations once; this plan adds only new R480 IR.
            if name=='formal_cached_admitted_plan.json' and s['family']!='IR':continue
            p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
            r=json.loads(p.read_text(encoding='utf-8'));audit_run(r,s,name!='formal_core_plan.json')
            rows.append(r);receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
            cells[s.get('family','core'),s.get('layout','uniform'),s['kind'],s['workload'],s['N'],s['B']].append(r)
    assert len(rows)==140 and len(cells)==28
    cell_rows=[]
    for key,rs in sorted(cells.items()):
        assert sorted(r['spec']['trace_seed'] for r in rs)==list(range(101,106))
        vals=[r['bytes_per_request'] for r in rs]
        cell_rows.append(dict(family=key[0],layout=key[1],kind=key[2],workload=key[3],N=key[4],B=key[5],
            bytes_per_request=stats(vals),rpc_per_request=stats([r['rpc_per_request'] for r in rs]),
            cost_cv=statistics.stdev(vals)/statistics.mean(vals)))
    by_pair=defaultdict(dict)
    for r in rows:
        s=r['spec'];key=(s.get('family','core'),s.get('layout','uniform'),s['workload'],s['N'],s['B'])
        by_pair[key][s['kind'],s['trace_seed']]=r
    effects=[];prior=json.loads((PACKAGE/'results/paired_statistics.json').read_text())['rows']
    for key,rs in sorted(by_pair.items()):
        for base,new in [('path','sde'),('deferred','sde'),('ring','gc_ring'),('ring','r0'),('gc_ring','r0')]:
            if not all((k,seed) in rs for k in (base,new) for seed in range(101,106)):continue
            details=[]
            for seed in range(101,106):
                a,b=rs[base,seed],rs[new,seed]
                assert (a['trace'],a['answer_sha256'])==(b['trace'],b['answer_sha256'])
                sa,sb=a['spec'],b['spec'];ignore={'id','kind'}
                assert {k:v for k,v in sa.items() if k not in ignore}=={k:v for k,v in sb.items() if k not in ignore}
                details.append(dict(seed=seed,baseline=sa['id'],variant=sb['id'],bytes_saving=100*(1-b['bytes_per_request']/a['bytes_per_request']),
                    rpc_saving=100*(1-b['rpc_per_request']/a['rpc_per_request'])))
            e=dict(family=key[0],layout=key[1],workload=key[2],N=key[3],B=key[4],baseline=base,variant=new,
                bytes_saving=stats([d['bytes_saving'] for d in details]),rpc_saving=stats([d['rpc_saving'] for d in details]),per_seed=details)
            prev=next(x for x in prior if (x['family'],x['layout'] or 'uniform',x['workload'],x['N'],x['B'],x['baseline'],x['selective'])==key+(base,new))
            assert prev['n']==5
            for x,y in zip([e['bytes_saving']['mean']]+e['bytes_saving']['ci95'],[prev['paired_mean_saving_pct']]+prev['ci95']):
                assert math.isclose(x,y,rel_tol=1e-11,abs_tol=1e-8)
            effects.append(e)
    assert len(effects)==18
    repeat=any(c['cost_cv']>.10 for c in cell_rows) or any((e['bytes_saving']['ci95'][1]-e['bytes_saving']['ci95'][0])/2>5 for e in effects)
    out=dict(status='passed',observations=140,cells=cell_rows,effects=effects,receipts=receipts,
        plan_hashes={n:sha(PACKAGE/n) for n in plans},paired_statistics_sha256=sha(PACKAGE/'results/paired_statistics.json'),
        auditor_sha256=sha(__file__),helper_sha256={n:sha(Path(__file__).parent/n) for n in ('audit_completed_ablation.py','analyze_ir_dwb.py')},
        repeat_gate_triggered=repeat,full_paper_complete=False,full_native_IR_AB=False,
        scope='B1 fixed-profile core and static cached AB/IR components; not tuned optimum, DWB or native hit/CB/DeadQ performance')
    save(PACKAGE/'results/core_components_complete_audit.json',out)
    md=['# B1核心与静态IR/AB组件：完整重复审计','',
        '60次核心、40次AB静态组件、40次R480 IR静态组件全部完成。逐行核对独立答案摘要、运行源码、配置、完整字节分项、RPC序号和递归时钟；28个配置每格5次、18个比较均未触发追加重复门槛。','',
        '统计口径为测量阶段双向序列化字节/完成请求。初始化与暖机另列；不计TCP/TLS，不报告原型运行时间为延迟收益。核心均使用Z4/A3/S3，这不是双方分别调优后的比较。静态AB为Y0，无CB/DeadQ；静态IR无IR-Stash/DWB，不能替代完整组合结果。','',
        '| 家族/布局 | N/B | 负载 | 后端 | bytes/op均值 | RPC/op均值 |','|---|---|---|---|---:|---:|']
    for c in cell_rows:md.append(f"| {c['family']}/{c['layout']} | {c['N']}/{c['B']} | {c['workload']} | {c['kind']} | {c['bytes_per_request']['mean']:,.2f} | {c['rpc_per_request']['mean']:.3f} |")
    md+=['','| 家族/布局 | N/B | 负载 | 比较 | 字节减少 | 95%区间 | RPC减少 |','|---|---|---|---|---:|---|---:|']
    for e in effects:
        lo,hi=e['bytes_saving']['ci95']
        md.append(f"| {e['family']}/{e['layout']} | {e['N']}/{e['B']} | {e['workload']} | {e['baseline']} → {e['variant']} | {e['bytes_saving']['mean']:.3f}% | [{lo:.3f}%, {hi:.3f}%] | {e['rpc_saving']['mean']:.3f}% |")
    md+=['','IR静态异质布局在4KiB块下对Deferred约21.53%，在64B下约19.24%；因此“除ρ外均超过20%”仍不成立。块长度和是否包含系统机制都必须随数字报告。','',
        '原始140行及SHA256、28格绝对开销、18组逐种子效应和区间保存在 `results/core_components_complete_audit.json`。缺少的基线安全归约不因本批完成而自动补齐。']
    (PACKAGE/'36_B1核心与静态组件完整结果.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',observations=140,cells=28,effects=18,repeat_gate_triggered=repeat)))


if __name__=='__main__':main()
