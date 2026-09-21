from pathlib import Path
import sys,json,statistics,math,datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minimal_runtime import *

def midpoint(obj):return (float(obj['lower'])+float(obj['upper']))/2

def main():
    if '--freeze' in sys.argv:
        save(HOME/'source_lock.json',dict(source_hashes=identity(),plan_hashes={n:sha(HOME/n) for n in ('pilot_plan.json','formal_plan.json')},created=datetime.datetime.now().isoformat()))
    rows=[]
    for suite in ('pilot','formal'):
        plan={s['id']:s for s in json.loads((HOME/f'{suite}_plan.json').read_text(encoding='utf-8'))['specs']}
        for p in (HOME/'results'/suite).glob('*.json'):
            r=json.loads(p.read_text(encoding='utf-8'));assert r['status']=='passed'
            s=r['spec'];assert s==plan[s['id']]
            locked=r['source_hashes'];locked=locked.get('minimal',locked);assert locked==identity()
            flags=r.get('effective_flags');configs=[r['config']] if 'config' in r else r['configs']
            assert all(not c['compact'] and not c['fused'] and c['kind']!='r0' for c in configs)
            rows.append((suite,r,p))
    groups={}
    for suite,r,p in rows:
        s=r['spec'];k=(suite,s['family'],s['layout'],s['B'],s['workload'])
        assert (s['arm'],s['trace_seed']) not in groups.setdefault(k,{})
        groups[k][s['arm'],s['trace_seed']]=(r,p)
    comparisons=[]
    for k,rs in sorted(groups.items()):
        for base in ('base','full_probe'):
            seeds=sorted({seed for arm,seed in rs if arm==base}&{seed for arm,seed in rs if arm=='selective'})
            if not seeds:continue
            effects=[];a_bytes=[];b_bytes=[];a_rpc=[];b_rpc=[];refs=[]
            for seed in seeds:
                a,ap=rs[base,seed];b,bp=rs['selective',seed]
                assert a['trace']==b['trace'] and a['answer_sha256']==b['answer_sha256']
                for field in ('N','B','profile','R','warmup','requests','compact','fusion','root_retained'):
                    assert a['spec'][field]==b['spec'][field]
                if 'schedules' in a['phases']['measurement']:
                    assert a['phases']['measurement']['schedules']==b['phases']['measurement']['schedules']
                effects.append(100*(1-b['bytes_per_request']/a['bytes_per_request']))
                a_bytes.append(a['bytes_per_request']);b_bytes.append(b['bytes_per_request']);a_rpc.append(a['rpc_per_request']);b_rpc.append(b['rpc_per_request'])
                refs.append(dict(seed=seed,base=str(ap.relative_to(HOME)),selective=str(bp.relative_to(HOME)),base_sha256=sha(ap),selective_sha256=sha(bp)))
            n=len(effects);mean=statistics.mean(effects);t95={5:2.7764451051977987,10:2.2621571628540993}
            half=t95[n]*statistics.stdev(effects)/math.sqrt(n) if n in t95 else None
            cv=max(statistics.stdev(v)/statistics.mean(v) for v in (a_bytes,b_bytes)) if n>1 else None
            comparisons.append(dict(suite=k[0],family=k[1],layout=k[2],B=k[3],workload=k[4],baseline=base,n=n,
                mean_saving_pct=mean,paired_effects_pct=effects,ci95=None if half is None else [mean-half,mean+half],
                baseline_bytes=statistics.mean(a_bytes),selective_bytes=statistics.mean(b_bytes),baseline_rpc=statistics.mean(a_rpc),selective_rpc=statistics.mean(b_rpc),receipts=refs,
                needs_more_repeats=None if half is None else (half>5 or cv>0.1),
                headline_eligible=n>=5 and k[0]=='formal' and half is not None and half<=5 and cv<=0.1))
    theory=[];seen=set()
    for s in json.loads((HOME/'formal_plan.json').read_text(encoding='utf-8'))['specs']:
        if s['family'] not in ('IR','AB'):continue
        k=(s['family'],s['layout'],s['B'],s['arm'])
        if k in seen:continue
        seen.add(k);c=configuration(s);cost=expected_tree(c,s['cached_levels'])
        theory.append(dict(family=s['family'],layout=s['layout'],B=s['B'],arm=s['arm'],cost=cost,config=dataclasses.asdict(c)))
    save(HOME/'results/analysis.json',dict(generated=datetime.datetime.now().isoformat(),receipt_count=len(rows),comparisons=comparisons,theory=theory,
       note='pilot is a single seed at N128; theoretical expectation is separate from measured values; formal partial rows are not final conclusions'))
    md=['# 最小组合实验：当前可核验结果','','关闭 compact header、fusion、省根和参数重调。base 使用原样式放置；full_probe 与 selective 使用相同受限放置，只有逻辑读集合不同。',
        '预实验 N=128、单种子，不能作为投稿效应量。正式计划 N=4096，每格5种子；IR/AB测量两个完整维护周期。','','| 批次 | 组合 | B | 对照 | n | 对照 bytes/op | selective bytes/op | 节省 | 95%区间 |','|---|---|---:|---|---:|---:|---:|---:|---|']
    for r in comparisons:
        ci='不生成' if r['ci95'] is None else f"[{r['ci95'][0]:.3f}%, {r['ci95'][1]:.3f}%]"
        md.append(f"| {r['suite']} | {r['family']}/{r['layout']} | {r['B']} | {r['baseline']} | {r['n']} | {r['baseline_bytes']:,.2f} | {r['selective_bytes']:,.2f} | {r['mean_saving_pct']:.3f}% | {ci} |")
    (HOME/'05_最小组合实验结果.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    grouped={}
    for r in theory:grouped.setdefault((r['family'],r['layout'],r['B']),{})[r['arm']]=r
    lines=['# 纯selective正式配置的理论期望','','以下是模型计算，不是新正式实验的实测均值。N4096、Z4/A3、根保留、完整header、独立neutral、相同缓存与布局。',
           'IR为完整维护周期期望；AB另包含理想随机槽及服务窗口neutral频率。误差验证以相应raw receipt为准。','','| 组合 | B | base bytes/op期望 | selective bytes/op期望 | 模型节省 |','|---|---:|---:|---:|---:|']
    for (family,layout,B),arms in sorted(grouped.items()):
        a=midpoint(arms['base']['cost']['total']);b=midpoint(arms['selective']['cost']['total'])
        lines.append(f'| {family}/{layout} | {B} | {a:,.3f} | {b:,.3f} | {100*(1-b/a):.3f}% |')
    lines += ['', 'Freecursive/ρ的总期望还需要前端实际tick/命中率，故不填一个假定普适的固定降幅；新预实验和既有前端计费结果单列。',
              'full_probe和base的公开全读/维护形状一致，模型期望相同；真实Ring有限样本可因随机槽/neutral计数不同而不同。']
    (HOME/'06_理论性能预测.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(receipts=len(rows),comparisons=len(comparisons),theory_rows=len(theory))))
if __name__=='__main__':main()
