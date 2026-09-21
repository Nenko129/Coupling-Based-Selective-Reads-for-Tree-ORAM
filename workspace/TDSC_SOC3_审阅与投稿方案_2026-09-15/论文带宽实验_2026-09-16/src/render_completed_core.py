"""Completed B1 and static-component vector figures, with plotted raw IDs."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import math,statistics


def summarize(xs):
    assert len(xs)==5
    mean=statistics.mean(xs);half=2.7764451051977987*statistics.stdev(xs)/math.sqrt(5)
    return dict(mean=mean,ci95=[mean-half,mean+half],values=xs)


def main():
    source=PACKAGE/'results/core_components_complete_audit.json';a=json.loads(source.read_text())
    assert a['status']=='passed' and a['observations']==140 and not a['repeat_gate_triggered']
    assert a['auditor_sha256']==sha(Path(__file__).parent/'audit_completed_core_components.py')
    rows={}
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];rows[ref['id']]=json.loads(p.read_text())
    out=PACKAGE/'figures';pdfdir=PACKAGE/'output/pdf';pdfdir.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'svg.fonttype':'none','figure.dpi':150,'savefig.dpi':180})
    series=[];outputs=[]
    colors=['#326a91','#d58b38'];names={'path':'Path','deferred':'Deferred','sde':'SDE','ring':'Ring','gc_ring':'GC-Ring','r0':'R0'}

    def draw(ax,x,values,label,color,width=.32,scale=1,offset=.6):
        s=summarize(values);mean=s['mean']/scale;lo,hi=[z/scale for z in s['ci95']]
        ax.bar(x,mean,width,color=color,label=label)
        ax.errorbar(x,mean,yerr=[[mean-lo],[hi-mean]],fmt='none',color='#292929',capsize=3,linewidth=.9)
        ax.text(x,hi+offset,f'{mean:.1f}' if scale!=1 else f'{mean:.2f}',ha='center',fontsize=8)
        return s

    def decorate(ax):
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True);ax.axhline(0,color='#777777',lw=.6)

    def export(fig,stem):
        for p in (pdfdir/(stem+'.pdf'),out/(stem+'.svg'),out/(stem+'.png')):
            fig.savefig(p,bbox_inches='tight');outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
        plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11.2,4.8))
    protocols=['path','deferred','sde','ring','gc_ring','r0']
    pairs=[('path','sde'),('deferred','sde'),('ring','gc_ring'),('ring','r0'),('gc_ring','r0')]
    for wi,(workload,label) in enumerate([('uniform','Uniform'),('hot90','Hot-90')]):
        shift=(-.18,.18)[wi]
        for i,kind in enumerate(protocols):
            ids=[f'B1_{kind}_{workload}_N16384_B4096_seed{seed}' for seed in range(101,106)]
            values=[rows[k]['phases']['measurement']['total_bytes']/rows[k]['spec']['requests'] for k in ids]
            s=draw(axes[0],i+shift,values,label if i==0 else None,colors[wi],scale=1024,offset=(7,35)[wi])
            series.append(dict(figure='core',panel='absolute',metric='bytes_per_request',kind=kind,workload=workload,ids=ids,**s))
        for i,(base,var) in enumerate(pairs):
            ids=[[f'B1_{kind}_{workload}_N16384_B4096_seed{seed}' for kind in (base,var)] for seed in range(101,106)]
            values=[100*(1-rows[y]['bytes_per_request']/rows[x]['bytes_per_request']) for x,y in ids]
            s=draw(axes[1],i+shift,values,label if i==0 else None,colors[wi],offset=(.55,2.2)[wi])
            series.append(dict(figure='core',panel='paired',metric='bytes_saving_pct',baseline=base,variant=var,workload=workload,ids=ids,**s))
    axes[0].set(xticks=range(6),xticklabels=[names[k] for k in protocols],ylabel='Total communication (KiB / request)',ylim=(0,620),title='(a) Absolute bandwidth cost')
    axes[1].set(xticks=range(5),xticklabels=[f'{names[x]}\nto {names[y]}' for x,y in pairs],ylabel='Paired communication reduction (%)',ylim=(0,42),title='(b) Explicit baseline comparisons')
    for ax in axes:decorate(ax);ax.legend(frameon=False,ncol=2,loc='upper right')
    fig.subplots_adjust(left=.075,right=.99,top=.86,bottom=.26,wspace=.28)
    fig.text(.075,.065,'N = 16,384; B = 4,096 bytes; fixed Z4/A3/S3; five paired runs, mean and 95% t intervals.\n'
        '2,048 warmup + 4,096 measured requests. Includes headers, nonces, authentication and recursive maps.\n'
        'Finite measurement window; same-profile comparison, not the separately tuned result. No latency claim.',fontsize=8,color='#494949')
    export(fig,'completed_core_bandwidth')

    fig,axes=plt.subplots(1,2,figsize=(10.5,4.8))
    for fi,(family,base,var,title) in enumerate([('IR','deferred','sde','(a) Static IR allocation + prefix cache'),('AB','ring','r0','(b) Static AB dummy layout + prefix cache')]):
        ax=axes[fi]
        for li,(layout,label) in enumerate([('uniform','Uniform buckets'),('depth','Depth-dependent buckets')]):
            for bi,B in enumerate([64,4096]):
                e=next(x for x in a['effects'] if (x['family'],x['layout'],x['B'],x['baseline'],x['variant'])==(family,layout,B,base,var))
                ids=[[x['baseline'],x['variant']] for x in e['per_seed']]
                values=[100*(1-rows[y]['bytes_per_request']/rows[x]['bytes_per_request']) for x,y in ids]
                s=draw(ax,bi+(-.18,.18)[li],values,label if bi==0 else None,colors[li],offset=.35)
                series.append(dict(figure='static_components',panel=family,metric='bytes_saving_pct',layout=layout,B=B,baseline=base,variant=var,ids=ids,**s))
        ax.set(xticks=[0,1],xticklabels=['64 B blocks','4 KiB blocks'],ylabel=f'Reduction vs {names[base]} (%)',ylim=(0,34),title=title)
        decorate(ax);ax.legend(frameon=False,fontsize=8,loc='upper left')
    fig.subplots_adjust(left=.075,right=.99,top=.86,bottom=.26,wspace=.28)
    fig.text(.075,.065,'N = 4,096; uniform requests; five paired runs, mean and 95% t intervals.\n'
        '2,048 warmup + 4,096 measured requests. IR: R480, six cached levels; AB: R256, five cached levels.\n'
        'Static components only: no native IR-Stash/DWB or AB CB/DeadQ. All serialized protocol bytes included.',fontsize=8,color='#494949')
    export(fig,'completed_static_components')
    data=out/'completed_core_components_data.json'
    save(data,dict(source_sha256=sha(source),series=series,unit_for_absolute_plot='KiB = 1024 bytes',raw_units='bytes/request or percent',performance_scope='fixed profiles and static components'))
    report=PACKAGE/'37_核心及静态组件图表核验.md'
    report.write_text('\n'.join(['# 核心与静态组件图表','',
        '两张图来自已完成并独立审计的140次运行。每个柱及其95%区间都绑定五个原始run；减少率先按种子配对，再求均值。','',
        '- 核心图：`output/pdf/completed_core_bandwidth.pdf`。左侧为6后端、两种负载的绝对总通信，右侧区分Path→SDE、Deferred→SDE、Ring→GC-Ring、Ring→R0、GC-Ring→R0。固定Z4/A3/S3，不用作分别调优主结果。',
        '- 静态组件图：`output/pdf/completed_static_components.pdf`。IR/AB分面，64B与4KiB分组，均匀与逐层桶分开。IR按Deferred分母，AB按Ring分母；未纳入完整原生机制。','',
        '各图另有SVG和PNG；`figures/completed_core_components_data.json` 保存30组逐柱数值、原始ID、单位和置信区间。原始140行与28格绝对开销见36号文档对应审计收据。','',
        '核心图说明：同固定参数下，SDE对Path的改善包含维护策略改变；以Deferred为分母可更直接观察selective的增量。Ring→GC-Ring与GC-Ring→R0分开显示，避免将省根全部称为少读收益。','',
        '静态图说明：4KiB时数据流量占比上升，IR异质配置相对Deferred超过20%；64B同配置约19%。两种块长不能合并成“IR均超过20%”。AB图只说明静态dummy布局组合，不替代带CB与DeadQ的条件实验。','',
        '生成、数值审计、PDF嵌入字体与版面审阅分别记录。实际审阅状态以results中的core_components_exports_audit.json和core_components_visual_review.json为准。'])+'\n',encoding='utf-8')
    outputs.append(dict(path=str(report.relative_to(PACKAGE)),sha256=sha(report)))
    save(PACKAGE/'results/core_components_exports.json',dict(status='generated',source_sha256=sha(source),generator_sha256=sha(__file__),
        data_sha256=sha(data),outputs=outputs,visual_review_pending=True))
    print(json.dumps(dict(status='generated',pdfs=2,series=len(series),raw_records=len(rows))))


if __name__=='__main__':main()
