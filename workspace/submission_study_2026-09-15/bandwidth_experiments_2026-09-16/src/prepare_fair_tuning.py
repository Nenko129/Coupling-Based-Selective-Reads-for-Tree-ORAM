"""Finite, public candidate set; choose by periodic model before matched runs."""
from common import *
from run_core import configs_for
from optimized_oram import local_indices, TAG
from optimized_cost import expected_tree, sum_rows
from optimized_gate import OptimizedBank
from decimal import Decimal
import dataclasses


def object_storage(cs):
    total=0
    for c in cs:
        buckets=(1<<(c.L+1))-1;full=buckets-int(c.rootless)
        total+=full*(c.H+c.n*c.W+(len(local_indices(c.n))*TAG if c.ring else 0))+2*buckets*TAG
    return total


def main():
    bank=OptimizedBank();candidates=[]
    families={'path':[(4,3,3),(5,3,3)],'deferred':[(4,3,3)],'sde':[(4,3,3)],
              'ring':[(4,3,3),(4,3,4),(4,3,6),(7,6,6),(7,6,9)],
              'r0':[(4,3,3),(4,3,6),(7,6,6)]}
    for kind,profiles in families.items():
        for profile in profiles:
            for map_B in (256,512,1024):
                for terminal in (8192,32768):
                    s=dict(kind=kind,N=16384,B=4096,profile=list(profile),map_B=map_B,terminal_bytes=terminal,
                           compact=True,fusion=True,R=256)
                    cs=configs_for(s);cost=sum_rows([expected_tree(c) for c in cs]);server=object_storage(cs)
                    persistent=sum(c.R*c.B for c in cs)+4*cs[-1].N
                    reasons=[];gate=None;gate_error=None
                    try:gate=bank.plan(cs,1<<56)
                    except (ValueError,KeyError) as e:gate_error=str(e)
                    if kind in ('sde','r0') and gate is None:reasons.append('selective profile rejected by its applicable frozen gate')
                    # These are serialized storage / persistent-payload limits, not RSS or a peak-memory claim.
                    if server>4*(1<<30):reasons.append('serialized server objects exceed common 4 GiB budget')
                    if persistent>256*(1<<20):reasons.append('persistent stash payload plus terminal map exceeds common 256 MiB budget')
                    candidates.append(dict(candidate_id=f'TUNE_{len(candidates):03d}',spec=s,configs=[dataclasses.asdict(c) for c in cs],
                        periodic_model=cost,server_object_bytes=server,persistent_payload_plus_terminal=persistent,
                        eligible=not reasons,rejection_reasons=reasons,selective_gate=gate,baseline_gate_gap=gate_error,
                        true_peak_memory_checked=False))
    chosen=[]
    for kind in families:
        eligible=[c for c in candidates if c['spec']['kind']==kind and c['eligible']]
        winner=min(eligible,key=lambda c:(Decimal(c['periodic_model']['total']['upper']),c['server_object_bytes'],c['persistent_payload_plus_terminal'],c['candidate_id']))
        chosen.append(winner)
    plans=[];aliases=[];core=json.loads((PACKAGE/'formal_core_plan.json').read_text())['specs']
    def comparable(s):return {k:v for k,v in s.items() if k not in ('id','experiment_class')}
    for seed in range(101,106):
        for workload in ('uniform','hot90'):
            for c in chosen:
                s=dict(c['spec'],id=f"B3_{c['spec']['kind']}_{workload}_seed{seed}",warmup=2048,requests=4096,
                       trace_seed=seed,oram_seed=seed+900,workload=workload,experiment_class='formal_tuned')
                alias=next((x for x in core if comparable(x)==comparable(s)),None)
                if alias:aliases.append(dict(id=s['id'],source_id=alias['id'],source_folder='formal_core',spec=s))
                else:plans.append(s)
    # Verify the object-size formula on actual completed records, not merely another formula.
    checked=[]
    import optimized_oram as ref
    for path in sorted((PACKAGE/'results/formal_core').glob('*.json')):
        row=json.loads(path.read_text());cs=[ref.Config(**c) for c in row['configs']]
        assert object_storage(cs)==row['server_storage']['total_bytes']
        checked.append(dict(id=row['spec']['id'],sha256=sha(path)))
    result=dict(candidates=candidates,selected=[c['candidate_id'] for c in chosen],selection='minimum upper endpoint of periodic total bytes, within the published finite candidate set and common resource ceilings',
        fair_comparison_limits=['not globally optimal','no XOR, tree-top cache or mixed per-recursion-layer parameter search',
            'Path/Deferred/Ring lifetime proofs are not supplied by the selective gate','resource figures exclude allocator and peak scratch'],
        measured_storage_regression=checked,source_hashes=source_identity())
    dest=PACKAGE/'results/fair_tuning_candidates.json';assert not dest.exists();save(dest,result)
    planpath=PACKAGE/'formal_tuned_plan.json';assert not planpath.exists()
    save(planpath,dict(specs=plans,aliases=aliases,stage='B3',candidate_file_sha256=sha(dest),source_hashes=source_identity(),
                      initial_observations=50,selection_not_from_run_outcomes=True))
    lines=['# 双方有限候选调优：执行前选择','','以下全部为周期成本模型；正式配对测量由具名计划单独执行。','',
           '| 方案 | Z/A/S | map块B | terminal上限 | 预测bytes/op | 服务器对象MiB | selective gate |',
           '|---|---|---:|---:|---:|---:|---|']
    for c in chosen:
        s=c['spec'];lines.append(f"| {s['kind']} | {'/'.join(map(str,s['profile']))} | {s['map_B']} | {s['terminal_bytes']} | {float(c['periodic_model']['total']['upper']):,.2f} | {c['server_object_bytes']/(1<<20):.2f} | {'通过适用SOC3 gate' if c['selective_gate'] else '非该gate覆盖的基线'} |")
    ring=next(c for c in chosen if c['spec']['kind']=='ring');r0=next(c for c in chosen if c['spec']['kind']=='r0')
    gain=100*(1-Decimal(r0['periodic_model']['total']['upper'])/Decimal(ring['periodic_model']['total']['upper']))
    lines += ['',f'在此有限集合中，R0 相对 Ring 的周期模型节省为 **{gain:.2f}%**；不是实测结果，也不是全局最优比较。',
              '',f'全部 {len(candidates)} 个候选及拒绝理由保存在 JSON 中。各方共用4GiB服务器对象上限及256MiB持久payload/terminal预算；后一口径不等于真实峰值可信内存。',
              '同种方案在所有递归层使用同一Z/A/S；未搜索混合层参数。安全强度完全一致的基线标签仍需补齐各自的证明绑定。']
    (PACKAGE/'09_有限候选调优方案.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(candidates=len(candidates),new_runs=len(plans),aliases=len(aliases),predicted_R0_saving_pct=float(gain))))

if __name__=='__main__':main()
