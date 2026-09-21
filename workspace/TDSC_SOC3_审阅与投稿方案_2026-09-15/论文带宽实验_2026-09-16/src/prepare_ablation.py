"""Clean factorial ablation, independently repeated; aliases avoid duplicate runs."""
from common import *
from run_core import configs_for
from optimized_cost import expected_tree,sum_rows
from decimal import Decimal

def main():
    plan=json.loads((PACKAGE/'formal_core_plan.json').read_text(encoding='utf-8'));template=dict(plan['specs'][0],kind='r0',workload='uniform')
    specs=[];aliases=[];models=[]
    for seed in range(101,106):
        for profile in ([4,3,3],[7,6,6]):
            family='43' if profile[0]==4 else '76'
            for compact,fusion in ((False,False),(False,True),(True,False),(True,True)):
                label=f'{int(compact)}{int(fusion)}'
                s=dict(template,id=f'B2_R0_{family}_cf{label}_seed{seed}',profile=profile,compact=compact,fusion=fusion,
                       trace_seed=seed,oram_seed=seed+900,experiment_class='formal_ablation')
                if family=='43' and compact and fusion:
                    aliases.append(dict(spec=s,source=f'results/formal_core/B1_r0_uniform_N16384_B4096_seed{seed}.json'))
                else:specs.append(s)
                if seed==101:models.append(dict(id=f'R0_{family}_cf{label}',spec=s,**sum_rows([expected_tree(c) for c in configs_for(s)])))
        large=dict(template,id=f'B2_R0_43_large_map_cf00_seed{seed}',map_B=4096,compact=False,fusion=False,
                   trace_seed=seed,oram_seed=seed+900,experiment_class='formal_ablation')
        specs.append(large)
        if seed==101:models.append(dict(id='R0_43_large_map_cf00',spec=large,**sum_rows([expected_tree(c) for c in configs_for(large)])))
    val={r['id']:Decimal(r['total']['upper']) for r in models};effects=[]
    for fam in ('43','76'):
        a,b,c,d=(val[f'R0_{fam}_cf{x}'] for x in ('00','10','01','11'))
        effects.append(dict(family=fam,compact_when_unfused_bytes=str(a-b),compact_when_fused_bytes=str(c-d),
             fusion_when_uncompact_bytes=str(a-c),fusion_when_compact_bytes=str(b-d),interaction_bytes=str(a-b-c+d),
             fusion_when_uncompact_pct=float(100*(1-c/a)),fusion_when_compact_pct=float(100*(1-d/b))))
    order=['R0_43_large_map_cf00','R0_43_cf00','R0_43_cf10','R0_43_cf11','R0_76_cf11']
    ladder=[dict(before=a,after=b,absolute_bytes=str(val[a]-val[b]),conditional_saving_pct=float(100*(1-val[b]/val[a]))) for a,b in zip(order,order[1:])]
    save(PACKAGE/'formal_ablation_plan.json',dict(specs=specs,aliases=aliases,new_runs=len(specs),total_runs_with_reuse=len(specs)+len(aliases),
         source_hashes=source_identity(),scope='compact/fusion factorial and ordered map/parameter-family ablation; not a unique causal allocation',
         setup_policy='independent initialization, same input traces as B1, fixed geometry inside each parameter family'))
    save(PACKAGE/'results/ablation_periodic_models.json',dict(status='analytic_expectation_not_measured',models=models,effects=effects,ladder=ladder))
    md=['# 干净消融：预先确定的配置与周期成本模型','','以下均为**周期期望模型值，非正式运行实测**。45次对应观察中5次复用B1同配置原始收据，另外执行40次。',
        '', '| 参数族 | compact | fusion | 期望 bytes/op |','|---|---:|---:|---:|']
    for r in models:md.append(f"| {r['id']} | {int(r['spec']['compact'])} | {int(r['spec']['fusion'])} | {float(r['total']['upper']):,.2f} |")
    md+=['','完整四格保留，不将compact与fusion合并归因。跨参数族的差别同时包含Z/A/S、高度和递归几何变化。','',
         '| 参数族 | fusion（无compact）节省 | fusion（有compact）节省 | 四格交互项 bytes/op |','|---|---:|---:|---:|']
    for e in effects:md.append(f"| {e['family']} | {e['fusion_when_uncompact_pct']:.3f}% | {e['fusion_when_compact_pct']:.3f}% | {float(e['interaction_bytes']):,.3f} |")
    (PACKAGE/'04_消融设计与模型表.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(new_runs=len(specs),reused=len(aliases),factorial_models=len(models))))
if __name__=='__main__':main()
