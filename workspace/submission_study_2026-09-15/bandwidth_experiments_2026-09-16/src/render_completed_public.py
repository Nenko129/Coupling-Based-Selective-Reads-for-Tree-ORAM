"""Public trace figures use observed window ranges, never population CIs."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    source=PACKAGE/'results/public_completed_audit.json';s=json.loads(source.read_text())
    assert s['status']=='passed' and s['runs']==80 and s['comparisons']==8
    raw=[]
    for receipt in s['receipts']:
        p=PACKAGE/receipt['path'];assert sha(p)==receipt['sha256'];r=json.loads(p.read_text())
        raw.append(dict(source=receipt,spec=r['spec'],trace=r['trace'],measurement=r['phases']['measurement'],
            bytes_per_request=r['bytes_per_request'],rpc_per_request=r['rpc_per_request'],server_storage=r['server_storage'],
            frontend_memory_representation=r['frontend_memory_representation'],configs=r['configs'],scope=r['scope']))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'svg.fonttype':'none','figure.dpi':150,'savefig.dpi':180})
    fig,axes=plt.subplots(1,2,figsize=(9.8,4.5),sharey=True)
    for ax,family,title in zip(axes,('free_compressed','rho'),('Freecursive-style frontend','Rho-style two-tree frontend')):
        for base,variant,color,offset,label in [('deferred','sde','#188977',-.18,'SDE vs Deferred'),('ring','r0','#486da6',.18,'R0 vs Ring')]:
            for i,workload in enumerate(('Financial1_startkey','WebSearch1_startkey')):
                e=next(e for e in s['effects'] if (e['family'],e['workload'],e['baseline'],e['variant'])==(family,workload,base,variant))
                mean=e['mean'];lo,hi=e['range'];assert e['n']==5 and e['ci95'] is None
                ax.bar(i+offset,mean,.31,color=color,label=label if i==0 else None)
                ax.errorbar(i+offset,mean,yerr=[[mean-lo],[hi-mean]],fmt='none',color='#222222',capsize=4,linewidth=1)
                ax.text(i+offset,hi+.35,f'{mean:.2f}',ha='center',va='bottom',fontsize=9)
        ax.set(title=title,xticks=[0,1],xticklabels=['Financial1','WebSearch1'],ylim=(0,29),xlim=(-.55,1.55))
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    axes[0].set_ylabel('Reduction in total serialized bytes (%)')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.93),ncol=2,frameon=False)
    fig.suptitle('Public command-key locality replay',fontsize=12,y=.985)
    fig.subplots_adjust(left=.08,right=.98,top=.76,bottom=.30,wspace=.15)
    fig.text(.08,.045,'N = 16,384; B = 64 B; 2,048 warmup + 4,096 measured commands per window.\n'
        'Five preselected adjacent windows per trace. Whiskers: observed min-max, not confidence intervals.\n'
        'Counts all frontend/backend, authentication, maintenance and padding bytes in the implemented variants.\n'
        'Command start keys only; original I/O sizes and arrival times are not replayed. No native-system or latency claim.',fontsize=8,color='#555555')
    outputs=[]
    for ext in ('pdf','svg','png'):
        p=PACKAGE/('output/pdf' if ext=='pdf' else 'figures')/f'completed_public_workloads.{ext}'
        fig.savefig(p);outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    plt.close(fig)
    dp=PACKAGE/'figures/completed_public_workloads_data.json'
    save(dp,dict(source_sha256=sha(source),runs=raw,cells=s['cells'],effects=s['effects'],windows=s['windows'],
        statistical_unit=s['statistical_unit'],native_full_system=False,latency_claim=False))
    outputs.append(dict(path=str(dp.relative_to(PACKAGE)),sha256=sha(dp)))
    md=['# 公开访问记录：80次完整运行与组合带宽结果','',
        'Financial1和WebSearch1各选定5个相邻窗口，分别运行Freecursive压缩前端、ρ两树前端的Deferred/SDE/Ring/R0，全部80/80完成。每窗2048条暖机命令、4096条测量命令，N16384/B64；同族profile为Z4/A3/S4，PLB8、LLC32、ρ容量128、R256。不是双方独立调优结果。',
        '', '源数据来自UMass Trace Repository的Storage Performance Council访问记录；原始压缩文件、下载URL和SHA256在 `datasets/download_receipt.json`。独立重新解析61440条源命令，核对ASU/LBA键映射、操作、时间边界和命令长度元数据；另从版本历史独立重算全部返回值摘要。',
        '适配器将每个命令起始键映射为一个64B记录，保留重复键和读写顺序。未按原始I/O长度拆块、未回放到达时间，不能称完整块设备重放。五个相邻窗口并非工作负载总体的独立抽样；主表报告配对节省的均值和窗口最小—最大值，不给总体置信区间。',
        '', '## 8组完整配对结果','',
        '| 前端 | 公开记录 | 比较 | 基线bytes/op | selective bytes/op | 平均节省 | 五窗口范围 |','|---|---|---|---:|---:|---:|---|']
    for e in s['effects']:
        md.append(f"| {e['family']} | {e['workload'].replace('_startkey','')} | {e['baseline']} → {e['variant']} | {e['baseline_mean']:.3f} | {e['variant_mean']:.3f} | {e['mean']:.3f}% | [{e['range'][0]:.3f}%, {e['range'][1]:.3f}%] |")
    def bounds(family,variant):
        vals=[e['mean'] for e in s['effects'] if e['family']==family and e['variant']==variant]
        return f'{min(vals):.2f}%–{max(vals):.2f}%'
    md+=['', f"Freecursive组合SDE约{bounds('free_compressed','sde')}、R0约{bounds('free_compressed','r0')}；ρ组合SDE约{bounds('rho','sde')}、R0约{bounds('rho','r0')}。这些是当前两组公开窗口的总通信结果，不能外推为全部实际应用的平均收益。",
        '', '## ρ分账','',
        '各窗口均校验前树转录及字节完全相同，并用有理数验证：整体节省 = 原后端流量占比 × 后端自身节省。以下分别对窗口取均值；不能用均值的乘积替代逐窗口乘积的均值。','',
        '| 公开记录 | 比较 | 前树bytes/op均值 | 原后端占比均值 | 后端自身节省均值 | 整体节省均值 |','|---|---|---:|---:|---:|---:|']
    import statistics
    for e in s['effects']:
        if e['family']!='rho':continue
        ps=e['per_window'];mean=lambda k:statistics.mean(p[k] for p in ps)
        md.append(f"| {e['workload'].replace('_startkey','')} | {e['baseline']} → {e['variant']} | {mean('front_bytes'):.3f} | {100*mean('backend_share'):.3f}% | {mean('backend_saving_pct'):.3f}% | {e['mean']:.3f}% |")
    md+=['', '## 16格绝对通信与RPC','',
        '| 前端 | 记录 | 后端 | n | bytes/op均值 | 五窗口范围 | RPC/op均值 |','|---|---|---|---:|---:|---|---:|']
    for c in s['cells']:md.append(f"| {c['family']} | {c['workload'].replace('_startkey','')} | {c['kind']} | 5 | {c['mean']:.3f} | [{c['range'][0]:.3f}, {c['range'][1]:.3f}] | {c['rpc_mean']:.6f} |")
    md+=['', '## 证据和适用边界','',
        '- `output/pdf/completed_public_workloads.pdf`：8组总通信效应，误差线明确为窗口范围；另有SVG和PNG。',
        '- `figures/completed_public_workloads_data.json`：全部80行的spec、原始来源hash、真实字节分项、配置、服务器对象及前端内存记账；每个原始收据还单列初始化和暖机。',
        '- `results/public_completed_audit.json`：80份收据、10个源窗口、16个绝对开销格、8组效应及40个配对窗口。',
        '- `results/public_exports_audit.json`、`results/public_visual_review.json`：独立数值与PDF结构核验、最终版面审阅。',
        '', '实现范围沿用基础组合：Freecursive统一压缩map/PLB但无原生PMMAC/硬件控制器；ρ保留既定公开frame长度及可信Full PosMap条件，无ECC/compact/原生异步。参数R256和运行成功不提供缺失的组合安全归约。进程内真实协议字节不包含TCP/TLS，逻辑内存表也不代表可信峰值实测。',
        '这些范围随结果保留，避免把局部性回放或成功计费表误写成完整原生系统复现。']
    doc=PACKAGE/'42_公开负载完整结果与图表.md';doc.write_text('\n'.join(md)+'\n',encoding='utf-8')
    outputs.append(dict(path=str(doc.relative_to(PACKAGE)),sha256=sha(doc)))
    save(PACKAGE/'results/public_exports.json',dict(status='generated',source_sha256=sha(source),generator_sha256=sha(__file__),outputs=outputs,
        runs=80,comparisons=8,visual_review_pending=True))
    print(json.dumps(dict(runs=80,comparisons=8,pdfs=1)))


if __name__=='__main__':main()
