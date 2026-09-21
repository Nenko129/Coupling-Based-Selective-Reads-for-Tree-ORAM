"""Separate B3 finite-window observations from full-period cost expectations."""
from common import *
from collections import defaultdict
from fractions import Fraction as F
import statistics


def main():
    source=PACKAGE/'results/tuned_completed_snapshot.json';a=json.loads(source.read_text())
    assert a['status']=='passed' and a['runs']==50
    groups=defaultdict(list);by_id={};clocks=[]
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];r=json.loads(p.read_text());s=r['spec'];by_id[s['id']]=r
        m=r['expected_periodic_cost']['total'];lo=F(m['lower']);hi=F(m['upper']);assert 0<lo<=hi
        actual=F(r['phases']['measurement']['total_bytes'],s['requests'])
        groups[s['kind'],s['workload']].append(dict(id=s['id'],seed=s['trace_seed'],model_lower=lo,model_upper=hi,
            actual=actual,error_lower=100*(actual/hi-1),error_upper=100*(actual/lo-1)))
        initial=0
        for c,clock,q in zip(r['configs'],r['final_clock'],r['phases']['measurement']['backend_requests']):
            initial+=c['N'];start=initial+s['warmup'];assert q==s['requests'] and clock['t']==start+q
            period=c['A']*(1<<c['L'])
            clocks.append(dict(id=s['id'],tree=c['tree'],kind=c['kind'],measurement_start=start,measurement_end=clock['t'],
                measured_accesses=q,scheduled_cycle_applicable=c['kind']!='path',
                reference_period=period,start_phase=start%period,end_phase=clock['t']%period,
                period_fraction=str(F(q,period)),is_integer_number_of_periods=q%period==0))
    cells=[]
    for key,rs in sorted(groups.items()):
        assert sorted(r['seed'] for r in rs)==list(range(101,106))
        assert len({(r['model_lower'],r['model_upper']) for r in rs})==1
        lower,upper=rs[0]['model_lower'],rs[0]['model_upper'];mean=sum((r['actual'] for r in rs),F(0))/5
        cells.append(dict(kind=key[0],workload=key[1],n=5,model_lower=str(lower),model_upper=str(upper),
            observed_mean_bytes=float(mean),relative_model_difference_pct=[float(100*(mean/upper-1)),float(100*(mean/lower-1))],
            ids=[r['id'] for r in rs]))
    contrasts=[]
    for e in a['effects']:
        pair=e['pairs'][0];left=by_id[pair['baseline_id']];right=by_id[pair['variant_id']]
        lm=left['expected_periodic_cost']['total'];rm=right['expected_periodic_cost']['total']
        lo=100*(1-F(rm['upper'])/F(lm['lower']));hi=100*(1-F(rm['lower'])/F(lm['upper']))
        contrasts.append(dict(baseline=e['baseline'],variant=e['variant'],workload=e['workload'],
            full_period_model_gain_pct=[float(lo),float(hi)],finite_window_paired_gain_pct=e['bytes_saving']['mean'],
            finite_window_ci95=e['bytes_saving']['ci95'],
            difference_percentage_points=[e['bytes_saving']['mean']-float(hi),e['bytes_saving']['mean']-float(lo)]))
    assert all(c['period_fraction']=='1/12' for c in clocks if c['tree']==0)
    assert all(c['period_fraction']=='16/3' for c in clocks if c['tree']==1)
    assert {c['start_phase'] for c in clocks if c['tree']==0}=={18432}
    assert {c['end_phase'] for c in clocks if c['tree']==0}=={22528}
    out=dict(status='passed',source_sha256=sha(source),auditor_sha256=sha(__file__),runs=50,
        cells=cells,contrasts=contrasts,clocks=clocks,
        confirms_full_period_measurement=False,steady_state_claim=False,
        model_scope='existing complete-period expected byte ledger, not a prediction interval for this finite warm-start window',
        no_extrapolation_from_small_calibration_error=True)
    save(PACKAGE/'results/tuned_model_window_audit.json',out)
    md=['# 调优结果：有限窗口与完整周期期望分开报告','',
        '47号主图是真实执行的有限窗口结果。本报告核对50份原始收据的模型值、实际时钟和测量字节，避免把它重述为完整周期或稳态收益。','',
        '## 实际测量覆盖','',
        '对Deferred/SDE/Ring/R0，数据层的scheduled周期均为49152次后端访问。测量从t=18432到22528，仅4096次，即1/12周期；位置表层周期768次，测量4096次为16/3周期。两层测量都不是整数周期。Path每次随机路径读写，不采用scheduled bit-reversal周期，因此这些长度对Path只作参考。','',
        '这些窗口与初始化、暖机参数均在测量前固定，所有配对臂采用对应输入与相同公开时钟。有限窗口比较有效，但五个随机种子的区间描述该固定窗口下的随机波动，不包含换维护相位或延长运行时间所带来的变化。','',
        '| 后端 | 负载 | 完整周期期望bytes/op | 当前窗口实测均值 | 相对模型差异 |','|---|---|---:|---:|---:|']
    for c in cells:
        mid=(F(c['model_lower'])+F(c['model_upper']))/2;diff=c['relative_model_difference_pct']
        md.append(f"| {c['kind']} | {c['workload']} | {float(mid):,.2f} | {c['observed_mean_bytes']:,.2f} | {(diff[0]+diff[1])/2:.4f}% |")
    md+=['','| 比较 | 负载 | 完整周期模型节省 | 当前窗口配对节省 | 差值（百分点） |','|---|---|---:|---:|---:|']
    for c in contrasts:
        mid=sum(c['full_period_model_gain_pct'])/2;delta=sum(c['difference_percentage_points'])/2
        md.append(f"| {c['baseline']} → {c['variant']} | {c['workload']} | {mid:.3f}% | {c['finite_window_paired_gain_pct']:.3f}% | {delta:+.3f} |")
    md+=['','## 论文表述边界','',
        'Ring→R0的约25.37%–25.39%是本次已测窗口的结果，完整周期模型约24.58%。二者分栏报告，不把较大的实测比例改称稳态收益；这里也没有从差异直接认定模型错误或证明全部差异由维护相位造成。',
        '', '较小N256/B64完整周期校准的最大平均模型偏差约0.15648%，不能外推到本N16384/B4096且非完整周期的窗口。本轮保留所有模型差异，不重新选择有利窗口，不混合两类分母。若另作目标规模稳态主张，需要覆盖完整周期及相位的额外证据；当前正文限定为具名有限窗口。','',
        '`results/tuned_model_window_audit.json`保存100行逐层时钟、10格模型/实测开销和6组差值，绑定不可变B3完整快照及原始收据。报告模型数值为区间中点显示，机器数据保留上下界。']
    (PACKAGE/'48_调优有限窗口与周期期望核对.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',runs=50,tree_windows=100,contrasts=6)))


if __name__=='__main__':main()
