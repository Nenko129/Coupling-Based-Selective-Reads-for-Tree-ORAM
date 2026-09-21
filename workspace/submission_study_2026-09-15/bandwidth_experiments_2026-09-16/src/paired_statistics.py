"""Paired run-level effects. Partial batches never masquerade as n=5."""
from common import *
from collections import defaultdict
import math,statistics

T95={5:2.7764451051977987,10:2.2621571628540993}

def groups(folder):
    out=defaultdict(dict)
    for path in (PACKAGE/'results'/folder).glob('*.json'):
        row=json.loads(path.read_text(encoding='utf-8'));assert row['status']=='passed'
        if folder=='formal_composition' and row['spec']['family']=='rho':continue
        if folder=='formal_cached_components' and row['spec']['family']=='IR':continue
        if folder.startswith('formal_cached') and 'cache_representation' not in row:continue
        if any(k.endswith('run_fast.py') for k in row['source_hashes']) and 'execution_revision' not in row:continue
        s=row['spec'];key=(s.get('family','core'),s['workload'],s['N'],s['B'],tuple(s['profile']),
                           s.get('layout'),s.get('cached_levels',0),s.get('R'),s.get('map_B'),s.get('terminal_bytes'),
                           s.get('compact'),s.get('fusion'))
        sub=s['kind'],s['trace_seed'];assert sub not in out[key],('duplicate run',key,sub)
        out[key][sub]=row
    return out

def main():
    result=[]
    for folder in ('formal_core','formal_composition','formal_rho_fixed','formal_cached_components','formal_cached_admitted'):
        for key,rs in groups(folder).items():
            for base,new in (('path','sde'),('deferred','sde'),('ring','gc_ring'),('ring','r0'),('gc_ring','r0')):
                seeds=sorted({s for kind,s in rs if kind==base}&{s for kind,s in rs if kind==new})
                if not seeds:continue
                values=[]
                for seed in seeds:
                    a=rs[base,seed];b=rs[new,seed]
                    assert a['trace']==b['trace'],'unpaired input trace'
                    if folder in ('formal_composition','formal_rho_fixed'):assert a['phases']['measurement']['schedules']==b['phases']['measurement']['schedules'],'frontend schedule changed'
                    values.append(100*(1-b['bytes_per_request']/a['bytes_per_request']))
                n=len(seeds);mean=statistics.mean(values);half=T95[n]*statistics.stdev(values)/math.sqrt(n) if n in T95 else None
                cvs=[]
                for kind in (base,new):
                    costs=[rs[kind,s]['bytes_per_request'] for s in seeds]
                    cvs.append(statistics.stdev(costs)/statistics.mean(costs) if n>1 else None)
                row=dict(family=key[0],workload=key[1],N=key[2],B=key[3],profile=key[4],layout=key[5],cached_levels=key[6],R=key[7],
                         source_folder=folder,baseline=base,selective=new,n=n,seeds=seeds,
                         paired_savings_pct=values,paired_mean_saving_pct=mean,ci95=None if half is None else [mean-half,mean+half],
                         baseline_mean_bytes=statistics.mean(rs[base,s]['bytes_per_request'] for s in seeds),
                         selective_mean_bytes=statistics.mean(rs[new,s]['bytes_per_request'] for s in seeds),
                         complete_initial_repeats=n>=5,needs_more_repeats=(half>5 or max(cvs)>0.1) if half is not None else None,
                         claim_status='formal batch partial; do not use as final headline' if n<5 else 'initial n=5 evidence; inspect precision and whole-batch audit')
                result.append(row)
    save(PACKAGE/'results/paired_statistics.json',dict(rows=result,method='mean of per-run paired savings; two-sided Student t at run level',
         no_instruction_to_drop_negative_results=True,complete_experiment_chapter=False))
    md=['# 正式运行的配对统计（随批次更新）','','n<5 的行仅为过程记录，尚未达到预定重复数；不生成置信区间，不作为论文最终结论。',
        '旧ρ结果和旧IR R256缓存结果不进入此表。IR的新R480结果、AB静态布局按各自完整收据加入；均不能改称完整原生系统。','',
        '| 组合/布局 | N / B | trace | 基线→selective | n | 基线 bytes/op | selective bytes/op | 配对平均节省 | 95%区间 |','|---|---|---|---|---:|---:|---:|---:|---|']
    for r in result:
        ci='待5次完整运行' if r['ci95'] is None else f"[{r['ci95'][0]:.2f}%, {r['ci95'][1]:.2f}%]"
        family=r['family']+(('/'+r['layout']) if r['layout'] else '')
        md.append(f"| {family} | {r['N']} / {r['B']} | {r['workload']} | {r['baseline']} → {r['selective']} | {r['n']} | {r['baseline_mean_bytes']:,.2f} | {r['selective_mean_bytes']:,.2f} | {r['paired_mean_saving_pct']:.2f}% | {ci} |")
    (PACKAGE/'03_正式运行配对统计.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(paired_groups=len(result),groups_with_5_repeats=sum(r['n']>=5 for r in result))))
if __name__=='__main__':main()
