"""Freeze all predeclared compressed-map outcomes and raw-map comparators.

Incomplete stress windows remain outcomes; no survivor-only performance means.
"""
from common import *
from collections import defaultdict
import math
import statistics
from audit_ir_compressed import inputs,audit_record
from audit_ir_compressed_failure import audit_failure
from analyze_ir_dwb import inputs as raw_inputs,audit_record as audit_raw
from analyze_ir_compressed import pair
from start_ir_compressed_validation import validate_plan


def stats(xs):
    assert len(xs)==5
    mean=sum(xs)/5;half=2.7764451051977987*math.sqrt(sum((x-mean)**2 for x in xs)/20)
    return dict(n=5,mean=mean,ci95=[mean-half,mean+half],values=xs)


def resource(r):
    s=r['spec'];c=r['configs'][0];remote={k:0 for k in ('headers','ciphertext_slots','local_authentication','bucket_tags','global_tags')};cache=0
    for d in range(c['L']+1):
        z=c['Z_by_depth'][d] if c['Z_by_depth'] else c['Z']
        parts=dict(headers=76+((8+30*z+31)//32)*32,ciphertext_slots=z*(s['B']+16),local_authentication=0,bucket_tags=64,global_tags=64)
        if d<s['cached_levels']:cache+=2**d*sum(parts.values())
        else:
            for k,v in parts.items():remote[k]+=2**d*v
    assert r['server_storage']['components']==remote and r['server_storage']['total_bytes']==sum(remote.values())
    assert r['cache_representation']['bytes']==cache
    p=r['frontend_memory_representation'];f=p['plb']
    selected=dict(tree_cache=cache,stash_payload=f['stash_reserved_bytes'],plb_payload=f['plb_payload_bytes'],
        plb_leaf_address=f['plb_leaf_and_address_bytes'],terminal_leaf=f['terminal_leaf_bytes'],llc_payload=p['llc_payload_capacity'])
    return dict(server=r['server_storage'],selected_client=selected,selected_client_sum=sum(selected.values()),
        reset_metadata=f.get('reset_scalar_fields',0),actual_peak=False)


def main():
    pp=PACKAGE/'formal_ir_compressed_plan.json';plan=json.loads(pp.read_text());validate_plan(plan);kw=inputs()
    ap=PACKAGE/'ir_compressed_observation_amendment.json';amend=json.loads(ap.read_text())
    assert amend['original_plan_sha256']==sha(pp)
    for name,value in amend['sources'].items():assert sha(Path(__file__).parent/name)==value
    cp=PACKAGE/'results/ir_compressed_observation_completion.json';completion=json.loads(cp.read_text())
    assert completion['status'] in ('passed','completed_with_incomplete_windows') and completion['expected']==75
    assert completion['plan_sha256']==sha(pp) and completion['amendment_sha256']==sha(ap)
    done={r['id']:r for r in completion['observations']};assert len(done)==75
    records={};receipts=[];outcomes=[];groups=defaultdict(list)
    for s in plan['specs']:
        ref=done[s['id']];path=PACKAGE/ref['path'];assert sha(path)==ref['sha256'];r=json.loads(path.read_text())
        if ref['status']=='passed':
            audit_record(r,s,**kw);resource(r);records[s['id']]=r
            m=r['phases']['measurement'];bill=m['bills'][0]
            assert sum(bill['components'].values())==sum(sum(x.values()) for x in bill['by_stage'].values())==m['total_bytes']
            outcome=dict(id=s['id'],status='passed',phase='measurement',offered=s['requests'],completed=m['requests'],
                public_slots=m['public_slots'],total_bytes=m['total_bytes'],reset_end=m['reset_end'])
        else:
            assert ref['status']=='incomplete_horizon' and s['cohort']=='reset_stress_beta4'
            audited=audit_failure(r,s);assert audited==ref['audit']
            outcome=dict(id=s['id'],status='incomplete_horizon',audit=audited)
        receipts.append(dict(id=s['id'],path=str(path.relative_to(PACKAGE)),sha256=sha(path),status=ref['status']))
        outcomes.append(dict(outcome,spec=s));groups[s['cohort'],s['workload'],s['dwb'],s['kind']].append(s['id'])
    assert len(receipts)==75 and sum(o['status']!='passed' for o in outcomes)==completion['incomplete_windows']
    rp=PACKAGE/'formal_ir_periodic_plan.json';rawplan,rawkw=raw_inputs(periodic=True)
    assert sha(rp)==plan['comparison_raw_plan_sha256'] and len(rawplan['specs'])==60
    for s in rawplan['specs']:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json";r=json.loads(p.read_text());audit_raw(r,s,**rawkw);resource(r)
        records[s['id']]=r;receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p),status='reused_raw_control'))
    cells=[]
    for (cohort,workload,dwb,kind),ids in sorted(groups.items()):
        ids.sort(key=lambda name:done[name]['id'])
        assert len(ids)==5
        successful=sorted([records[i] for i in ids if i in records],key=lambda r:r['spec']['trace_seed'])
        complete=len(successful)==5
        cell=dict(cohort=cohort,workload=workload,dwb=dwb,kind=kind,ids=ids,completed=len(successful),expected=5,
            eligible_for_performance=complete)
        if complete:
            rs=successful;ms=[r['phases']['measurement'] for r in rs];res=[resource(r) for r in rs];assert all(x==res[0] for x in res)
            cell.update(bytes=stats([m['total_bytes']/m['requests'] for m in ms]),rpc=stats([m['rpc']/m['requests'] for m in ms]),
                resource=res[0],ids=[r['spec']['id'] for r in rs],
                frontend={k:stats([m['frontend_metrics'].get(k,0) for m in ms]) for k in sorted({k for m in ms for k in m['frontend_metrics']})},
                map_metrics={k:stats([m['map_metrics'].get(k,0) for m in ms]) for k in sorted({k for m in ms for k in m['map_metrics']})},
                components={k:stats([m['bills'][0]['components'].get(k,0)/m['requests'] for m in ms]) for k in sorted({k for m in ms for k in m['bills'][0]['components']})},
                reset_end=[m['reset_end'] for m in ms],observed_boundary_stash_max=[r['max_online_boundary_stash'] for r in rs])
        cells.append(cell)
    assert len(cells)==15
    # Declare all comparison groups before considering outcome completeness.
    by={(s['cohort'],s['kind'],s['dwb'],s['workload'],s['trace_seed']):s['id'] for s in plan['specs']}
    combinations=[]
    for cohort,workload,dwb in sorted({(s['cohort'],s['workload'],s['dwb']) for s in plan['specs']}):
        for base in ('path','deferred'):
            combinations.append(('backend',cohort,workload,dwb,base,'sde',[(by[cohort,base,dwb,workload,i],by[cohort,'sde',dwb,workload,i]) for i in range(101,106)]))
    for workload in ('uniform','hot90'):
        for kind in ('path','deferred','sde'):
            combinations.append(('dwb','main_beta14',workload,True,kind,kind,[(by['main_beta14',kind,False,workload,i],by['main_beta14',kind,True,workload,i]) for i in range(101,106)]))
            for dwb in (False,True):
                ids=[by['main_beta14',kind,dwb,workload,i] for i in range(101,106)]
                combinations.append(('packing','main_beta14',workload,dwb,kind,kind,[(name.replace('IRCM_','IRPER_',1),name) for name in ids]))
    for kind in ('path','deferred','sde'):
        combinations.append(('beta','beta14_to_beta4','hot90',True,kind,kind,[(by['main_beta14',kind,True,'hot90',i],by['reset_stress_beta4',kind,True,'hot90',i]) for i in range(101,106)]))
    effects=[];excluded=[]
    for axis,cohort,workload,dwb,base,var,pair_ids in combinations:
        meta=dict(axis=axis,cohort=cohort,workload=workload,dwb=dwb,baseline=base,variant=var)
        if not all(l in records and r in records for l,r in pair_ids):
            excluded.append(dict(meta,pairs=pair_ids,reason='at least one predeclared run did not finish its fixed horizon; no survivor-only mean'));continue
        pairs=[pair(records[l],records[r],axis) for l,r in pair_ids]
        values=[p['saving_pct'] for p in pairs];st=stats(values)
        cvs=[statistics.stdev(p[k] for p in pairs)/statistics.mean(p[k] for p in pairs) for k in ('before_bytes','after_bytes')]
        effects.append(dict(meta,pairs=pairs,paired_saving_pct=st,
            baseline_mean=statistics.mean(p['before_bytes'] for p in pairs),variant_mean=statistics.mean(p['after_bytes'] for p in pairs),
            paired_rpc_saving_pct=stats([100*(1-p['after_rpc']/p['before_rpc']) for p in pairs]),
            run_cost_cv=cvs,needs_more_repeats=max(cvs)>.10 or (st['ci95'][1]-st['ci95'][0])/2>5))
    assert len(effects)+len(excluded)==31
    pilot=[]
    for ref,s in zip(amend['pilot_outcomes'],plan['pilots']):
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];r=json.loads(p.read_text())
        if ref['status']=='passed':audit_record(r,s,**kw)
        else:assert audit_failure(r,s)==ref['audit']
        pilot.append(ref)
    out=dict(status='all_predeclared_outcomes_audited',new_outcomes=75,reused_raw_controls=60,
        passed=sum(o['status']=='passed' for o in outcomes),incomplete=completion['incomplete_windows'],outcomes=outcomes,
        cells=cells,effects=effects,excluded_effects=excluded,receipts=receipts,pilots_separate=pilot,
        plan_sha256=sha(pp),raw_plan_sha256=sha(rp),amendment_sha256=sha(ap),completion_sha256=sha(cp),
        producer_sha256=sha(__file__),source_hashes=kw['source'],proof_hashes=kw['proofs'],capacity_hash=kw['capacity_hash'],
        helper_hashes={n:sha(Path(__file__).parent/n) for n in ('audit_ir_compressed.py','audit_ir_compressed_failure.py','analyze_ir_compressed.py','analyze_ir_dwb.py','start_ir_compressed_validation.py')},
        additional_repeat_groups=[{k:e[k] for k in ('axis','cohort','workload','dwb','baseline','variant')} for e in effects if e['needs_more_repeats']],
        native_IR=False,IR_Stash=False,PMMAC=False,adaptive_security_proof=False,actual_peak_measured=False,latency_claim=False)
    target=PACKAGE/'results/ir_compressed_completed_snapshot.json'
    if target.exists():assert json.loads(target.read_text())==out,'completed snapshot is immutable'
    else:save(target,out)
    md=['# IR压缩位置表：完整75格观测与raw对照','',
        f"预声明75格全部取得最终结果：{out['passed']}格完整完成，{out['incomplete']}格固定窗口未完成；复用60份已完成raw-map对照，总共135份来源。所有失败和pilot保留，pilot不进入正式均值。完整五次配对才报告性能区间，未完成组不以成功子集替代。",'',
        'N4096/B64，压缩X32后人口4229，L12/A3/R480；异质Z=[4,4,4,4,4,4,2,2,2,3,3,4,4]，前六层缓存、PLB8、LLC8×2。主组β14包含DWB开/关、Uniform/Hot90和Path/Deferred/SDE；压力组β4固定DWB开、Hot90。','',
        '初始化4229个Transfer，8059槽对齐至12288；暖机12288槽/1536请求，测量49152槽/6144请求，最终t73728。计入每个公开空闲时隙，测量四个维护周期；dirty LLC和私有pending reset可留在终点，不追加不计费drain。Path使用等长参照窗口。','',
        '## 全部配置与完成率','',
        '| 组 / 负载 / DWB | 后端 | 完整运行 | bytes/request | RPC/request | reset槽均值 | dummy槽均值 |',
        '|---|---|---:|---:|---:|---:|---:|']
    for c in cells:
        name=f"{c['cohort']} / {c['workload']} / {int(c['dwb'])}"
        if not c['eligible_for_performance']:md.append(f"| {name} | {c['kind']} | {c['completed']}/5 | 不报告成功子集均值 | — | — | — |");continue
        f=c['frontend'];md.append(f"| {name} | {c['kind']} | 5/5 | {c['bytes']['mean']:,.3f} | {c['rpc']['mean']:.4f} | {f.get('group_reset_slots',{'mean':0})['mean']:.1f} | {f.get('dummy_slots',{'mean':0})['mean']:.1f} |")
    md+=['','## 同配置配对结果','',
        '| 因素 | 组 / 负载 / DWB | 比较 | 通信减少 | 95%区间 |','|---|---|---|---:|---|']
    for e in effects:
        x=e['paired_saving_pct'];lo,hi=x['ci95'];comparison=e['baseline']+' → '+e['variant'] if e['axis']=='backend' else e['variant']
        md.append(f"| {e['axis']} | {e['cohort']} / {e['workload']} / {int(e['dwb'])} | {comparison} | {x['mean']:.4f}% | [{lo:.4f}, {hi:.4f}]% |")
    md+=['','packing表示raw X16→compressed X32；beta表示β14→4；dwb表示关闭→开启。这些因素分别报告，不能将压缩、调度变化归为纯selective，也不能把百分比相加。负值保留。','',
        f"预声明的31组比较中，{len(effects)}组有完整五对，{len(excluded)}组因固定窗口未完成而不报告性能均值；追加重复门槛触发{len(out['additional_repeat_groups'])}组。",'',
        '## 固定时隙为何限制压缩/DWB的带宽收益','',
        '相同树几何和公开时隙下，Path/Deferred每槽通信固定。少访问位置表、把前台dirty写回搬到后台、或者增加group reset，都可能只是改变有效工作与dummy的比例。因此前端计数改善不能自动解释为总字节节省。所有DWB/β对照的Path和Deferred总字节相等，raw/compressed主组也如此；SDE的有限差异需结合配对区间，不能把微小波动叫额外收益。','',
        '## 固定窗口未完成与pilot','',
        'β4目标pilot只完成6143/6144，启动前据此预先修订观测处理规则：保留全部15个压力格的完成率，只有已审计的窗口未完成允许继续收集；不改W、R、输入或协议。该pilot仍单独保存，不用正式结果覆盖。','',
        '| 正式ID | 阶段 | 完成/提交 | 公开时隙 | 全部计费字节 |','|---|---|---:|---:|---:|']
    for o in outcomes:
        if o['status']=='passed':continue
        x=o['audit'];md.append(f"| {o['id']} | {x['phase']} | {x['completed_requests']}/{x['offered_requests']} | {x['public_slots']} | {x['total_bytes']} |")
    if not out['incomplete']:md.append('| 正式75格无窗口未完成；pilot另列 | — | — | — | — |')
    md+=['','## 资源、审计及主张边界','',
        f"每份完整运行重新核对返回摘要、初始化/对齐/结束时钟、分项字节、RPC连续性、reset游标及slot守恒。对{len(records)}份完整运行逐层重算服务器对象与可信前缀；另对{out['incomplete']}份未完成记录核查失败阶段、请求完成数、窗口及全部账单。PLB/LLC/stash/terminal和五个reset scalar字段单列。这些选定逻辑项不是并存ciphertext/decoded/write buffer/认证scratch的真实峰值。",'',
        '本组仍不包含原生IR-Stash或PMMAC，不能复用被反例拒绝的skip适配来增强收益主张。R480数值模型只提供既定profile/population条件参照，不给该完整压缩控制器自适应归约，也不替代基线安全定理。完整周期、正确返回和五次重复不等于原生IR闭合或稳态。','',
        '完整结果为`results/ir_compressed_completed_snapshot.json`；复现入口`src/freeze_ir_compressed_completed.py`。33号动态报告和原始失败文件继续保留。']
    (PACKAGE/'58_IR压缩位置表完整结果.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=out['status'],passed=out['passed'],incomplete=out['incomplete'],cells=len(cells),effects=len(effects),excluded=len(excluded))))


if __name__=='__main__':main()
