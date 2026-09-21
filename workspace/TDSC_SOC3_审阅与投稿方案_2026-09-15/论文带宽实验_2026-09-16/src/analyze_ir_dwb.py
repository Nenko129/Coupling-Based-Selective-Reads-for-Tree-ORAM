"""Audit the integrated IR fixed-horizon experiment before estimating effects.

The control trace, answer digest, ledger partitions and clock conservation are
checked separately from the runtime's success flag. This is an artifact audit,
not an independent execution or a native IR security proof.
"""
from common import *
from collections import defaultdict
import math, statistics
from functools import lru_cache
from audit_frontend_batches import check_bill
from analyze_ablation import summary
from run_ir_dwb import identity


@lru_cache(None)
def expected_answers(path, expected_sha, N, B, count, seed, workload):
    p=(PACKAGE/path).resolve()
    assert p.is_relative_to(PACKAGE.resolve()) and sha(p)==expected_sha
    t=json.loads(p.read_text(encoding='utf-8'))
    assert (t['N'],t['count'],t['seed'],t['workload'])==(N,count,seed,workload)
    assert len(t['rows'])==count
    # Independent of the frontend's initial_payload and workload.payload code.
    truth={a:a.to_bytes(8,'big')+bytes(B-8) for a in range(N)}
    ans=hashlib.sha256()
    for a,v in t['rows']:
        assert isinstance(a,int) and 0<=a<N
        ans.update(truth[a])
        if v is not None:
            assert isinstance(v,int) and v>=1
            truth[a]=hashlib.shake_256(b'SOC3-EVAL-PAYLOAD-v1'+a.to_bytes(8,'big')+v.to_bytes(8,'big')).digest(B)
    return ans.hexdigest()


def bill(b):
    check_bill(b)
    assert all(isinstance(v,int) and v>=0 for v in b['components'].values())
    for partition in ('by_stage','by_tree'):
        for component,value in b['components'].items():
            assert sum(x.get(component,0) for x in b[partition].values())==value


def audit_record(r,s,source,proof_hash,capacity_hash,lifetime,periodic=False):
    assert r['status']=='passed' and r['spec']==s and r['source_hashes']==source
    assert r['controller_proof_sha256']==proof_hash
    assert not r['native_full_paper_reproduction'] and not r['latency_claim'] and not r['true_client_peak_measured']
    assert r['correctness_checked_requests']==s['warmup']+s['requests']
    assert r['answer_sha256']==expected_answers(r['trace']['path'],r['trace']['sha256'],s['N'],s['B'],
        s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    # This plan is raw recursive maps: ceil(N/X) + ceil(N/X^2) + ... + 1.
    population=s['N'];n=s['N']
    while n>1:
        n=(n+s['X']-1)//s['X'];population+=n
    c,=r['configs'];assert c==dict(kind=s['kind'],L=12,N=population,B=s['B'],Z=s['profile'][0],
        A=s['profile'][1],S=s['profile'][2],R=s['R'],tree=0,compact=True,fused=True,
        Z_by_depth=s['Z_by_depth'],S_by_depth=[])
    assert population==4369 and population<=c['A']*2**(c['L']-1)
    binding=r['capacity_model_binding']
    assert binding==dict(matches_profile_and_population=True,population_including_maps=population,
        audit_sha256=capacity_hash,selective_reference_R=480,lifetime_log2=lifetime,
        protocol_closure=False,baseline_theorem_not_supplied=s['kind']!='sde')
    assert s['R']>=480
    profile=s['Z_by_depth'] or [c['Z']]*(c['L']+1)
    assert len(profile)==13 and all(a>=b for a,b in zip(profile,[4,4,4,4,4,4,2,2,2,3,3,4,4]))
    bill(r['setup']);lastseq=r['setup']['next_sequence'];clock=0
    if periodic:
        period=c['A']*2**c['L'];a=r['alignment'];bill(a['bill'])
        assert a['public_slots']==(-population)%period and a['start_t']==population
        assert a['end_t']==population+a['public_slots'] and a['end_t']%period==0
        assert a['schedule']['slots']==a['public_slots'] and a['bill']['first_sequence']==lastseq
        clock=a['public_slots'];lastseq=a['bill']['next_sequence']
        assert s['period_slots']==period and s['warmup']*s['slots_per_request']==period
        assert s['requests']*s['slots_per_request']==4*period
        assert r['periodic_extension']==dict(period_slots=period,warmup_complete_periods=1,measurement_complete_periods=4,
            no_steady_state_claim=True,path_uses_reference_window=s['kind']=='path')
    for phase,Q in [('warmup',s['warmup']),('measurement',s['requests'])]:
        p=r['phases'][phase];W=Q*s['slots_per_request'];m=p['frontend_metrics']
        assert p['requests']==Q and p['public_slots']==W and p['start_clock']==clock and p['end_clock']==clock+W
        if periodic:assert (population+p['start_clock'])%s['period_slots']==0 and (population+p['end_clock'])%s['period_slots']==0
        clock+=W
        b,=p['bills'];bill(b)
        assert b['first_sequence']==lastseq;lastseq=b['next_sequence']
        assert p['total_bytes']==b['total_bytes'] and p['rpc']==b['rpc']
        assert p['bytes_per_public_slot']==b['total_bytes']/W
        schedule,=p['schedules'];assert schedule['slots']==W
        assert len(schedule['remove_admit_sha256'])==64
        assert m['public_slots']==W and m['application_completed']==Q and m['unfinished_foreground']==0
        assert all(isinstance(v,(int,bool)) and v>=0 for v in m.values())
        assert m.get('llc_hits',0)+m.get('llc_misses',0)==Q
        assert m.get('foreground_slots',0)==m.get('foreground_data_slots',0)+m.get('foreground_posmap_slots',0)
        assert m.get('foreground_data_slots',0)==m.get('llc_misses',0)+m.get('foreground_writebacks',0)
        assert m.get('dwb_data_slots',0)==m.get('dwb_completed',0)
        assert W==sum(m.get(k,0) for k in ('foreground_slots','dwb_posmap_slots','dwb_data_slots','dummy_slots'))
        assert 0<=m['dirty_resident']<=s['llc_sets']*s['llc_ways']
        if not s['dwb']:
            assert not m['dwb_pending'] and all(not v for k,v in m.items() if k.startswith('dwb_'))
    p=r['phases']['measurement']
    assert r['bytes_per_request']==p['total_bytes']/s['requests']
    assert r['rpc_per_request']==p['rpc']/s['requests']
    assert r['bytes_per_public_slot']==p['bytes_per_public_slot']
    assert r['final_clock']['t']==population+clock
    storage=r['server_storage'];assert storage['total_bytes']==sum(storage['components'].values())
    assert storage['physical_bucket_records']==2**(c['L']+1)-2**s['cached_levels']
    cache=r['cache_representation'];assert cache['bucket_records']==cache['global_tag_records']==2**s['cached_levels']-1
    mem=r['frontend_memory_representation'];assert mem['llc_payload_capacity']==s['llc_sets']*s['llc_ways']*s['B']
    assert mem['plb']['plb_payload_bytes']==s['plb']*s['B'] and mem['logical_metadata_not_peak']
    return True


def matched(a,b,axis):
    allowed={'id'}|{'backend':{'kind'},'layout':{'layout','Z_by_depth'},'dwb':{'dwb'}}[axis]
    assert {k:v for k,v in a['spec'].items() if k not in allowed}=={k:v for k,v in b['spec'].items() if k not in allowed}
    assert a['trace']==b['trace'] and a['answer_sha256']==b['answer_sha256']
    for phase in ('warmup','measurement'):
        x=a['phases'][phase];y=b['phases'][phase]
        assert (x['requests'],x['public_slots'],x['start_clock'],x['end_clock'])==(y['requests'],y['public_slots'],y['start_clock'],y['end_clock'])
        if axis!='dwb':
            assert x['schedules']==y['schedules'] and x['frontend_metrics']==y['frontend_metrics']
    assert a['cache_representation']==b['cache_representation']
    assert a['frontend_memory_representation']==b['frontend_memory_representation']
    if axis=='dwb' and a['spec']['kind'] in ('path','deferred'):
        # Fixed full-path lengths and a fixed clock have no traffic saving from
        # reusing dummy slots; changed useful work must not alter this identity.
        assert a['phases']['measurement']['total_bytes']==b['phases']['measurement']['total_bytes']


def pair_group(rows,axis,before,after):
    field={'backend':'kind','layout':'layout','dwb':'dwb'}[axis]
    left={r['spec']['trace_seed']:r for r in rows if r['spec'][field]==before}
    right={r['spec']['trace_seed']:r for r in rows if r['spec'][field]==after}
    seeds=sorted(left.keys()&right.keys())
    if not seeds:return None
    details=[]
    for seed in seeds:
        a,b=left[seed],right[seed];matched(a,b,axis)
        details.append(dict(seed=seed,baseline_id=a['spec']['id'],variant_id=b['spec']['id'],
            baseline_bytes=a['bytes_per_request'],variant_bytes=b['bytes_per_request'],
            saving_pct=100*(1-b['bytes_per_request']/a['bytes_per_request']),
            baseline_rpc=a['rpc_per_request'],variant_rpc=b['rpc_per_request'],
            baseline_metrics=a['phases']['measurement']['frontend_metrics'],variant_metrics=b['phases']['measurement']['frontend_metrics']))
    stat=summary([x['saving_pct'] for x in details])
    cvs=[statistics.stdev([side[s]['bytes_per_request'] for s in seeds])/statistics.mean(side[s]['bytes_per_request'] for s in seeds) if len(seeds)>1 else None for side in (left,right)]
    needs_more=None if len(seeds)<5 else (max(cvs)>.10 or (stat['ci95'][1]-stat['ci95'][0])/2>5)
    return dict(axis=axis,before=before,after=after,effect=stat,baseline_mean_bytes=statistics.mean(d['baseline_bytes'] for d in details),
        variant_mean_bytes=statistics.mean(d['variant_bytes'] for d in details),run_cost_cv=cvs,needs_more_repeats=needs_more,per_seed=details)


def condition_label(effect):
    first,second,workload=effect['condition']
    names={'path':'Path','deferred':'Deferred','sde':'SDE','depth':'异质桶','uniform':'均匀桶'}
    if effect['axis']=='dwb':middle=names[second]
    else:middle='DWB开' if second else 'DWB关'
    return f"{names[first]} / {middle} / "+{'uniform':'均匀负载','hot90':'热点负载'}[workload]


def inputs(periodic=False):
    plan=json.loads((PACKAGE/('formal_ir_periodic_plan.json' if periodic else 'formal_ir_dwb_plan.json')).read_text(encoding='utf-8'))
    if periodic:
        from run_ir_periodic import identity as periodic_identity
        source=periodic_identity()
    else:source=identity()
    assert plan['source_hashes']==source
    # The staged frontend imports need/Reject from the original Transfer module.
    # The live runner's runtime identity omits that import, so bind it to the
    # earlier frozen manifest instead of silently changing a running closure.
    manifest=json.loads((COMPOSITION.parent/'MANIFEST.sha256.json').read_text(encoding='utf-8'))
    files=manifest.get('files',manifest)
    for name in ('frontends.py','transfer_backend.py'):
        assert sha(COMPOSITION/name)==files['src/'+name]
    p=PACKAGE/'results/ir_dwb_controller_checks.json';proof=json.loads(p.read_text())
    assert proof['status']=='passed' and proof['runtime_identity']==source['runtime']
    cap=PACKAGE/'numerics/IR43_scaled_L12_c480_m128_audit.json';a=json.loads(cap.read_text())
    lifetime=next(x['lifetime_log2'] for x in a['tested'] if x['R']==480)
    return plan,dict(source=source,proof_hash=sha(p),capacity_hash=sha(cap),lifetime=lifetime,periodic=periodic)


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--periodic',action='store_true');args=parser.parse_args()
    plan,kwargs=inputs(args.periodic);rows=[];receipts=[];missing=[]
    for s in plan['specs']:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        if not p.exists():missing.append(s['id']);continue
        r=json.loads(p.read_text(encoding='utf-8'));audit_record(r,s,**kwargs);rows.append(r)
        receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    groups={axis:defaultdict(list) for axis in ('backend','layout','dwb')}
    for r in rows:
        s=r['spec']
        groups['backend'][s['layout'],s['dwb'],s['workload']].append(r)
        groups['layout'][s['kind'],s['dwb'],s['workload']].append(r)
        groups['dwb'][s['layout'],s['kind'],s['workload']].append(r)
    effects=[]
    for axis,group in groups.items():
        for key,rs in sorted(group.items()):
            choices={'backend':[('path','sde'),('deferred','sde')],'layout':[('uniform','depth')],'dwb':[(False,True)]}[axis]
            for before,after in choices:
                result=pair_group(rs,axis,before,after)
                if result:effects.append(dict(condition=list(key),**result))
    out=dict(status='complete_receipts_audited' if not missing else 'partial_receipts_audited',expected=len(plan['specs']),completed=len(rows),
        plan_sha256=sha(PACKAGE/('formal_ir_periodic_plan.json' if args.periodic else 'formal_ir_dwb_plan.json')),checker_sha256=sha(__file__),receipts=receipts,missing=missing,effects=effects,
        endpoint='same public W and Q completed requests, inclusive dirty LLC may remain; no persistence-barrier claim',
        scope='static IR allocation + prefix cache + raw maps + LLC + DWB; no IR-Stash, compressed maps or native full-system reproduction',
        frozen_frontend_binding=dict(manifest=str((COMPOSITION.parent/'MANIFEST.sha256.json').relative_to(ROOT)),
            manifest_sha256=sha(COMPOSITION.parent/'MANIFEST.sha256.json'),
            source_hashes={n:sha(COMPOSITION/n) for n in ('frontends.py','transfer_backend.py')}),
        security_proof=False,latency_claim=False)
    save(PACKAGE/('results/ir_periodic_statistics.json' if args.periodic else 'results/ir_dwb_statistics.json'),out)
    md=['# IR集成DWB：通信审计与配对结果','',f"已审计 {len(rows)}/{len(plan['specs'])} 个具名运行。n<5只作过程记录，不作论文最终性能结论。",
        '', 'N=4096、64B数据块；递归map后人口4369；前6层缓存、PLB8、LLC为8组×2路。双方相同128次暖机请求/1024时隙和256次测量请求/2048时隙。',
        '该窗口是有限前缀，不代表稳态或完整维护周期；计入每个dummy、PosMap、回写和认证。测量终点允许LLC保留dirty数据，双方均未承诺持久化屏障。',
        '', '| 变化 | 固定条件 | n | 基线 bytes/op | 组合 bytes/op | 节省 | 95%区间 |', '|---|---|---:|---:|---:|---:|---|']
    if args.periodic:
        md[0]='# IR集成DWB：完整周期窗口复核'
        md[4]='N=4096、B=64、depth布局、递归后人口4369；缓存前6层、PLB8、LLC8组×2路。初始化后7919个dummy时隙对齐，再暖机1536请求/12288时隙，测量6144请求/49152时隙。'
        md[5]='Deferred/SDE覆盖一个完整暖机维护周期与四个测量周期；Path仅使用同长度参考窗口。所有对齐通信单列，未并入测量。有限周期不自动等于稳态；测量终点仍允许dirty LLC驻留。'
    for e in effects:
        t=e['effect'];ci=t['ci95'];interval='待5次' if ci is None else f'[{ci[0]:.3f}%, {ci[1]:.3f}%]'
        change='DWB关 → 开' if e['axis']=='dwb' else ('均匀桶 → 异质桶' if e['axis']=='layout' else e['before'].title()+' → SDE')
        md.append(f"| {change} | {condition_label(e)} | {t['n']} | {e['baseline_mean_bytes']:,.2f} | {e['variant_mean_bytes']:,.2f} | {t['mean']:.3f}% | {interval} |")
    md+=['','每行只改变第一列所列因素；其余公开设置和输入保持一致。',
        '', '## DWB的工作量与终点','', '| layout/backend/负载 | n | 前台回写 off→on | DWB完成 off→on | dummy时隙 off→on | dirty留存 off→on |', '|---|---:|---:|---:|---:|---:|']
    for e in effects:
        if e['axis']!='dwb':continue
        def avg(side,key):return statistics.mean(d[side+'_metrics'].get(key,0) for d in e['per_seed'])
        vals=[f"{avg('baseline',k):.1f} → {avg('variant',k):.1f}" for k in ('foreground_writebacks','dwb_completed','dummy_slots','dirty_resident')]
        md.append(f"| {condition_label(e)} | {e['effect']['n']} | "+' | '.join(vals)+' |')
    md+=['','后台DWB减少前台dirty回写并不等于减少总传输。Path/Deferred在同固定时隙和布局下总通信应完全相同；SDE可因不同随机路径序列产生有限样本波动，保留负收益。',
        '每个结果均核查输入与源码身份、独立重算答案摘要、每类账单分项、RPC序号连续性、每时隙恰好一次Transfer及前端计数守恒。后端/布局比较还核对相同remove/admit摘要与前端工作量。',
        '容量数值包只提供该profile的条件参考；原生IR-Stash、新组合的完整归约以及Path/Deferred基线安全定理仍未齐，不能称完整原生IR闭合。']
    (PACKAGE/('21_IR完整周期窗口结果.md' if args.periodic else '19_IR集成DWB通信结果.md')).write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=len(rows),expected=len(plan['specs']),effects=len(effects))))


if __name__=='__main__':main()
