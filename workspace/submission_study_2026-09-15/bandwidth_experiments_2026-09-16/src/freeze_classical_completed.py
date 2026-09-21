"""Freeze completed Path Z5 supplement alongside the stronger Path Z4 control."""
from common import *
import math,statistics
from audit_tuned_reference import audit_supplement
from audit_completed_core_components import audit_run
from audit_storage_components import audit_materialized


def stats(xs):
    assert len(xs)==5
    m=sum(xs)/5;h=2.7764451051977987*math.sqrt(sum((x-m)**2 for x in xs)/20)
    return dict(n=5,mean=m,ci95=[m-h,m+h],per_seed=xs)


def main():
    p=PACKAGE/'results/tuned_reference_independent_audit.json';a=json.loads(p.read_text(encoding='utf-8'))
    assert a['status']=='all_runs_audited' and not a['repeat_gate_triggered']
    assert a['counts']['supplement']==dict(completed=10,expected=10)
    assert a['auditor_sha256']==sha(Path(__file__).parent/'audit_tuned_reference.py')
    for name,value in a['helper_sha256'].items():assert sha(Path(__file__).parent/name)==value
    q=PACKAGE/'results/classical_reference_queue_bulk_completion.json';completion=json.loads(q.read_text(encoding='utf-8'))
    assert completion['status']=='passed' and len(completion['rows'])==10
    assert completion['queue_sha256']==sha(PACKAGE/'classical_reference_queue.json')
    rows=[r for r in a['rows'] if r['group']=='supplement' or r['group']=='tuned' and r['spec']['kind'] in ('path','sde')]
    assert len(rows)==30
    raw={};sources=[]
    for row in rows:
        source=row['source'];rp=PACKAGE/source['path'];assert sha(rp)==source['sha256']
        r=json.loads(rp.read_text(encoding='utf-8'));s=row['spec']
        if row['group']=='supplement':audit_supplement(r,s)
        else:audit_run(r,s,False)
        assert audit_materialized(r)==row['resource']
        label='Path Z5' if row['group']=='supplement' else ('Path Z4' if s['kind']=='path' else 'SDE')
        raw[label,s['workload'],s['trace_seed']]=r;sources.append(source)
    effects=[];cells=[]
    for workload in ('uniform','hot90'):
        for label in ('Path Z4','Path Z5','SDE'):
            group=[raw[label,workload,i] for i in range(101,106)]
            rs=[audit_materialized(r) for r in group];assert all(r==rs[0] for r in rs)
            cells.append(dict(label=label,workload=workload,profile=group[0]['spec']['profile'],R=group[0]['spec']['R'],
                bytes=stats([r['phases']['measurement']['total_bytes']/4096 for r in group]),
                rpc=stats([r['phases']['measurement']['rpc']/4096 for r in group]),
                resource=rs[0],ids=[r['spec']['id'] for r in group]))
        for base,var in (('Path Z4','SDE'),('Path Z5','SDE'),('Path Z4','Path Z5')):
            pairs=[]
            for seed in range(101,106):
                l,r=raw[base,workload,seed],raw[var,workload,seed]
                assert l['trace']==r['trace'] and l['answer_sha256']==r['answer_sha256']
                ignored={'id','kind','profile','R','experiment_class','study'}
                assert {k:v for k,v in l['spec'].items() if k not in ignored}=={k:v for k,v in r['spec'].items() if k not in ignored}
                x,y=[z['phases']['measurement']['total_bytes']/4096 for z in (l,r)]
                pairs.append(dict(seed=seed,baseline_id=l['spec']['id'],variant_id=r['spec']['id'],
                    baseline_bytes=x,variant_bytes=y,saving_pct=100*(1-y/x)))
            effect=stats([x['saving_pct'] for x in pairs])
            cvs=[statistics.stdev([x[k] for x in pairs])/statistics.mean(x[k] for x in pairs) for k in ('baseline_bytes','variant_bytes')]
            effects.append(dict(baseline=base,variant=var,workload=workload,bytes_saving=effect,pairs=pairs,
                run_cost_cv=cvs,needs_more_repeats=max(cvs)>.10 or (effect['ci95'][1]-effect['ci95'][0])/2>5))
    assert not any(e['needs_more_repeats'] for e in effects)
    proof_names=('classical_reference_evidence_audit.json','classical_stash_execution_ledger.json','classical_stash_execution_ledger_audit.json')
    proof_hashes={name:sha(PACKAGE/'results'/name) for name in proof_names}
    proof=json.loads((PACKAGE/'results/classical_reference_evidence_audit.json').read_text(encoding='utf-8'))
    assert proof['status']=='evidence_consistent' and not proof['full_security_admission']
    out=dict(status='passed',new_runs=10,reused_controls=20,runs=30,cells=cells,effects=effects,receipts=sources,
        source_identity=source_identity(),producer_sha256=sha(__file__),helper_hashes=a['helper_sha256'],
        upstream_sha256=sha(p),queue_completion_sha256=sha(q),proof_hashes=proof_hashes,
        plan_hashes={name:sha(PACKAGE/name) for name in ('formal_tuned_plan.json','formal_classical_reference_plan.json')},
        full_security_admission=False,true_client_peak_measured=False,latency_claim=False,
        replaces_main_Path_Z4=False,scope='supplementary fixed-history classical stash-bound reference; stronger empirical Z4 retained')
    target=PACKAGE/'results/classical_completed_snapshot.json'
    if target.exists():assert json.loads(target.read_text(encoding='utf-8'))==out,'completed snapshot is immutable'
    else:save(target,out)
    md=['# 经典Path补充对照：完整重复与主基线并列','',
        '补充Path Z5/R258的10次新运行全部完成。与已有Path Z4/R256、SDE Z4/A3/R256各10次复用对照组成30份固定来源；每格五个相同输入种子。原Path Z4主基线及47号主图保留，不用更贵的Z5替换。','',
        'N16384、数据块4096B、位置表块256B，终端map上限8192B；完整初始化后暖机2048请求、测量4096请求。统计实际双向应用协议字节，包含认证与递归；不计TCP/TLS，不作延迟主张。','',
        '| 方案 | 负载 | Z/A/S | R | bytes/op | RPC/op | 服务器对象MiB | stash payload＋terminal KiB |',
        '|---|---|---|---:|---:|---:|---:|---:|']
    for c in cells:
        r=c['resource'];client=(r['reserved_stash_payload_bytes']+(r['terminal_map_bytes'] or 0))/1024
        md.append(f"| {c['label']} | {c['workload']} | {'/'.join(map(str,c['profile']))} | {c['R']} | {c['bytes']['mean']:,.2f} | {c['rpc']['mean']:.4f} | {r['remote_bytes']/(1<<20):.6f} | {client:.3f} |")
    md+=['','Path列中的A/S为配置占位；Path本身每次随机路径读写，不使用scheduled A周期或Ring dummy阈值。上表已列客户端项不是完整可信峰值。','',
        '| 比较 | 负载 | 配对减少率 | 95%区间 |','|---|---|---:|---|']
    for e in effects:
        s=e['bytes_saving'];lo,hi=s['ci95']
        md.append(f"| {e['baseline']} → {e['variant']} | {e['workload']} | {s['mean']:.3f}% | [{lo:.3f}, {hi:.3f}]% |")
    md+=['','减少率为1−新/旧；Path Z4→Z5的负值表示补充参照更贵，不能作为优化效果。Path Z5的657456 bytes/op在每个实际运行中均由分项账单测得，并与其确定性模型相等，不以模型数字替代实测。','',
        'SDE相对Z5补充参照约48.45%的节省，不能替换相对Z4主基线约35.77%的正文主张。两种分母与参数均保留。追加重复门槛未触发。','',
        '## 安全与公平性边界','',
        'Z5/R258补充的依据是45号账本在既定初始化、固定访问历史、理想独立叶及2^56应用寿命下的经典stash表达式和2^-130预算。它不等于整个实现的主动安全证明；公开寿命执行、PRF/取模预算和完整可信峰值仍须补齐。Path Z4为经验强基线，不能借用Z5定理。',
        '两者使用同样trace、块长、递归配置和测量窗口，但Z与R不同，因此是明确参数下的补充参照，不称完全相同资源/同保证比较。有限候选没有穷尽缓存、XOR或全部参数，不作全局最优主张。',
        '逐份重新核对返回摘要、账单/RPC、递归时钟和对象存储；完整30份来源、六格、六组配对及证明账本哈希在 `results/classical_completed_snapshot.json`。C1队列已终止成功，无需重启；之前B3主图不重复导出。']
    (PACKAGE/'53_经典Path补充完整结果.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',new_runs=10,reused=20,cells=6,effects=6,
        supplement_savings=[e['bytes_saving']['mean'] for e in effects if e['baseline']=='Path Z5'])))


if __name__=='__main__':main()
