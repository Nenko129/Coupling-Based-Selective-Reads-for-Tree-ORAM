"""Audit named extended runs, then summarize comparable pairs and period errors.

Public adjacent windows are deliberately summarized without an iid Student CI.
"""
from common import *
from collections import defaultdict
from fractions import Fraction
import math,statistics
from audit_frontend_batches import check_bill
from analyze_ablation import summary
from run_fast import expected_identity as fast_identity
from run_extended import identity as extended_identity
from run_extended_composition import identity as composition_identity
from run_bulk_scale import identity as bulk_identity


def audit_record(r,s,entry,alias=False):
    assert r['status']=='passed'
    ignore={'id','experiment_class','study'} if alias else set()
    assert {k:v for k,v in r['spec'].items() if k not in ignore}=={k:v for k,v in s.items() if k not in ignore}
    expected=composition_identity() if entry=='composition' else (bulk_identity() if s.get('study')=='size_slice' and not alias else extended_identity())
    if alias or s.get('experiment_class')=='formal_tuned':
        assert r['source_hashes'] in (source_identity(),fast_identity())
        if r['source_hashes']==fast_identity() and 'execution_revision' not in r:return False
    else:
        assert r['source_hashes']==expected
        if 'extended_experiment' not in r:return False
        assert r['extended_experiment']['source_identity']==expected
        if entry=='core' and s['study']=='size_slice' and r['execution_revision']['name']!='hmac_bulk_exact_v2':return False
    assert sha(PACKAGE/r['trace']['path'])==r['trace']['sha256']
    assert r['correctness_checked_requests']==s['warmup']+s['requests']
    setup=r['setup'] if isinstance(r['setup'],list) else [r['setup']]
    for b in setup:check_bill(b)
    for phase,count in [('warmup',s['warmup']),('measurement',s['requests'])]:
        x=r['phases'][phase];assert x['requests']==count
        bills=x['bills'] if 'bills' in x else [x]
        for b in bills:check_bill(b)
        assert x['total_bytes']==sum(b['total_bytes'] for b in bills)
        assert x['rpc']==sum(b['rpc'] for b in bills)
    assert r['bytes_per_request']*s['requests']==r['phases']['measurement']['total_bytes']
    return True


def matched(a,b):
    assert a['trace']==b['trace'] and a['spec']['trace_seed']==b['spec']['trace_seed']
    assert a['answer_sha256']==b['answer_sha256']
    for phase in ('warmup','measurement'):
        if 'schedules' in a['phases'][phase]:
            assert a['phases'][phase]['schedules']==b['phases'][phase]['schedules']
            assert a['phases'][phase]['frontend_metrics']==b['phases'][phase]['frontend_metrics']


def paired_row(rows,base,new,public=False):
    left={r['spec']['trace_seed']:r for r in rows if r['spec']['kind']==base}
    right={r['spec']['trace_seed']:r for r in rows if r['spec']['kind']==new}
    seeds=sorted(left.keys()&right.keys())
    if not seeds:return None
    values=[];details=[]
    for seed in seeds:
        a,b=left[seed],right[seed];matched(a,b)
        delta=100*(1-b['bytes_per_request']/a['bytes_per_request']);values.append(delta)
        detail=dict(seed=seed,baseline_id=a['spec']['id'],selective_id=b['spec']['id'],
                    baseline_bytes=a['bytes_per_request'],selective_bytes=b['bytes_per_request'],saving_pct=delta,
                    baseline_rpc=a['rpc_per_request'],selective_rpc=b['rpc_per_request'])
        if a['spec'].get('family')=='rho':
            aa=a['phases']['measurement']['bills'];bb=b['phases']['measurement']['bills']
            assert aa[0]['transcript_sha256']==bb[0]['transcript_sha256']
            assert aa[0]['total_bytes']==bb[0]['total_bytes']
            front=aa[0]['total_bytes'];back=aa[1]['total_bytes'];new_back=bb[1]['total_bytes']
            assert 1-Fraction(front+new_back,front+back)==Fraction(back,front+back)*(1-Fraction(new_back,back))
            detail.update(front_bytes=front/a['spec']['requests'],backend_share=back/(front+back),backend_saving_pct=100*(1-new_back/back))
        details.append(detail)
    effect=summary(values)
    if public:effect['ci95']=None
    effect['range']=[min(values),max(values)]
    cvs=[statistics.stdev([side[s]['bytes_per_request'] for s in seeds])/statistics.mean(side[s]['bytes_per_request'] for s in seeds) if len(seeds)>1 else None for side in (left,right)]
    needs_more=None if len(seeds)<5 or public else (max(cvs)>.10 or (effect['ci95'][1]-effect['ci95'][0])/2>5)
    return dict(baseline=base,selective=new,effect=effect,seeds=seeds,per_seed=details,
                baseline_mean_bytes=statistics.mean(d['baseline_bytes'] for d in details),selective_mean_bytes=statistics.mean(d['selective_bytes'] for d in details),
                run_cost_cv=cvs,needs_more_repeats=needs_more,
                statistical_unit='preselected adjacent trace-window/seed pairs; no population CI' if public else 'independent synthetic run pairs')


def main():
    audits=[];found={};all_pairs=[];calibration=[]
    plans=[('calibration','formal_calibration_plan.json'),('public','formal_public_plan.json'),
           ('sensitivity','formal_frontend_sensitivity_plan.json'),('slices','formal_slices_plan.json'),('tuned','formal_tuned_plan.json')]
    for study,filename in plans:
        planpath=PACKAGE/filename;plan=json.loads(planpath.read_text(encoding='utf-8'))
        entries=plan.get('items',[dict(spec=s,entry='core') for s in plan.get('specs',[])])
        entries=entries+[dict(x,entry='core',alias=True) for x in plan.get('aliases',[])]
        records=[];bindings=[];missing=[];pending=[]
        for item in entries:
            s=item['spec'];alias=item.get('alias',False)
            folder=item['folder'] if alias else s['experiment_class'];sid=item['source_id'] if alias else s['id']
            p=PACKAGE/'results'/folder/f'{sid}.json'
            if not p.exists():missing.append(s['id']);continue
            r=json.loads(p.read_text(encoding='utf-8'))
            # Tuned specs have no study field; the field is used only to choose a runtime closure.
            audit_spec=s
            if not audit_record(r,audit_spec,item['entry'],alias):pending.append(s['id']);continue
            records.append(r);bindings.append(dict(id=s['id'],source_id=sid,path=str(p.relative_to(PACKAGE)),sha256=sha(p),alias=alias))
        audits.append(dict(study=study,plan=filename,plan_sha256=sha(planpath),expected=len(entries),completed=len(records),missing=missing,pending_final_receipt=pending,bindings=bindings))
        found[study]=records
        grouped=defaultdict(list)
        for r in records:
            s=r['spec'];key=(s.get('family','core'),s['workload'],s['N'],s['B'],s.get('condition','default'))
            if study=='calibration':continue
            grouped[key].append(r)
        for key,rows in grouped.items():
            comparisons=[('path','sde'),('deferred','sde'),('ring','r0')]
            for base,new in comparisons:
                stat=paired_row(rows,base,new,public=study=='public')
                if stat:all_pairs.append(dict(study=study,family=key[0],workload=key[1],N=key[2],B=key[3],condition=key[4],**stat))
    # Period alignment is verified using the actual final t, not merely the plan label.
    groups=defaultdict(list)
    for r in found['calibration']:groups[r['spec']['kind'],tuple(r['spec']['profile'])].append(r)
    for (kind,profile),rows in groups.items():
        values=[];costs=[];models=[]
        for r in rows:
            s=r['spec'];assert len(r['configs'])==1
            period=s['period_slots'];start_t=r['final_clock'][0]['t']-s['requests']
            assert start_t%period==0 and s['requests']==4*period
            assert r['phases']['measurement']['backend_requests']==[s['requests']]
            lo=float(r['expected_periodic_cost']['total']['lower']);hi=float(r['expected_periodic_cost']['total']['upper'])
            model=(lo+hi)/2;costs.append(r['bytes_per_request']);models.append(model);values.append(100*(r['bytes_per_request']/model-1))
            if kind in ('path','deferred'):assert abs(r['bytes_per_request']-model)<1e-8,('deterministic billing mismatch',s['id'])
        assert max(models)-min(models)<1e-8
        calibration.append(dict(kind=kind,profile=list(profile),n=len(rows),model_bytes=models[0],observed_bytes=summary(costs),
                                model_relative_error_pct=summary(values),
                                service='Path reads and writes each random access path; the aligned window is a reference window, not a bit-reversal cycle' if kind=='path' else 'four complete scheduled bit-reversal service cycles',
                                no_steady_state_claim=True))
    out=dict(audits=audits,pairs=all_pairs,calibration=calibration,checker_sha256=sha(__file__),complete=all(r['completed']==r['expected'] for r in audits))
    save(PACKAGE/'results/extended_statistics.json',out)
    md=['# 扩展实验的配对统计与模型校准','','指标为实际序列化双向字节/应用请求。模型列为完整周期期望，不能与有限前缀测量混称。',
        '公开trace的5组相邻窗口只报配对均值与范围，不报告代表整个工作负载总体的独立样本置信区间。','',
        '| 批次 | 已核查/计划观察数 |','|---|---:|']
    for a in audits:md.append(f"| {a['study']} | {a['completed']}/{a['expected']} |")
    md+=['','## 配对收益','','n<5仅为过程数据；只用两侧均完成的同种子运行。','',
         '| 批次/条件 | 前端/负载 | N/B | 基线→selective | n | 基线 bytes/op | selective bytes/op | 节省 | 95%区间或窗口范围 |',
         '|---|---|---|---|---:|---:|---:|---:|---|']
    for r in all_pairs:
        e=r['effect'];ci=e['ci95'];interval=f"窗口范围 [{e['range'][0]:.2f}%, {e['range'][1]:.2f}%]" if r['study']=='public' else ('待5次' if ci is None else f'[{ci[0]:.2f}%, {ci[1]:.2f}%]')
        md.append(f"| {r['study']}/{r['condition']} | {r['family']}/{r['workload']} | {r['N']}/{r['B']} | {r['baseline']} → {r['selective']} | {e['n']} | {r['baseline_mean_bytes']:,.2f} | {r['selective_mean_bytes']:,.2f} | {e['mean']:.2f}% | {interval} |")
    md+=['','## 完整周期校准','','Path每次访问一条随机路径并读写；其窗口长度与其他方案对齐，但不是bit-reversal维护周期。其余方案核对测量起点整周期对齐。有限个周期仍不自动等于稳态。','',
         '| 协议/参数 | n | 周期期望 bytes/op | 实际均值 bytes/op | 相对模型偏差 |','|---|---:|---:|---:|---:|']
    for r in calibration:md.append(f"| {r['kind']}/{r['profile']} | {r['n']} | {r['model_bytes']:,.2f} | {r['observed_bytes']['mean']:,.2f} | {r['model_relative_error_pct']['mean']:.3f}% |")
    md+=['','随机neutral频次会产生有限样本偏差。单个均值或置信区间与模型不同不能直接判定协议或模型错误，应先检查暖机、周期相位与分项账单。所有偏差保留。',
         'sensitivity中的B4096点同时按编码容量改变X（raw=1024、compressed=2048），它是块大小与相应打包方式的配置切片，不能称固定X的单因素实验。']
    (PACKAGE/'15_扩展实验统计与模型校准.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(batches=[{k:a[k] for k in ('study','completed','expected')} for a in audits],pairs=len(all_pairs),calibration_groups=len(calibration))))

if __name__=='__main__':main()
