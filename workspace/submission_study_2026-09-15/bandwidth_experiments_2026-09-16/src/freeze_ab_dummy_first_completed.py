"""Complete conditional AB-CB data, preserving GC-Ring as a strong control."""
from common import *
from collections import defaultdict
import math
import statistics
from audit_ab_dummy_first import inputs,audit_record,matched


def stats(xs):
    assert len(xs)==5
    m=sum(xs)/5;half=2.7764451051977987*math.sqrt(sum((x-m)**2 for x in xs)/20)
    return dict(n=5,mean=m,ci95=[m-half,m+half],values=xs)


def resource(r):
    p=r['frontend_memory_representation'];f=p['plb']
    selected=dict(tree_cache=r['cache_representation']['bytes'],stash_payload=f['stash_reserved_bytes'],
        plb_payload=f['plb_payload_bytes'],plb_leaf_address=f['plb_leaf_and_address_bytes'],
        terminal_leaf=f['terminal_leaf_bytes'],llc_payload=p['llc_payload_capacity'])
    return dict(server=r['server_storage'],selected_client=selected,selected_client_sum=sum(selected.values()),
        full_private_posmap_present=f['full_private_posmap_present'],actual_peak=False)


def main():
    plan,kw=inputs();pp=PACKAGE/'ab_dummy_first_periodic_plan.json'
    cp=PACKAGE/'results/ab_dummy_first_periodic_queue_completion.json';completion=json.loads(cp.read_text())
    assert completion['status']=='passed' and len(completion['rows'])==60 and completion['plan_sha256']==sha(pp)
    done={r['id']:r for r in completion['rows']};records={};receipts=[];groups=defaultdict(list)
    for s in plan['specs']:
        path=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        assert not (PACKAGE/'results/failures'/path.name).exists()
        r=json.loads(path.read_text());audit_record(r,s,**kw)
        assert done[s['id']]['receipt_sha256']==sha(path) and done[s['id']]['bytes_per_request']==r['bytes_per_request']
        m=r['phases']['measurement'];bill=m['bills'][0]
        assert sum(bill['components'].values())==sum(sum(v.values()) for v in bill['by_stage'].values())==m['total_bytes']
        for k,value in bill['components'].items():assert sum(stage.get(k,0) for stage in bill['by_stage'].values())==value
        records[s['id']]=r;receipts.append(dict(id=s['id'],path=str(path.relative_to(PACKAGE)),sha256=sha(path)))
        layout='D3' if s['bottom_dummy'] is None else 'bottom_D0'
        groups[layout,s['workload'],s['kind']].append(r)
    assert len(records)==60 and len(groups)==12
    cells=[]
    for (layout,workload,kind),rs in sorted(groups.items()):
        rs.sort(key=lambda r:r['spec']['trace_seed']);assert [r['spec']['trace_seed'] for r in rs]==list(range(101,106))
        ms=[r['phases']['measurement'] for r in rs];res=[resource(r) for r in rs];assert all(x==res[0] for x in res)
        components={k:stats([m['bills'][0]['components'].get(k,0)/m['requests'] for m in ms]) for k in sorted({k for m in ms for k in m['bills'][0]['components']})}
        stages={stage:stats([sum(m['bills'][0]['by_stage'].get(stage,{}).values())/m['requests'] for m in ms]) for stage in sorted({k for m in ms for k in m['bills'][0]['by_stage']})}
        front={k:stats([m['frontend_metrics'].get(k,0) for m in ms]) for k in sorted({k for m in ms for k in m['frontend_metrics']})}
        cb={k:stats([m['cb_metrics'].get(k,0) for m in ms]) for k in sorted({k for m in ms for k in m['cb_metrics']})}
        hist=[{int(k):v for k,v in m['boundary_stash_histogram'].items()} for m in ms]
        cells.append(dict(layout=layout,workload=workload,kind=kind,ids=[r['spec']['id'] for r in rs],
            bytes=stats([m['total_bytes']/m['requests'] for m in ms]),rpc=stats([m['rpc']/m['requests'] for m in ms]),
            components=components,stages=stages,frontend=front,cb=cb,resource=res[0],
            observed_boundary_stash_max=[max(h) for h in hist],
            observed_boundary_stash_mean=stats([sum(k*v for k,v in h.items())/sum(h.values()) for h in hist])))
    effects=[]
    cases=[('backend',layout,workload,base,var) for layout in ('D3','bottom_D0') for workload in ('uniform','hot90') for base,var in (('ring','gc_ring'),('ring','r0'),('gc_ring','r0'))]
    cases += [('layout',kind,workload,'D3','bottom_D0') for kind in ('ring','gc_ring','r0') for workload in ('uniform','hot90')]
    for axis,condition,workload,base,var in cases:
        keys=[(condition,workload,k) if axis=='backend' else (k,workload,condition) for k in (base,var)]
        left,right=[groups[k] for k in keys];pairs=[]
        for l,r in zip(left,right):
            matched(l,r,axis);assert l['spec']['trace_seed']==r['spec']['trace_seed']
            x,y=[z['phases']['measurement']['total_bytes']/z['spec']['requests'] for z in (l,r)]
            ml,mr=[z['phases']['measurement'] for z in (l,r)]
            parts={k:(ml['bills'][0]['components'].get(k,0)-mr['bills'][0]['components'].get(k,0))/ml['requests'] for k in sorted(set(ml['bills'][0]['components'])|set(mr['bills'][0]['components']))}
            assert math.isclose(sum(parts.values()),x-y,abs_tol=1e-9)
            pairs.append(dict(seed=l['spec']['trace_seed'],baseline_id=l['spec']['id'],variant_id=r['spec']['id'],
                baseline_bytes=x,variant_bytes=y,saving_pct=100*(1-y/x),component_saved_bytes=parts,
                rpc_saving_pct=100*(1-mr['rpc']/ml['rpc'])))
        st=stats([p['saving_pct'] for p in pairs]);cvs=[statistics.stdev(p[k] for p in pairs)/statistics.mean(p[k] for p in pairs) for k in ('baseline_bytes','variant_bytes')]
        effects.append(dict(axis=axis,condition=condition,workload=workload,baseline=base,variant=var,
            paired_saving_pct=st,paired_rpc_saving_pct=stats([p['rpc_saving_pct'] for p in pairs]),
            baseline_mean=statistics.mean(p['baseline_bytes'] for p in pairs),variant_mean=statistics.mean(p['variant_bytes'] for p in pairs),
            component_saved_bytes={k:stats([p['component_saved_bytes'][k] for p in pairs]) for k in pairs[0]['component_saved_bytes']},
            pairs=pairs,run_cost_cv=cvs,needs_more_repeats=max(cvs)>.10 or (st['ci95'][1]-st['ci95'][0])/2>5))
    proof_paths=[PACKAGE/'results'/n for n in ('ab_dummy_first_checks.json','ab_dummy_first_frontend_checks.json','ab_dummy_first_periodic_checks.json','ab_dummy_first_controlled_checks.json')]
    out=dict(status='complete_conditional_batch_audited',runs=60,cells=cells,effects=effects,receipts=receipts,
        plan_sha256=sha(pp),queue_completion_sha256=sha(cp),producer_sha256=sha(__file__),source_hashes=kw['source'],
        proof_hashes={str(p.relative_to(PACKAGE)):sha(p) for p in proof_paths},
        helper_hashes={n:sha(Path(__file__).parent/n) for n in ('audit_ab_dummy_first.py','audit_ab_cb.py')},
        additional_repeat_groups=[{k:e[k] for k in ('axis','condition','workload','baseline','variant')} for e in effects if e['needs_more_repeats']],
        security_admission=False,native_AB=False,DeadQ=False,true_client_peak_measured=False,latency_claim=False,
        scope=plan['scope'],endpoint=plan['endpoint'])
    target=PACKAGE/'results/ab_dummy_first_completed_snapshot.json'
    if target.exists():assert json.loads(target.read_text())==out,'completed snapshot is immutable'
    else:save(target,out)
    md=['# AB-CB条件协议：完整60次通信结果','',
        '预声明的60次运行全部完成，12格各五个种子，18组配对比较；当前批次没有运行失败。此前加载失败、策略诊断与试运行均保留，不混入本批均值。完整重复不等于安全闭合：本批没有DeadQ或green容量证明，不声称原生AB复现。','',
        '## 方法与公平对照','',
        'N4096/B64，raw递归后4369记录，L11/C5/A5/Y4/R500；上六层缓存、PLB8、LLC8组×2路、压力H48/L32。均匀D3的τ为7，底三层D0的τ为4；其余条件不变。Ring+CB、GC-Ring+CB与R0+CB同时比较，不省略GC-Ring这一强对照。','',
        '初始化按每A槽接纳一个记录，共21845 Transfer；8875槽对齐至30720后暖机10240槽/640请求，测量40960槽/2560请求（四个维护周期），终点t81920。所有阶段分开计费，最终dirty LLC可驻留，不补不计费drain；完整周期不自动代表稳态。','',
        '线上、空闲及后台Transfer均优先未读dummy，不足时允许green。背景压力与应用输入相同，但后端状态可导致不同background/dummy时刻，因此只要求有用迁移序列及前端工作量相同，不强迫填充后的全部schedule hash一致。','',
        '## 绝对开销与资源','',
        '| 布局 / 负载 | 后端 | bytes/request | RPC/request | 服务器对象MiB | 已列客户端KiB | 观测完成态stash最大值 |',
        '|---|---|---:|---:|---:|---:|---:|']
    for c in cells:
        res=c['resource'];md.append(f"| {c['layout']} / {c['workload']} | {c['kind']} | {c['bytes']['mean']:,.2f} | {c['rpc']['mean']:.4f} | {res['server']['total_bytes']/(1<<20):.6f} | {res['selected_client_sum']/1024:.3f} | {max(c['observed_boundary_stash_max'])} |")
    md+=['','已列客户端包含树顶缓存对象、stash payload预留、PLB payload与叶/地址、terminal leaf及LLC payload；不含全部并存解密、加密、写回和认证scratch，也不含Python容器。观测stash最大值不是概率尾界，不能代替R500的安全容量证明。','',
        '## 配对收益','',
        '| 因素 | 条件 / 负载 | 比较 | 通信减少 | 95%区间 | RPC减少 |','|---|---|---|---:|---|---:|']
    for e in effects:
        x=e['paired_saving_pct'];lo,hi=x['ci95'];md.append(f"| {e['axis']} | {e['condition']} / {e['workload']} | {e['baseline']} → {e['variant']} | {x['mean']:.4f}% | [{lo:.4f}, {hi:.4f}]% | {e['paired_rpc_saving_pct']['mean']:.4f}% |")
    md+=['','先对相同种子计算1−新/旧，再报五对均值和95% Student-t区间。负值及包含零的区间保留。布局比较改变服务器dummy空间，其收益不能与后端减少率直接相加。','',
        f"触发预声明追加重复门槛（任一成本CV>10%或减少率区间半宽>5个百分点）的组数：{len(out['additional_repeat_groups'])}。",'',
        '## 收益来自哪里','',
        'Ring→GC-Ring与Ring→R0的收益近似，而GC-Ring→R0新增字节变化接近零。根桶已处于可信前缀缓存，省根不能再次减少它的远程通信；剩余小差异包含独立后端随机序列引起的有限窗口波动。不得把相对Ring的全部收益归于超越GC-Ring的新贡献。','',
        '| 布局 / 负载 | Ring→GC：数据下载节省B/请求 | 数据上传 | 桶头合计 | 认证合计 | 控制 | 总节省B/请求 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for e in effects:
        if not(e['axis']=='backend' and e['baseline']=='ring' and e['variant']=='gc_ring'):continue
        p=e['component_saved_bytes'];value=lambda k:p[k]['mean']
        values=[value('data_download'),value('data_upload'),value('headers_download')+value('headers_upload'),
            value('authentication_download')+value('authentication_upload'),value('framing_and_control'),e['baseline_mean']-e['variant_mean']]
        md.append(f"| {e['condition']} / {e['workload']} | "+' | '.join(f'{v:,.3f}' for v in values)+' |')
    md+=['','上表是逐项平均绝对字节差，包含负项；各项可加为总字节差。它与“逐种子相对节省的均值”是不同统计口径，不把均值的比值冒充配对均值。完整logical/evict阶段和green/neutral计数在冻结JSON每格中保留。','',
        '## 审计与使用边界','',
        '每份原始记录重新核对输入、返回值摘要、源代码、初始化/对齐/递归时钟、RPC顺序和全部阶段账单；所有分项按操作阶段守恒。完成队列的60个收据hash逐一匹配，12格资源按深度重算的已有独立审计也通过。结果绑定固定计划、受控检查和实现身份。','',
        '本批结果可写为“已实现的、无DeadQ的AB-CB适配在给定公开时隙策略下的条件通信结果”。不能写成完整AB的普遍收益、green尾界、原生strict-dummy后台或自适应安全证明。54号认证DeadQ层尚未接入本批协议，其元数据成本也未包含在这里。','',
        '复现入口：`src/freeze_ab_dummy_first_completed.py`；完整12格、18组效应、60份来源及分项数据为`results/ab_dummy_first_completed_snapshot.json`。已有原始CSV为`tables/AB_CB_dummy_first_periodic_runs.csv`，31号动态报告保留。']
    (PACKAGE/'56_AB_CB完整结果与强基线.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=out['status'],runs=60,cells=12,effects=18,repeat_groups=len(out['additional_repeat_groups']))))


if __name__=='__main__':main()
