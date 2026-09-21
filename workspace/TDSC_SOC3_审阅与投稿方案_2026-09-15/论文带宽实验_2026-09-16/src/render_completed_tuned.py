"""A single vector figure and raw tables for the completed tuned comparison."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import math,statistics,csv


def stats(xs):
    assert len(xs)==5
    m=statistics.mean(xs);half=2.7764451051977987*statistics.stdev(xs)/math.sqrt(5)
    return dict(mean=m,ci95=[m-half,m+half],values=xs)


def main():
    source=PACKAGE/'results/tuned_completed_snapshot.json';a=json.loads(source.read_text())
    assert a['status']=='passed' and a['runs']==50 and not a['repeat_gate_triggered']
    assert a['source_identity']==source_identity()
    assert a['freezer_sha256']==sha(PACKAGE/'src/freeze_tuned_completed.py')
    rows={}
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];rows[ref['id']]=json.loads(p.read_text())
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,
        'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none','savefig.dpi':180})
    fig,axes=plt.subplots(1,2,figsize=(11.8,5.4))
    names={'path':'Path','deferred':'Deferred','sde':'SDE','ring':'Ring','r0':'R0'}
    kinds=list(names);pairs=[('path','sde'),('deferred','sde'),('ring','r0')]
    colors=['#326A91','#D58B38'];series=[]
    for wi,(workload,label) in enumerate([('uniform','Uniform'),('hot90','Hot-90')]):
        shift=(-.19,.19)[wi]
        for i,kind in enumerate(kinds):
            ids=[f'B3_{kind}_{workload}_seed{seed}' for seed in range(101,106)]
            vals=[rows[x]['phases']['measurement']['total_bytes']/rows[x]['spec']['requests'] for x in ids]
            summary=stats(vals);y=summary['mean']/1024;lo,hi=[v/1024 for v in summary['ci95']]
            axes[0].bar(i+shift,y,.34,color=colors[wi],label=label if i==0 else None)
            axes[0].errorbar(i+shift,y,yerr=[[y-lo],[hi-y]],fmt='none',color='#303030',capsize=3,lw=.9)
            axes[0].text(i+shift,hi+(6,23)[wi],f'{y:.1f}',ha='center',fontsize=8)
            series.append(dict(panel='absolute',metric='bytes_per_request',kind=kind,workload=workload,ids=ids,**summary))
        for i,(base,var) in enumerate(pairs):
            ids=[[f'B3_{kind}_{workload}_seed{seed}' for kind in (base,var)] for seed in range(101,106)]
            vals=[100*(1-rows[y]['phases']['measurement']['total_bytes']/rows[x]['phases']['measurement']['total_bytes']) for x,y in ids]
            summary=stats(vals);m=summary['mean'];lo,hi=summary['ci95']
            axes[1].bar(i+shift,m,.34,color=colors[wi],label=label if i==0 else None)
            axes[1].errorbar(i+shift,m,yerr=[[m-lo],[hi-m]],fmt='none',color='#303030',capsize=3,lw=.9)
            axes[1].text(i+shift,hi+(.55,2.05)[wi],f'{m:.2f}',ha='center',fontsize=8)
            series.append(dict(panel='paired',metric='bytes_saving_pct',baseline=base,variant=var,workload=workload,ids=ids,**summary))
    axes[0].set(xticks=range(5),xticklabels=list(names.values()),ylabel='Total communication (KiB / request)',
        ylim=(0,580),title='(a) Absolute cost after separate tuning')
    axes[1].set(xticks=range(3),xticklabels=[f'{names[b]} to {names[v]}' for b,v in pairs],
        ylabel='Paired communication reduction (%)',ylim=(0,43),title='(b) Reduction vs each stated baseline')
    for ax in axes:
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True);ax.legend(frameon=False,ncol=2,loc='upper right',fontsize=8)
    fig.subplots_adjust(left=.075,right=.99,top=.88,bottom=.33,wspace=.28)
    fig.text(.075,.19,'N = 16,384; data B = 4,096 bytes; map B = 256 bytes; R = 256; five paired seeds, mean and 95% t intervals.\n'
        'Path / Deferred / SDE: Z4/A3; Ring: Z7/A6/S9; R0: Z7/A6/S6. 2,048 warmup + 4,096 measured requests.',fontsize=8,color='#454545')
    fig.text(.075,.085,'All serialized protocol bytes, including authentication and recursive maps. Predeclared search: 72 candidates.\n'
        'Common resource ceilings; actual storage differs. Finite window, empirical Path Z4, no global-optimum or latency claim.',fontsize=8,color='#454545')
    outputs=[];stem='completed_tuned_bandwidth'
    for p in [PACKAGE/'output/pdf'/f'{stem}.pdf',PACKAGE/'figures'/f'{stem}.svg',PACKAGE/'figures'/f'{stem}.png']:
        p.parent.mkdir(parents=True,exist_ok=True);fig.savefig(p,bbox_inches='tight')
        outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    plt.close(fig)
    dp=PACKAGE/'figures/completed_tuned_data.json'
    save(dp,dict(source_sha256=sha(source),series=series,raw_units='bytes/request or percent',
        absolute_plot_scale=1024,configs=[dict(kind=c['kind'],workload=c['workload'],resource=c['resource']) for c in a['cells']]))
    rp=PACKAGE/'tables/tuned_50_runs.csv';fields=['id','kind','workload','seed','N','B','Z','A','S','R','map_B','requests',
        'measurement_bytes','bytes_per_request','rpc_per_request','source_path','source_sha256']
    with rp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for ref in a['receipts']:
            r=rows[ref['id']];s=r['spec'];z,ar,ss=s['profile']
            w.writerow(dict(id=s['id'],kind=s['kind'],workload=s['workload'],seed=s['trace_seed'],N=s['N'],B=s['B'],
                Z=z,A=ar,S=ss,R=s['R'],map_B=s['map_B'],requests=s['requests'],
                measurement_bytes=r['phases']['measurement']['total_bytes'],bytes_per_request=r['bytes_per_request'],
                rpc_per_request=r['rpc_per_request'],source_path=ref['path'],source_sha256=ref['sha256']))
    ep=PACKAGE/'tables/tuned_6_comparisons.csv';fields=['baseline','variant','workload','n','mean_saving_pct','ci95_low','ci95_high']
    with ep.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for s in series:
            if s['panel']=='paired':w.writerow(dict(baseline=s['baseline'],variant=s['variant'],workload=s['workload'],n=5,
                mean_saving_pct=s['mean'],ci95_low=s['ci95'][0],ci95_high=s['ci95'][1]))
    for p in (rp,ep):outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    report=PACKAGE/'47_调优主比较完整图表.md'
    md=['# 调优主比较：50次完整重复与主图','',
        'B3五个方案、uniform/hot90两种负载、每格五个种子全部通过独立审计。每个配置是从预声明72个有限候选中按各自周期模型选择，参数在测量前固定。输入、块大小、递归打包、暖机和计量窗口逐种子对应。','',
        '| 比较 | 负载 | n | 总字节减少 | 95%配对区间 |','|---|---|---:|---:|---|']
    for s in series:
        if s['panel']=='paired':md.append(f"| {names[s['baseline']]} → {names[s['variant']]} | {s['workload']} | 5 | {s['mean']:.3f}% | [{s['ci95'][0]:.3f}%, {s['ci95'][1]:.3f}%] |")
    md+=['','## 图、表与口径','',
        '- `output/pdf/completed_tuned_bandwidth.pdf`：左侧绝对通信KiB/request，右侧明确分母的配对减少率；另有SVG及PNG。',
        '- `tables/tuned_50_runs.csv`：全部原始观测，附配置、原始字节、收据路径和SHA256。',
        '- `tables/tuned_6_comparisons.csv`：六组比较；减少率先按种子计算，再求均值和95% t区间。',
        '- `figures/completed_tuned_data.json`：16组图元数值，每组绑定五个原始ID；不从部分组或汇总摘要复制最终结果。','',
        'N16384，数据块4096B，位置表块256B，终端map上限8192B。Path/Deferred/SDE用Z4/A3，Ring用Z7/A6/S9，R0用Z7/A6/S6；各层R256。每次测量前完整初始化，暖机2048请求，再测4096请求，包含认证、控制、递归与所有维护的应用层双向字节；初始化单独计费，不包括TCP/TLS。','',
        '双方采用共同服务器对象4GiB、持久payload+terminal256MiB筛选上限，但实际对象使用不同，也未测得完整可信峰值。Ring约1067.27MiB、R0约870.21MiB的真实对象差异另见44号文档。不能把共同上限写成相等实际内存。','',
        '这是当前预声明有限候选和有限测量窗口的比较，未穷尽XOR、缓存和所有递归/参数组合，不作全局最优或优于所有ORAM主张。Path Z4是经验强基线；另行执行的Path Z5/R258补充组不混入本图。基线安全准入边界见45号文档，整体论文尚未完成。',
        '', '数值重算与最终PDF渲染审阅状态分别记录在 `results/tuned_exports_audit.json` 和 `results/tuned_visual_review.json`。']
    report.write_text('\n'.join(md)+'\n',encoding='utf-8');outputs.append(dict(path=str(report.relative_to(PACKAGE)),sha256=sha(report)))
    save(PACKAGE/'results/tuned_exports.json',dict(status='generated',source_sha256=sha(source),
        generator_sha256=sha(__file__),data_sha256=sha(dp),outputs=outputs,visual_review_pending=True))
    print(json.dumps(dict(status='generated',pdfs=1,series=len(series),raw_records=50)),flush=True)


if __name__=='__main__':main()
