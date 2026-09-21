"""Retain all declared cells; only full paired groups get performance means."""
from common import *
from collections import defaultdict
import statistics,math
from dispatch_ir_guarded import validate
from audit_ir_guarded_periodic import audit_record


def stats(values):
    n=len(values);assert n in (5,10)
    mean=statistics.mean(values);half=(2.7764451051977987 if n==5 else 2.262157162798205)*statistics.stdev(values)/math.sqrt(n)
    return dict(n=n,mean=mean,ci95=[mean-half,mean+half],values=values)


def main():
    pp=PACKAGE/'formal_ir_guarded_plan.json';plan=json.loads(pp.read_text());validate(plan)
    target=PACKAGE/'results/ir_guarded_target_checks.json';pilots=[]
    if target.exists():
        gate=json.loads(target.read_text());assert gate['status']=='passed' and gate['plan_sha256']==sha(pp)
        assert len(gate['cases'])==len(plan['pilots'])==2
        for ref,s in zip(gate['cases'],plan['pilots']):
            p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];r=json.loads(p.read_text())
            assert audit_record(r,s)==ref['audit']
            pilots.append(dict(id=s['id'],beta=s['beta'],path=ref['path'],sha256=ref['sha256'],
                reset_slots=ref['audit']['measurement_reset_slots'],guard_bytes=ref['audit']['measurement_guard_bytes']))
    records={};receipts=[];missing=[];failed=[];groups=defaultdict(list)
    for s in plan['specs']:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json";f=PACKAGE/'results/failures'/f"{s['id']}.json"
        groups[s['beta'],s['kind']].append(s)
        if not p.exists():
            if f.exists():failed.append(dict(id=s['id'],path=str(f.relative_to(PACKAGE)),sha256=sha(f)))
            else:missing.append(s['id'])
            continue
        assert not f.exists(),'both success and failure require manual provenance review'
        r=json.loads(p.read_text());audit=audit_record(r,s);records[s['id']]=r
        receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p),audit=audit))
    cells=[]
    for (beta,kind),specs in sorted(groups.items()):
        rs=[records[s['id']] for s in specs if s['id'] in records]
        cell=dict(beta=beta,kind=kind,completed=len(rs),expected=5,performance_eligible=len(rs)==5)
        if len(rs)==5:
            rs.sort(key=lambda r:r['spec']['trace_seed']);ms=[r['phases']['measurement'] for r in rs]
            cell.update(ids=[r['spec']['id'] for r in rs],bytes=stats([r['bytes_per_request'] for r in rs]),
                rpc=stats([r['rpc_per_request'] for r in rs]),
                guard_bytes_per_request=stats([p['guard_bytes']/p['requests'] for p in ms]),
                reset_slots=stats([p['frontend_metrics']['group_reset_slots'] for p in ms]),
                dummy_slots=stats([p['frontend_metrics'].get('dummy_slots',0) for p in ms]),
                completed_at_original_cut=[p['original_cut']['completed'] for p in ms],
                tail_slots_to_clear=[p['tail_slots_to_clear'] for p in ms])
        cells.append(cell)
    by={(s['beta'],s['kind'],s['trace_seed']):s['id'] for s in plan['specs']}
    designs=[]
    for beta in (14,4):
        for kind in ('path','deferred'):designs.append(('backend',beta,kind,beta,'sde'))
    for kind in ('path','deferred','sde'):designs.append(('beta',14,kind,4,kind))
    effects=[];pending=[]
    for axis,beta0,kind0,beta1,kind1 in designs:
        meta=dict(axis=axis,before_beta=beta0,baseline=kind0,after_beta=beta1,variant=kind1)
        ids=[(by[beta0,kind0,seed],by[beta1,kind1,seed]) for seed in range(101,106)]
        if not all(a in records and b in records for a,b in ids):
            pending.append(dict(meta,pairs=ids,reason='all five pairs required; no survivor-only means'));continue
        pairs=[]
        for left,right in ids:
            a,b=records[left],records[right]
            assert a['trace']==b['trace'] and a['answer_sha256']==b['answer_sha256']
            for phase in ('warmup','measurement'):
                aa,bb=a['phases'][phase],b['phases'][phase]
                for key in ('requests','public_slots','guard_slots','start_t','end_t'):assert aa[key]==bb[key]
                if axis=='backend':
                    for key in ('frontend_metrics','map_metrics','schedules','reset_start','reset_end'):assert aa[key]==bb[key]
                elif kind0 in ('path','deferred'):assert aa['total_bytes']==bb['total_bytes']
            pairs.append(dict(seed=a['spec']['trace_seed'],baseline_id=left,variant_id=right,
                baseline_bytes=a['bytes_per_request'],variant_bytes=b['bytes_per_request'],
                saving_pct=100*(1-b['bytes_per_request']/a['bytes_per_request'])))
        effect=stats([x['saving_pct'] for x in pairs])
        cvs=[statistics.stdev(x[k] for x in pairs)/statistics.mean(x[k] for x in pairs) for k in ('baseline_bytes','variant_bytes')]
        effects.append(dict(meta,pairs=pairs,effect=effect,run_cost_cv=cvs,
            needs_more_repeats=max(cvs)>.1 or (effect['ci95'][1]-effect['ci95'][0])/2>5))
    out=dict(status='complete_receipts_audited' if len(records)==30 else 'partial_receipts_audited',
        completed=len(records),expected=30,missing=missing,failed=failed,receipts=receipts,cells=cells,effects=effects,pending_comparisons=pending,
        plan_sha256=sha(pp),auditor_sha256=sha(__file__),additional_repeat_groups=[e for e in effects if e['needs_more_repeats']],
        target_checks_sha256=sha(target) if target.exists() else None,target_pilots=pilots,
        original_75_outcomes_replaced=False,native_IR=False,actual_peak_measured=False,latency_claim=False)
    save(PACKAGE/'results/ir_guarded_statistics.json',out)
    md=['# IR公开尾部补充实验：实际账单与进度','',
        f"已审计完成{len(records)}/30，具名失败{len(failed)}；所有六格及七组比较均保留。只有五对全部完成的比较报告性能。准备、原始失败及改变窗口的理由见60号报告。",'',
        f"目标规模预试验通过{len(pilots)}/2；预试验使用独立seed901/1901，不进入正式均值。",'',
        '新窗口每阶段额外执行12288个公开槽，测量61440槽/6144请求，初始化及暖机另记；这些尾部槽不是免费drain。原75个观测不覆盖。该批没有IR-Stash/PMMAC，不构成完整原生IR安全或延迟结果。','',
        '| β / 后端 | 完成数 | bytes/请求 | RPC/请求 | 其中尾部bytes/请求 | 测量reset槽均值 |','|---|---:|---:|---:|---:|---:|']
    for c in cells:
        if not c['performance_eligible']:
            md.append(f"| {c['beta']} / {c['kind']} | {c['completed']}/5 | 待完整 | — | — | — |");continue
        md.append(f"| {c['beta']} / {c['kind']} | 5/5 | {c['bytes']['mean']:,.3f} | {c['rpc']['mean']:.4f} | {c['guard_bytes_per_request']['mean']:,.3f} | {c['reset_slots']['mean']:.1f} |")
    md+=['','| 因素 | 对照 → 新配置 | 通信减少 | 95%配对区间 |','|---|---|---:|---|']
    for e in effects:
        x=e['effect'];lo,hi=x['ci95'];md.append(f"| {e['axis']} | β{e['before_beta']}/{e['baseline']} → β{e['after_beta']}/{e['variant']} | {x['mean']:.4f}% | [{lo:.4f}, {hi:.4f}]% |")
    if not effects:md.append('| 尚无完整五对 | — | — | — |')
    md+=['','负值、含零区间、失败及触发追加重复门槛的组都保留；不同公开窗口之间不能归因于selective本身。完整原始来源、尾部完成数、资源及分项账单在JSON和每次收据中。']
    (PACKAGE/'61_IR公开尾部补充实验进度.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=len(records),expected=30,effects=len(effects),failed=len(failed))))


if __name__=='__main__':main()
