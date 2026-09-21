"""Publication vector figure and auditable Markdown tables for complete B2."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import statistics

def interval(s):return f"{s['mean']:.3f}% [{s['ci95'][0]:.3f}%, {s['ci95'][1]:.3f}%]"

def main():
    source=PACKAGE/'results/ablation_complete_audit.json';a=json.loads(source.read_text())
    assert a['status']=='passed' and a['observations']==45 and not a['repeat_gate_triggered']
    for r in a['receipts']:assert sha(PACKAGE/r['path'])==r['sha256']
    out=PACKAGE/'figures';out.mkdir(exist_ok=True);pdfdir=PACKAGE/'output/pdf';pdfdir.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'svg.fonttype':'none','figure.dpi':150,'savefig.dpi':180})
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.8))
    groups=[('compact_without_fusion_pct','Compact\nfusion off'),('compact_with_fusion_pct','Compact\nfusion on'),
            ('fusion_without_compact_pct','Fusion\ncompact off'),('fusion_with_compact_pct','Fusion\ncompact on')]
    plotted=[]
    for family,color,shift,label in [('43','#326a91',-.18,'Z4 / A3 / S3'),('76','#d58b38',.18,'Z7 / A6 / S6')]:
        for i,(key,text) in enumerate(groups):
            s=next(e['bytes_saving'] for e in a['effects'] if e['family']==family and e['effect']==key)
            mean=s['mean'];lo,hi=s['ci95'];x=i+shift
            axes[0].bar(x,mean,.32,color=color,label=label if i==0 else None)
            axes[0].errorbar(x,mean,yerr=[[mean-lo],[hi-mean]],fmt='none',color='#292929',capsize=3,linewidth=.9)
            axes[0].text(x,hi+.08,f'{mean:.2f}',ha='center',fontsize=8)
            plotted.append(dict(panel='conditional',family=family,effect=key,metric='bytes_saving',mean=mean,ci95=[lo,hi]))
    axes[0].set(xticks=range(4),xticklabels=[x[1] for x in groups],ylabel='Total communication reduction (%)',ylim=(0,3.7),title='(a) Separate header and fusion effects')
    axes[0].legend(loc='upper left',ncol=2,frameon=False,fontsize=8,bbox_to_anchor=(0,1.19))
    for metric,color,shift,label in [('bytes_saving','#326a91',-.18,'Bytes'),('rpc_saving','#d58b38',.18,'RPCs')]:
        for i,e in enumerate(a['ladder'][:4]):
            s=e[metric];mean=s['mean'];lo,hi=s['ci95'];x=i+shift
            axes[1].bar(x,mean,.32,color=color,label=label if i==0 else None)
            axes[1].errorbar(x,mean,yerr=[[mean-lo],[hi-mean]],fmt='none',color='#292929',capsize=3,linewidth=.9)
            axes[1].text(x,hi+.6 if mean>=0 else lo-.6,f'{mean:.2f}',ha='center',va='bottom' if mean>=0 else 'top',fontsize=8)
            plotted.append(dict(panel='ladder',before=e['before'],after=e['after'],metric=metric,mean=mean,ci95=[lo,hi]))
    axes[1].set(xticks=range(4),xticklabels=['Smaller map\n4096 to 512 B','Compact\nheader','Fusion','Z/A/S +\ngeometry'],
                ylabel='Conditional reduction (%)',ylim=(-5,22),title='(b) Incremental steps in the chosen order')
    axes[1].legend(loc='upper left',ncol=2,frameon=False,fontsize=8,bbox_to_anchor=(0,1.19))
    for ax in axes:
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True);ax.axhline(0,color='#777777',lw=.7)
    fig.subplots_adjust(left=.07,right=.99,top=.78,bottom=.25,wspace=.27)
    fig.text(.07,.07,'R0 ablation | N = 16,384; data blocks = 4,096 B; uniform workload; five paired runs per cell.\n'
        '2,048 warmup + 4,096 measured requests; bars show mean and 95% t intervals.\n'
        'All protocol bytes included. Steps are conditional and not additive; parameter retuning also changes tree geometry.',fontsize=8,color='#4a4a4a')
    outputs=[]
    for p in (pdfdir/'completed_r0_ablation.pdf',out/'completed_r0_ablation.svg',out/'completed_r0_ablation.png'):
        fig.savefig(p,bbox_inches='tight');outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    plt.close(fig)
    save(out/'completed_r0_ablation_data.json',dict(source_sha256=sha(source),bars=plotted))
    md=['# R0完整消融：字节、RPC和可追溯表','','45/45个观测已完成独立收据审计；每格5次，9格。N16384，数据块4096B，uniform，暖机2048请求、测量4096请求。固定R256和terminal map预算32768B。这里是执行账单证据，基线执行归约/完整论文仍未完成。','',
        '小map是位置表块4096B→512B，数据块大小不变。compact和fusion各有独立四格；不再把一起开启后的联合收益归到fusion。参数重调同时改变Z/A/S、树高和递归几何，不能单独归因于某一个参数。','',
        '| 参数族 | 条件效应 | 字节减少：均值与95%区间 | RPC减少：均值与95%区间 |','|---|---|---|---|']
    labels={'fusion_without_compact_pct':'fusion，compact关','fusion_with_compact_pct':'fusion，compact开',
        'compact_without_fusion_pct':'compact，fusion关','compact_with_fusion_pct':'compact，fusion开'}
    for e in a['effects']:
        if e['effect']=='interaction_bytes':continue
        md.append(f"| {e['family']} | {labels[e['effect']]} | {interval(e['bytes_saving'])} | {interval(e['rpc_saving'])} |")
    md+=['','| 顺序步骤 | 字节减少：均值与95%区间 | RPC减少：均值与95%区间 |','|---|---|---|']
    titles=['小map','compact header','fusion','Z/A/S与递归几何重调','起点到终点的联合变化']
    for label,e in zip(titles,a['ladder']):md.append(f"| {label} | {interval(e['bytes_saving'])} | {interval(e['rpc_saving'])} |")
    md+=['','联合变化按每个种子的起点和终点直接相除，再对五个减少率求均值。不能相加步骤百分比，也不能把均值比例直接相乘替代配对估计。负收益保留：小map在本配置中减少字节但增加约2%的RPC。fusion减少RPC不等于已经测得延迟加速。','',
        '交互项以a−b−c+d字节/请求定义，Z4族为442.56，95%区间[-1018.68,1903.79]；Z7族为−94.12，区间[-1251.74,1063.51]。两者区间均覆盖零，不能宣称显著交互。运行成本CV均未超过10%，百分比效应区间半宽均未超过5个百分点，未触发预设追加重复门槛。','',
        '## 九格绝对开销','','| 格 | n | 平均字节/请求 | 平均RPC/请求 |','|---|---:|---:|---:|']
    for c in a['cells']:md.append(f"| {c['cell']} | 5 | {c['bytes_per_request']['mean']:,.2f} | {c['rpc_per_request']['mean']:.4f} |")
    md+=['','## 全部45个观测','','别名指向原先已执行的相同配置，不重复计为新执行；独立审计核对spec、输入/答案摘要、源码身份、全部账单、RPC连续序号、递归时钟与分窗口和。来源路径与SHA256见results/ablation_complete_audit.json。','',
        '| 名义ID | 字节/请求 | RPC/请求 |','|---|---:|---:|']
    for r in sorted(a['raw'],key=lambda x:x['id']):md.append(f"| {r['id']} | {r['bytes_per_request']:,.4f} | {r['rpc_per_request']:.6f} |")
    md+=['','图为output/pdf/completed_r0_ablation.pdf，另有figures下的SVG与PNG。figures/completed_r0_ablation_data.json逐柱绑定原始统计；结果收据、模型口径和生成身份分开保存。没有以Python执行时间代替CPU、延迟或内存实测。']
    p=PACKAGE/'34_R0完整消融结果.md';p.write_text('\n'.join(md)+'\n',encoding='utf-8');outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    save(PACKAGE/'results/ablation_exports.json',dict(status='generated',source_sha256=sha(source),generator_sha256=sha(__file__),
        data_sha256=sha(out/'completed_r0_ablation_data.json'),outputs=outputs,visual_review_pending=True))
    print(json.dumps(dict(status='generated',pdf=1,svg=1,table_observations=45,bars=len(plotted))))

if __name__=='__main__':main()

