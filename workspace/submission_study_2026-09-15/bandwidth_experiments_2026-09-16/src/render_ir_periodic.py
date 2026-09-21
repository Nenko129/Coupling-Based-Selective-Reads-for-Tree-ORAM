"""Export the completed raw-map IR period-window batch, never partial cells."""
from common import *
import statistics
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    source=PACKAGE/'results/ir_periodic_statistics.json';stats=json.loads(source.read_text())
    assert stats['status']=='complete_receipts_audited' and stats['completed']==stats['expected']==60
    assert len(stats['effects'])==14 and all(e['effect']['n']==5 and e['needs_more_repeats'] is False for e in stats['effects'])
    records=[]
    for item in stats['receipts']:
        p=PACKAGE/item['path'];assert sha(p)==item['sha256'];r=json.loads(p.read_text())
        s=r['spec'];m=r['phases']['measurement']
        assert s['requests']==6144 and m['public_slots']==49152 and s['warmup']==1536
        records.append(dict(spec=s,measurement=m,bytes_per_request=r['bytes_per_request'],source=item))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'svg.fonttype':'none','figure.dpi':150,'savefig.dpi':180})
    fig,(left,right)=plt.subplots(1,2,figsize=(11.2,4.7),gridspec_kw={'width_ratios':[1.3,1]})
    plotted=[]
    configs=[('uniform',False),('uniform',True),('hot90',False),('hot90',True)]
    for base,color,offset,label in [('path','#486da6',-.18,'SDE vs Path'),('deferred','#188977',.18,'SDE vs Deferred')]:
        for i,(workload,dwb) in enumerate(configs):
            e=next(e for e in stats['effects'] if e['axis']=='backend' and e['before']==base and e['condition']==['depth',dwb,workload])
            mean=e['effect']['mean'];lo,hi=e['effect']['ci95']
            left.bar(i+offset,mean,.32,color=color,label=label if i==0 else None)
            left.errorbar(i+offset,mean,yerr=[[mean-lo],[hi-mean]],fmt='none',color='#303030',capsize=3,linewidth=1)
            left.text(i+offset,hi+.30,f'{mean:.2f}',ha='center',va='bottom',fontsize=8)
            plotted.append(dict(panel='a',axis='backend',condition=e['condition'],before=e['before'],after=e['after'],effect=e['effect'],pairs=e['per_seed']))
    left.set(title='(a) Selective backend replacement',xticks=range(4),
        xticklabels=['Uniform\nDWB off','Uniform\nDWB on','Hot 90%\nDWB off','Hot 90%\nDWB on'],
        ylabel='Reduction in total serialized bytes (%)',ylim=(0,24))
    left.legend(loc='upper left',frameon=False,fontsize=8,ncol=2)
    for workload,color,offset,label in [('uniform','#486da6',-.12,'Uniform'),('hot90','#bc6b37',.12,'Hot 90%')]:
        for i,kind in enumerate(('path','deferred','sde')):
            e=next(e for e in stats['effects'] if e['axis']=='dwb' and e['condition']==['depth',kind,workload])
            mean=e['effect']['mean'];lo,hi=e['effect']['ci95']
            right.errorbar(i+offset,mean,yerr=[[mean-lo],[hi-mean]],fmt='o',markersize=5,color=color,capsize=4,
                label=label if i==0 else None)
            right.annotate(f'{mean:+.3f}',(i+offset,hi if workload=='uniform' else lo),xytext=(0,9 if workload=='uniform' else -15),
                textcoords='offset points',ha='center',fontsize=8,color=color)
            plotted.append(dict(panel='b',axis='dwb',condition=e['condition'],before=e['before'],after=e['after'],effect=e['effect'],pairs=e['per_seed']))
    right.axhline(0,color='#555555',linewidth=.8,linestyle='--')
    right.set(title='(b) DWB off to on: fixed public slots',xticks=range(3),xticklabels=['Path','Deferred','SDE'],
        ylabel='Reduction in total serialized bytes (%)',ylim=(-.08,.095),xlim=(-.55,2.55))
    right.legend(loc='upper left',frameon=False,fontsize=8,ncol=2)
    for ax in (left,right):ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    fig.suptitle('IR integrated pipeline: complete-period window',fontsize=12,y=.985)
    fig.subplots_adjust(top=.83,bottom=.30,left=.07,right=.98,wspace=.32)
    fig.text(.07,.035,'N = 4,096; B = 64 B; depth profile; raw recursive maps + LLC + fixed-slot DWB.\n'
        '1,536 warmup + 6,144 measured requests; 49,152 measured public slots; five paired runs; 95% t intervals.\n'
        'Four Deferred/SDE service cycles; Path uses the same window. Initialization/alignment are billed separately.\n'
        'Finite window, not a steady-state claim. Dirty LLC entries may remain. IR-Stash is not included.',fontsize=8,color='#555555')
    out=PACKAGE/'output/pdf';out.mkdir(parents=True,exist_ok=True);figdir=PACKAGE/'figures';figdir.mkdir(exist_ok=True)
    outputs=[]
    for ext in ('pdf','svg','png'):
        p=(out if ext=='pdf' else figdir)/f'completed_ir_periodic.{ext}';fig.savefig(p);outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    plt.close(fig)
    data=dict(source_sha256=sha(source),runs=records,effects=stats['effects'],plotted=plotted,
        scope=stats['scope'],endpoint=stats['endpoint'],security_proof=False,latency_claim=False,steady_state_claim=False)
    dp=figdir/'completed_ir_periodic_data.json';save(dp,data);outputs.append(dict(path=str(dp.relative_to(PACKAGE)),sha256=sha(dp)))
    md=['# IR完整周期图表与原始表','',
        '60/60正式运行，12格各5次。14组配对效应全部保留，95%区间为逐种子相对节省的Student-t区间；未触发预定义追加重复门槛。',
        '', '图左侧区分Path和同维护策略Deferred两种分母，图右侧单独报告固定公共时隙下DWB开关。右轴单位也是百分比，但量程显著更小。',
        'SDE对Deferred约19.195%–19.216%，对Path约9.750%–9.773%。DWB开关对Path/Deferred总字节严格为零；SDE两个区间均覆盖零，不作为确定通信收益。',
        '', '完整配置与前端工作量见21号文档。图为 `output/pdf/completed_ir_periodic.pdf`；SVG、PNG及全部60行和14组效应在 `figures/completed_ir_periodic*`。',
        '', '## 14组配对效应','',
        '| 轴 | 条件 | 比较 | n | 基线bytes/op | 组合bytes/op | 节省 | 95%区间 |','|---|---|---|---:|---:|---:|---:|---|']
    for e in stats['effects']:
        v=e['effect'];lo,hi=v['ci95']
        md.append(f"| {e['axis']} | {e['condition']} | {e['before']} → {e['after']} | {v['n']} | {e['baseline_mean_bytes']:.6f} | {e['variant_mean_bytes']:.6f} | {v['mean']:.6f}% | [{lo:.6f}%, {hi:.6f}%] |")
    md+=['','## 全部60行测量原始表','',
        '每行均测量6144个完成请求、49152个公共时隙。完整逐类字节、前端计数、spec、来源路径及SHA256保存在配套JSON，初始化/对齐/预热账单留在被绑定的原始收据中。','',
        '| ID | 总字节 | bytes/op | RPC | 前台回写 | DWB完成 | dummy槽 | dirty留存 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in records:
        m=r['measurement'];f=m['frontend_metrics']
        md.append(f"| {r['spec']['id']} | {m['total_bytes']} | {r['bytes_per_request']:.6f} | {m['rpc']} | {f.get('foreground_writebacks',0)} | {f.get('dwb_completed',0)} | {f.get('dummy_slots',0)} | {f.get('dirty_resident',0)} |")
    md+=['','## 范围与审阅','',
        '实验包含异质桶、缓存前6层、raw递归位置表、PLB和LLC、DWB及填充流量。IR-Stash skip和压缩map未包含；不称完整原生IR、稳态、持久化屏障或网络延迟实验。',
        '独立导出核验重新读取60份运行收据、重算14组均值/区间，检查图数据绑定及PDF矢量字体；版面审阅单独保存，不从数值检查自动推断。']
    doc=PACKAGE/'41_IR完整周期图表与数据核验.md';doc.write_text('\n'.join(md)+'\n',encoding='utf-8')
    outputs.append(dict(path=str(doc.relative_to(PACKAGE)),sha256=sha(doc)))
    save(PACKAGE/'results/ir_periodic_exports.json',dict(status='generated',source_sha256=sha(source),generator_sha256=sha(__file__),
        outputs=outputs,runs=60,comparisons=14,visual_review_pending=True))
    print(json.dumps(dict(runs=60,comparisons=14,pdfs=1)))


if __name__=='__main__':main()
