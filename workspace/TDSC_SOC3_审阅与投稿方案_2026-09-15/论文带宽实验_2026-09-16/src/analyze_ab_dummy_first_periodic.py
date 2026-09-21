"""Conditional CB bandwidth estimates; preserve the missing security admission."""
from common import *
from collections import defaultdict
import statistics,csv,argparse
from audit_ab_dummy_first import inputs,audit_record,matched
from analyze_ablation import summary


def main():
    args=argparse.Namespace(paced=True)
    prefix='ab_dummy_first_periodic';plan_name=prefix+'_plan.json'
    plan,kwargs=inputs(plan_name);rows=[];receipts=[];missing=[];failures=[]
    for s in plan['specs']:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        if not p.exists():
            missing.append(s['id']);failure=PACKAGE/'results/failures'/f"{s['id']}.json"
            if failure.exists():
                f=json.loads(failure.read_text());assert f['spec']==s and f['source_hashes']==kwargs['source']
                failures.append(dict(id=s['id'],path=str(failure.relative_to(PACKAGE)),sha256=sha(failure),error=f['error']))
            continue
        r=json.loads(p.read_text());audit_record(r,s,**kwargs);rows.append(r)
        receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    groups=defaultdict(list)
    for r in rows:
        s=r['spec'];groups['backend',s['bottom_dummy'],s['workload']].append(r)
        groups['layout',s['kind'],s['workload']].append(r)
    effects=[]
    for (axis,condition,workload),rs in groups.items():
        field='kind' if axis=='backend' else 'bottom_dummy'
        pairs=[('ring','gc_ring'),('ring','r0'),('gc_ring','r0')] if axis=='backend' else [(None,0)]
        for before,after in pairs:
            left={r['spec']['trace_seed']:r for r in rs if r['spec'][field]==before}
            right={r['spec']['trace_seed']:r for r in rs if r['spec'][field]==after}
            seeds=sorted(left.keys()&right.keys());details=[]
            if not seeds:continue
            for seed in seeds:
                a,b=left[seed],right[seed];matched(a,b,axis)
                details.append(dict(seed=seed,baseline_id=a['spec']['id'],variant_id=b['spec']['id'],baseline_bytes=a['bytes_per_request'],
                    variant_bytes=b['bytes_per_request'],saving_pct=100*(1-b['bytes_per_request']/a['bytes_per_request']),
                    baseline_background_slots=a['phases']['measurement']['frontend_metrics'].get('background_slots',0),
                    variant_background_slots=b['phases']['measurement']['frontend_metrics'].get('background_slots',0)))
            stat=summary([d['saving_pct'] for d in details]);cvs=[]
            for side in (left,right):
                vals=[side[s]['bytes_per_request'] for s in seeds]
                cvs.append(statistics.stdev(vals)/statistics.mean(vals) if len(vals)>1 else None)
            repeat=None if len(seeds)<5 else max(cvs)>.10 or (stat['ci95'][1]-stat['ci95'][0])/2>5
            effects.append(dict(axis=axis,condition=condition,workload=workload,before=before,after=after,effect=stat,
                baseline_mean_bytes=statistics.mean(d['baseline_bytes'] for d in details),variant_mean_bytes=statistics.mean(d['variant_bytes'] for d in details),
                run_cost_cv=cvs,needs_more_repeats=repeat,per_seed=details))
    out=dict(status='stopped_after_failure' if failures else ('complete_conditional_batch_audited' if not missing else 'partial_conditional_batch_audited'),completed=len(rows),expected=60,
        missing=missing,failures=failures,receipts=receipts,effects=effects,plan_sha256=sha(PACKAGE/plan_name),auditor_sha256=sha(Path(__file__).parent/'audit_ab_dummy_first.py'),base_auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py'),
        analyzer_sha256=sha(__file__),security_admission=False,native_full_AB=False,deadq_implemented=False,latency_claim=False,
        scope=plan['scope'],endpoint=plan['endpoint'])
    save(PACKAGE/'results'/f'{prefix}_statistics.json',out)
    table_name='AB_CB_dummy_first_periodic_runs.csv' if args.paced else 'AB_CB_periodic_runs.csv'
    if rows:
        raw=[]
        for r,receipt in zip(rows,receipts):
            s=r['spec'];p=r['phases']['measurement'];h={int(k):v for k,v in p['boundary_stash_histogram'].items()}
            raw.append(dict(id=s['id'],kind=s['kind'],bottom_dummy=s['bottom_dummy'],workload=s['workload'],seed=s['trace_seed'],
                bytes_per_request=r['bytes_per_request'],rpc_per_request=r['rpc_per_request'],public_slots=p['public_slots'],requests=p['requests'],
                background_slots=p['frontend_metrics'].get('background_slots',0),green_promotions=p['cb_metrics'].get('green_promotions',0),
                boundary_stash_max=max(h),boundary_stash_mean=sum(k*v for k,v in h.items())/p['public_slots'],
                server_serialized_bytes=r['server_storage']['total_bytes'],source_path=receipt['path'],source_sha256=receipt['sha256']))
        with (PACKAGE/'tables'/table_name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)
    md=['# AB-CB完整周期通信复核（条件实验，未获安全准入）','',f'已审计 {len(rows)}/60 个具名运行；每格计划5次。n<5只作过程记录，不给置信区间。','',
        'N4096/B64，raw map后4369记录，L11，C5/A5/Y4/R500；均匀D3/τ7与底三层D0/τ4。前6层缓存、PLB8、LLC8×2，所有后端采用H48/L32。',
        '初始化后5871个公共时隙单独对齐，暖机640请求/10240时隙，测量2560请求/40960时隙，覆盖1+4个完整维护周期。完整周期不等于稳态；终点允许dirty LLC驻留。',
        '比较Ring+CB、GC-Ring+CB与R0+CB；每对保持输入、几何、缓存与内存预算、应用请求数及公共时隙相同。全部在线、空闲与后台Transfer均优先未读dummy，必要时green；尚非严格dummy后台。',
        '**尚无green容量证书、自适应安全证明或DeadQ。即使重复齐全，也只能支持该实验协议的条件带宽结论，不能称完整原生AB结果。**','',
        '| 因素 | 条件 | 负载 | 比较 | n | 基线 bytes/op | 变体 bytes/op | 减少 | 95%区间 |',
        '|---|---|---|---|---:|---:|---:|---:|---|']
    if args.paced:
        md[0]='# AB-CB完整周期通信复核：优先dummy选择修订（条件实验）'
        md[5]='初始化采用每A槽接纳一个记录：4369记录、21845 Transfer时隙，全部setup单列计费；随后8875槽对齐至30720，暖机10240槽，测量40960槽，最终t=81920。终点允许dirty LLC驻留。'
        md[6]+=' 旧连续加载失败保留，新ID不覆盖旧计划。六组目标规模受控数据检查及六组小域时钟检查均为启动前置条件。'
    for e in effects:
        stat=e['effect'];ci=stat['ci95'];interval='待5次' if ci is None else f'[{ci[0]:.3f}%, {ci[1]:.3f}%]'
        condition=('均匀D3' if e['condition'] is None else '底三层D0') if e['axis']=='backend' else e['condition']
        comparison=f"{e['before']} → {e['after']}" if e['axis']=='backend' else '均匀D3 → 底三层D0'
        md.append(f"| {e['axis']} | {condition} | {e['workload']} | {comparison} | {stat['n']} | {e['baseline_mean_bytes']:,.2f} | {e['variant_mean_bytes']:,.2f} | {stat['mean']:.3f}% | {interval} |")
    md+=['',f'首个成功运行后生成原始表 `tables/{table_name}`；完整收据链和配对细节在 `results/{prefix}_statistics.json`。未完成时只导出已有行，不补齐虚拟样本。',
        '若任一组95%区间半宽超过5个百分点，或任一方运行成本CV超过10%，整组追加至10次；负收益也保留。',
        '状态与安全边界独立记录：成功运行、正确返回值、账单守恒、完整周期和五次重复均不能替代安全证明。']
    if failures and not args.paced:
        md+=['','## 已记录的失败：批次停止','',
            '首个Ring+CB/N4096/R500配置在GeometryFront初始化的连续admit过程中发生transfer boundary stash溢出，尚未进入周期对齐、暖机或测量。后台Controller在前端构造结束后才创建，因此原H48/L32不保护初始化。',
            '旧计划、执行驱动、日志与失败收据均保留。不能把这次失败删去、增加R后覆盖原样本，或只继续成功后端。正在独立验证相同R/N/几何下、所有后端一致的公开加载节拍：每A个槽位接纳一个初始记录，其余为实际计费dummy。该修订尚未作为新主批次启动，也不提供容量保证。']
        for f in failures:md.append(f"- `{f['id']}`：`{f['path']}`，SHA256 `{f['sha256']}`。")
    elif failures:
        md+=['','## 修订批次执行失败','', '失败后停止，保留所有收据；具体阶段与错误见以下记录，不能自动沿用旧批次的初始化归因。']
        for f in failures:md.append(f"- `{f['id']}`：`{f['path']}`，SHA256 `{f['sha256']}`；最后错误：`{f['error'].strip().splitlines()[-1]}`。")
    (PACKAGE/('31_AB_CB优先dummy周期结果.md' if args.paced else '25_AB_CB完整周期条件实验.md')).write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=len(rows),expected=60,effects=len(effects),failures=len(failures))))


if __name__=='__main__':main()
