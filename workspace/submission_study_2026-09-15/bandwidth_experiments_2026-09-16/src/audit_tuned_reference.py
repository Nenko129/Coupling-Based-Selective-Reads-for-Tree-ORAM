"""Audit actual tuned and supplementary reference bytes; no partial final CIs."""
from common import *
from collections import defaultdict
import statistics
from audit_completed_core_components import audit_run
from audit_completed_ablation import answer, configs, stats
from audit_storage_components import audit_materialized
from analyze_ir_dwb import bill
from run_fast import expected_identity as fast_identity
from run_bulk_scale import identity as bulk_identity


def audit_supplement(r,s):
    assert r['status']=='passed' and r['spec']==s and r['source_hashes']==bulk_identity()
    assert r['extended_experiment']['source_identity']==bulk_identity()
    assert r['execution_revision']['name']=='hmac_bulk_exact_v2'
    assert r['execution_revision']['proof_sha256']==sha(PACKAGE/'results/bulk_prf_checks.json')
    cs=configs(s);assert r['configs']==cs and s['kind']=='path' and s['profile']==[5,3,3] and s['R']==258
    assert r['correctness_checked_requests']==s['warmup']+s['requests']
    assert r['answer_sha256']==answer(r['trace']['path'],r['trace']['sha256'],s['N'],s['B'],s['trace_seed'],s['workload'],s['warmup']+s['requests'])
    assert not r['latency_claim'] and not r['true_client_peak_measured']
    bill(r['setup']);assert r['setup']['first_sequence']==0;seq=r['setup']['next_sequence']
    for phase,q in [('warmup',s['warmup']),('measurement',s['requests'])]:
        x=r['phases'][phase];bill(x);assert x['first_sequence']==seq;seq=x['next_sequence']
        assert x['requests']==q and x['backend_requests']==[q]*len(cs)
    x=r['phases']['measurement'];q=s['requests']
    assert r['bytes_per_request']==x['total_bytes']/q and r['rpc_per_request']==x['rpc']/q
    assert sum(w['bytes'] for w in r['measurement_windows'])==x['total_bytes']
    assert sum(w['rpc'] for w in r['measurement_windows'])==x['rpc']
    assert [w['through_request'] for w in r['measurement_windows']]==list(range(128,q+1,128))
    assert r['terminal_position_map_bytes']==4*cs[-1]['N']
    initial=0
    for c,clock in zip(cs,r['final_clock']):
        initial+=c['N'];assert clock['t']==clock['g']==initial+s['warmup']+q
    # Path costs are independent of access addresses at these fixed geometries.
    # Independently compare each materialized measurement to the model scalar;
    # the result is still counted from actual request/response frames above.
    expected=r['expected_periodic_cost']['total']
    assert expected['lower']==expected['upper']=='657456'
    assert r['bytes_per_request']==657456


def summarize(values):
    if len(values)==5:return dict(complete=True,**stats(values))
    return dict(complete=False,n=len(values),mean=statistics.mean(values),ci95=None,
                range=[min(values),max(values)],per_seed=values)


def main():
    plans={};counts={};receipts=[];available={};raw=[];missing=[]
    for name,group in [('formal_tuned_plan.json','tuned'),('formal_classical_reference_plan.json','supplement')]:
        pp=PACKAGE/name;plan=json.loads(pp.read_text());plans[name]=sha(pp)
        specs=plan.get('specs') or [i['spec'] for i in plan['items']];done=0
        assert len(specs)==(50 if group=='tuned' else 10)
        for s in specs:
            p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
            if not p.exists():missing.append(s['id']);continue
            r=json.loads(p.read_text());assert r['status']=='passed' and r['spec']==s
            # Runners atomically replace their base receipt when adding their
            # final execution revision. A base receipt is not yet a final run.
            revision=r.get('execution_revision',{}).get('name')
            if group=='supplement' and revision!='hmac_bulk_exact_v2':
                assert r['source_hashes']==bulk_identity();missing.append(s['id']);continue
            if group=='tuned' and r['source_hashes']==fast_identity() and not revision:
                missing.append(s['id']);continue
            if group=='tuned':audit_run(r,s,False)
            else:audit_supplement(r,s)
            resource=audit_materialized(r);source=dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p))
            receipts.append(source);done+=1
            available[group,s['kind'],s['workload'],s['trace_seed']]=r
            raw.append(dict(group=group,spec=s,configs=r['configs'],bytes_per_request=r['bytes_per_request'],
                rpc_per_request=r['rpc_per_request'],total_bytes=r['phases']['measurement']['total_bytes'],
                components=r['phases']['measurement']['components'],resource=resource,source=source))
        counts[group]=dict(completed=done,expected=len(specs))
    cells=[];by_cell=defaultdict(list)
    for row in raw:by_cell[row['group'],row['spec']['kind'],row['spec']['workload']].append(row)
    for key,rs in sorted(by_cell.items()):
        rs.sort(key=lambda r:r['spec']['trace_seed']);assert len({r['spec']['trace_seed'] for r in rs})==len(rs)
        assert all(r['resource']==rs[0]['resource'] for r in rs)
        cells.append(dict(group=key[0],kind=key[1],workload=key[2],seeds=[r['spec']['trace_seed'] for r in rs],
            bytes_per_request=summarize([r['bytes_per_request'] for r in rs]),
            rpc_per_request=summarize([r['rpc_per_request'] for r in rs]),resource=rs[0]['resource']))
    effects=[]
    for workload in ('uniform','hot90'):
        for group,base,new in [('tuned','path','sde'),('tuned','deferred','sde'),
                               ('tuned','ring','r0'),('supplement','path','sde')]:
            pairs=[]
            for seed in range(101,106):
                a=available.get((group,base,workload,seed));b=available.get(('tuned',new,workload,seed))
                if a is None or b is None:continue
                ignore={'id','kind','profile','R','experiment_class','study'}
                assert {k:v for k,v in a['spec'].items() if k not in ignore}=={k:v for k,v in b['spec'].items() if k not in ignore}
                assert a['trace']==b['trace'] and a['answer_sha256']==b['answer_sha256']
                pairs.append(dict(seed=seed,baseline_id=a['spec']['id'],variant_id=b['spec']['id'],
                    baseline_bytes=a['phases']['measurement']['total_bytes'],variant_bytes=b['phases']['measurement']['total_bytes'],
                    bytes_saving_pct=100*(1-b['bytes_per_request']/a['bytes_per_request']),
                    rpc_saving_pct=100*(1-b['rpc_per_request']/a['rpc_per_request'])))
            if pairs:effects.append(dict(baseline_group=group,baseline=base,variant=new,workload=workload,
                bytes_saving=summarize([p['bytes_saving_pct'] for p in pairs]),
                rpc_saving=summarize([p['rpc_saving_pct'] for p in pairs]),pairs=pairs))
    repeat = any(c['bytes_per_request']['complete'] and statistics.stdev(c['bytes_per_request']['per_seed'])/
                 c['bytes_per_request']['mean']>.1 for c in cells)
    repeat |= any(e['bytes_saving']['complete'] and
                  (e['bytes_saving']['ci95'][1]-e['bytes_saving']['ci95'][0])/2>5 for e in effects)
    final=counts['tuned']['completed']==50 and counts['supplement']['completed']==10
    out=dict(status='all_runs_audited' if final else 'partial_runs_audited',counts=counts,receipts=receipts,
        cells=cells,effects=effects,rows=raw,missing=missing,plan_hashes=plans,repeat_gate_triggered=repeat,
        auditor_sha256=sha(__file__),helper_sha256={n:sha(PACKAGE/'src'/n) for n in (
            'audit_completed_core_components.py','audit_completed_ablation.py','audit_storage_components.py',
            'analyze_ir_dwb.py','run_fast.py','run_bulk_scale.py')},
        full_security_admission=False,full_paper_complete=False)
    save(PACKAGE/'results/tuned_reference_independent_audit.json',out)
    md=['# 调优主比较与经典Path补充对照：独立账单审计','',
        f"主比较已审计{counts['tuned']['completed']}/50，补充对照{counts['supplement']['completed']}/10。未满5个配对种子的组保留实际n，不报告95%最终区间。主比较双方参数分别按预声明有限候选选择；Z5/R258仅为补充，不替换Z4主基线。",'',
        '逐行独立重放输入版本并重算答案摘要，复算分项字节/RPC连续序号、递归时钟、空间对象及trace配对。这里只计应用层序列化通信，未计TCP/TLS，不作延迟改善或完整同安全保证声明。','',
        '| 组别 | 后端 | 负载 | n | 平均bytes/op | 平均RPC/op |','|---|---|---|---:|---:|---:|']
    for c in cells:md.append(f"| {c['group']} | {c['kind']} | {c['workload']} | {c['bytes_per_request']['n']} | {c['bytes_per_request']['mean']:,.2f} | {c['rpc_per_request']['mean']:.4f} |")
    md+=['','| 基线组别 | 比较 | 负载 | 配对n | 平均字节减少 | 95%区间 |','|---|---|---|---:|---:|---|']
    for e in effects:
        v=e['bytes_saving'];ci='待五次完整重复' if not v['complete'] else f"[{v['ci95'][0]:.3f}%, {v['ci95'][1]:.3f}%]"
        md.append(f"| {e['baseline_group']} | {e['baseline']} → {e['variant']} | {e['workload']} | {v['n']} | {v['mean']:.3f}% | {ci} |")
    md+=['',f'当前完整组是否触发预定追加重复门槛：{repeat}。剩余格仍须完成，不能据局部完整组结束全部任务。',
        '', '机器可读逐行与逐种子表见 `results/tuned_reference_independent_audit.json`，每个来源有SHA256。容量/证明口径见45号文档；缓存、XOR及其他参数族尚未穷尽，不作全局最优比较。']
    (PACKAGE/'46_调优与经典对照独立结果.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=out['status'],counts=counts,effects=len(effects),repeat_gate_triggered=repeat)),flush=True)


if __name__=='__main__':main()
