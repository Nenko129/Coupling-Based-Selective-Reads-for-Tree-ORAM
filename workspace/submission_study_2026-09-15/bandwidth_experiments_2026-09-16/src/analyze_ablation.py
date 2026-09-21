"""Actual four-cell effects and ordered changes, with all partial seeds explicit."""
from common import *
from run_fast import expected_identity
import statistics,math

def summary(values):
    n=len(values);mean=statistics.mean(values)
    t={5:2.7764451051977987,10:2.2621571628540993}.get(n)
    half=None if t is None else t*statistics.stdev(values)/math.sqrt(n)
    return dict(n=n,mean=mean,ci95=None if half is None else [mean-half,mean+half],per_seed=values)

def main():
    plan=json.loads((PACKAGE/'formal_ablation_plan.json').read_text());entries=[dict(spec=s,source=f"results/formal_ablation/{s['id']}.json") for s in plan['specs']]+plan['aliases']
    found={};audit=[]
    for x in entries:
        p=PACKAGE/x['source']
        if not p.exists():continue
        r=json.loads(p.read_text(encoding='utf-8'));s=x['spec']
        if r['source_hashes']==expected_identity() and 'execution_revision' not in r:continue
        assert r['source_hashes'] in (source_identity(),expected_identity())
        assert {k:v for k,v in r['spec'].items() if k not in ('id','experiment_class')}=={k:v for k,v in s.items() if k not in ('id','experiment_class')}
        found[s['id']]=r;audit.append(dict(id=s['id'],source=x['source'],sha256=sha(p)))
    effects=[]
    for family in ('43','76'):
        complete=[]
        for seed in range(101,106):
            names=[f'B2_R0_{family}_cf{c}{f}_seed{seed}' for c,f in ((0,0),(0,1),(1,0),(1,1))]
            if all(n in found for n in names):
                rows=[found[n] for n in names];assert all(r['trace']==rows[0]['trace'] for r in rows)
                complete.append((seed,[r['bytes_per_request'] for r in rows]))
        if not complete:continue
        for name,calc in [('fusion_without_compact_pct',lambda a,b,c,d:100*(1-b/a)),
                          ('fusion_with_compact_pct',lambda a,b,c,d:100*(1-d/c)),
                          ('compact_without_fusion_pct',lambda a,b,c,d:100*(1-c/a)),
                          ('compact_with_fusion_pct',lambda a,b,c,d:100*(1-d/b)),
                          ('interaction_bytes',lambda a,b,c,d:a-b-c+d)]:
            effects.append(dict(family=family,effect=name,seeds=[s for s,_ in complete],**summary([calc(*v) for _,v in complete])))
    ladder=[]
    order=['43_large_map_cf00','43_cf00','43_cf10','43_cf11','76_cf11']
    for before,after in zip(order,order[1:]):
        values=[];absolute=[];seeds=[]
        for seed in range(101,106):
            a=found.get(f'B2_R0_{before}_seed{seed}');b=found.get(f'B2_R0_{after}_seed{seed}')
            if a is None or b is None:continue
            assert a['trace']==b['trace'];seeds.append(seed)
            values.append(100*(1-b['bytes_per_request']/a['bytes_per_request']));absolute.append(a['bytes_per_request']-b['bytes_per_request'])
        if values:ladder.append(dict(before=before,after=after,seeds=seeds,saving_pct=summary(values),saving_bytes=summary(absolute)))
    save(PACKAGE/'results/ablation_measured.json',dict(audited_observations=len(found),expected_observations=45,receipts=audit,effects=effects,ladder=ladder,
         basis='actual serialized frames; conditional differences, not unique causal attribution',complete=len(found)==45))
    md=['# 实测消融进度','','每个效应仅使用四格均完成的同种子组；n<5不生成置信区间。负收益和交互项照常保留。','',
        '| 参数族 | 效应 | n | 均值 | 95%区间 |','|---|---|---:|---:|---|']
    for r in effects:
        unit=' bytes/op' if r['effect']=='interaction_bytes' else '%';ci='待五次' if r['ci95'] is None else f"[{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}]"
        md.append(f"| {r['family']} | {r['effect']} | {r['n']} | {r['mean']:.4f}{unit} | {ci} |")
    md+=['','| 顺序步骤 | n | 条件通信节省 |','|---|---:|---:|']
    for r in ladder:md.append(f"| {r['before']} → {r['after']} | {r['saving_pct']['n']} | {r['saving_pct']['mean']:.4f}% |")
    md+=['','顺序百分比不能直接相加。更换参数族同时改变Z/A/S、树高和递归布局；小map、compact、fusion分别记录。']
    (PACKAGE/'13_实测消融进度.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(observations=len(found),effects=len(effects),ladder=len(ladder))))
if __name__=='__main__':main()
