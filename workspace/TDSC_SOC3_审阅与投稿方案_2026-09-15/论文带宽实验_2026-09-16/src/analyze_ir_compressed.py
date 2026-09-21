"""Audit and summarize all planned compressed IR outcomes, including failures."""
from common import *
from collections import defaultdict
import statistics
from audit_ir_compressed import inputs,audit_record,matched
from audit_ir_compressed_failure import audit_failure
from analyze_ir_dwb import inputs as raw_inputs,audit_record as audit_raw
from analyze_ablation import summary
from start_ir_compressed_validation import validate_plan

def pair(a,b,axis):
    if axis!='packing':matched(a,b,axis)
    else:
        x,y=a['spec'],b['spec']
        ignore={'id','X','experiment_class'}
        assert {k:v for k,v in x.items() if k not in ignore}=={k:v for k,v in y.items() if k not in ignore|{'beta','map_mode','cohort'}}
        assert x['X']==16 and y['X']==32 and y['beta']==14
        assert a['trace']==b['trace'] and a['answer_sha256']==b['answer_sha256']
        for phase in ('warmup','measurement'):
            p,q=a['phases'][phase],b['phases'][phase]
            assert p['requests']==q['requests'] and p['public_slots']==q['public_slots']
            assert a['configs'][0]['N']+p['start_clock']==q['start_t'] and a['configs'][0]['N']+p['end_clock']==q['end_t']
        if x['kind'] in ('path','deferred'):assert a['bytes_per_request']==b['bytes_per_request']
    return dict(seed=b['spec']['trace_seed'],before=a['spec']['id'],after=b['spec']['id'],
        before_bytes=a['bytes_per_request'],after_bytes=b['bytes_per_request'],
        saving_pct=100*(1-b['bytes_per_request']/a['bytes_per_request']),
        before_rpc=a['rpc_per_request'],after_rpc=b['rpc_per_request'])

def main():
    path=PACKAGE/'formal_ir_compressed_plan.json';plan=json.loads(path.read_text());validate_plan(plan);kw=inputs()
    amendment=PACKAGE/'ir_compressed_observation_amendment.json';a=json.loads(amendment.read_text());assert a['original_plan_sha256']==sha(path)
    for n,h in a['sources'].items():assert sha(Path(__file__).parent/n)==h
    rows={};outcomes=[];missing=[]
    for s in plan['specs']:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json";f=PACKAGE/'results/failures'/f"{s['id']}.json"
        assert not (p.exists() and f.exists()),'ambiguous success and failure; inspect'
        if p.exists():
            r=json.loads(p.read_text());audit_record(r,s,**kw);rows[s['id']]=r
            outcomes.append(dict(id=s['id'],status='passed',path=str(p.relative_to(PACKAGE)),sha256=sha(p),cohort=s['cohort']))
        elif f.exists():
            r=json.loads(f.read_text());audit=audit_failure(r,s)
            assert s['cohort']=='reset_stress_beta4','a main failure must be investigated'
            outcomes.append(dict(id=s['id'],status='incomplete_horizon',path=str(f.relative_to(PACKAGE)),sha256=sha(f),cohort=s['cohort'],audit=audit))
        else:missing.append(s['id'])
    rawplan,rawkw=raw_inputs(periodic=True);assert sha(PACKAGE/'formal_ir_periodic_plan.json')==plan['comparison_raw_plan_sha256']
    raw={}
    for s in rawplan['specs']:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        if p.exists():
            r=json.loads(p.read_text());audit_raw(r,s,**rawkw);raw[s['id']]=r
    comparisons=defaultdict(list)
    by={(r['spec']['cohort'],r['spec']['kind'],r['spec']['dwb'],r['spec']['workload'],r['spec']['trace_seed']):r for r in rows.values()}
    for key,r in by.items():
        cohort,kind,dwb,workload,seed=key
        if kind=='sde':
            for base in ('path','deferred'):
                other=by.get((cohort,base,dwb,workload,seed))
                if other:comparisons[('backend',cohort,f'{base}->sde',dwb,workload)].append(pair(other,r,'backend'))
        if cohort=='main_beta14':
            if dwb:
                other=by.get((cohort,kind,False,workload,seed))
                if other:comparisons[('dwb',cohort,kind,True,workload)].append(pair(other,r,'dwb'))
            rawid=r['spec']['id'].replace('IRCM_','IRPER_',1)
            if rawid in raw:comparisons[('packing',cohort,kind,dwb,workload)].append(pair(raw[rawid],r,'packing'))
        elif cohort=='reset_stress_beta4':
            other=by.get(('main_beta14',kind,dwb,workload,seed))
            if other:comparisons[('beta','beta14->beta4',kind,dwb,workload)].append(pair(other,r,'beta'))
    effects=[]
    for key,pairs in sorted(comparisons.items()):
        pairs.sort(key=lambda x:x['seed']);st=summary([p['saving_pct'] for p in pairs])
        cvs=[statistics.stdev(v)/statistics.mean(v) if len(v)>1 else None for v in ([p['before_bytes'] for p in pairs],[p['after_bytes'] for p in pairs])]
        gate=None if st['n']<5 else max(cvs)>.1 or (st['ci95'][1]-st['ci95'][0])/2>5
        effects.append(dict(axis=key[0],cohort=key[1],comparison=key[2],dwb=key[3],workload=key[4],effect=st,per_seed=pairs,needs_more_repeats=gate))
    save(PACKAGE/'results/ir_compressed_statistics.json',dict(status='all_outcomes_audited' if not missing else 'partial_outcomes_audited',
        expected=75,observed=len(outcomes),passed=len(rows),incomplete=sum(x['status']=='incomplete_horizon' for x in outcomes),
        missing=missing,outcomes=outcomes,effects=effects,raw_comparators_audited=len(raw),plan_sha256=sha(path),
        amendment_sha256=sha(amendment),source_hashes=kw['source'],auditor_sha256=sha(__file__)))
    md=['# IR压缩位置表：完整周期实验与终点完成率','',
        f"75个预定配置中，已审计{len(outcomes)}个结果：{len(rows)}个完整完成，{sum(x['status']=='incomplete_horizon' for x in outcomes)}个固定窗口未完成。未完成配置仍列入75格；不能只对成功子集称完整五次重复。",'',
        '主60格：depth×DWB关/开×Path/Deferred/SDE×uniform/hot90×5种子，β14。压力15格：同X32、β4、DWB开、hot90×三后端×5种子。N4096/B64、人口4229、L12/cache6/PLB8/LLC8×2/R480；初始化4229、对齐8059、暖机12288、测量49152时隙，最终t73728。','',
        '## 启动前的边界发现','',
        '同目标规模的β14 pilot完成全部请求。β4 pilot在测量末尾完成6143/6144，仍有一个前台请求、level0分组重置cursor12/32；未见stash overflow。所有49152时隙的账单保留，不追加不计费drain。它是独立pilot，不能混入正式五种子均值。原“两个pilot都成功才启动”门槛因此未通过，原启动器已退出。','',
        '结果处理修订在pilot之后、正式结果之前写入ir_compressed_observation_amendment.json。原75个spec、输入、W、R和协议实现均不变：β14继续采用完整完成准入；15个β4压力配置全部执行并保留完成率，只有审计确认的窗口未完成可继续收集后续配置，其余错误仍停止。该修订不是把失败改为通过。失败记录缺少独立部分答案摘要，因此不将其用于正确完成请求的性能结论。','',
        '| 轴 | 组 | 比较 | DWB | 负载 | 完整配对n/5 | 总字节减少 | 95%区间 |','|---|---|---|---|---|---:|---:|---|']
    for e in effects:
        st=e['effect'];ci='待五次' if st['ci95'] is None else f"[{st['ci95'][0]:.3f}%, {st['ci95'][1]:.3f}%]"
        md.append(f"| {e['axis']} | {e['cohort']} | {e['comparison']} | {e['dwb']} | {e['workload']} | {st['n']}/5 | {st['mean']:.3f}% | {ci} |")
    md+=['','## 未完成窗口','',
        '| ID | 阶段 | 已完成/已提交请求 | 公共时隙 | 字节总量 |','|---|---|---:|---:|---:|']
    for r in outcomes:
        if r['status']!='incomplete_horizon':continue
        d=r['audit'];md.append(f"| {r['id']} | {d['phase']} | {d['completed_requests']}/{d['offered_requests']} | {d['public_slots']} | {d['total_bytes']} |")
    md+=['','固定时隙下，少做map工作可能只是多做dummy；同几何Path/Deferred的总通信应不变。压缩收益须同时报告前端工作量与实际字节。packing比较改变X和map编码，不能归为纯selective；β比较保持X32。','',
        '本实验不包含原生IR-Stash/PMMAC，不提供压缩前端完整自适应归约或新的容量证书，也没有稳态、真实峰值内存或延迟声明。正式数据尚未收齐时不补填预测值。']
    (PACKAGE/'33_IR压缩位置表周期结果.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(observed=len(outcomes),expected=75,passed=len(rows),effects=len(effects))))

if __name__=='__main__':main()

