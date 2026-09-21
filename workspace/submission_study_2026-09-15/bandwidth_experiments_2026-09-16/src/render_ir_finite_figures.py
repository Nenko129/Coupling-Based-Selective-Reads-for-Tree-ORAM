"""Export only the completed IR finite-prefix batch, with all cells and CIs."""
from common import *
import csv,statistics
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    source=PACKAGE/'results/ir_dwb_statistics.json';stats=json.loads(source.read_text())
    assert stats['completed']==stats['expected']==120 and stats['status']=='complete_receipts_audited'
    assert all(e['effect']['n']==5 and e['needs_more_repeats'] is False for e in stats['effects'])
    out=PACKAGE/'figures';tables=PACKAGE/'tables';out.mkdir(exist_ok=True);tables.mkdir(exist_ok=True)
    raw=[];by_id={}
    for receipt in stats['receipts']:
        p=PACKAGE/receipt['path'];assert sha(p)==receipt['sha256'];r=json.loads(p.read_text());by_id[r['spec']['id']]=r
        s=r['spec'];m=r['phases']['measurement'];components=m['bills'][0]['components'];metrics=m['frontend_metrics']
        row={k:s[k] for k in ('id','kind','layout','dwb','workload','trace_seed','N','B','warmup','requests','cached_levels','plb','llc_sets','llc_ways')}
        row.update(total_bytes=m['total_bytes'],bytes_per_request=r['bytes_per_request'],public_slots=m['public_slots'],rpc=m['rpc'])
        row.update({'bytes_'+k:v for k,v in components.items()})
        row.update({k:metrics.get(k,0) for k in ('foreground_slots','foreground_writebacks','foreground_posmap_slots','dwb_completed','dwb_posmap_slots','dummy_slots','dirty_resident')})
        row.update(source_path=receipt['path'],source_sha256=receipt['sha256']);raw.append(row)
    def write_csv(name,rows):
        with (tables/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write_csv('IR_DWB_120_runs.csv',raw)
    pairs=[]
    for e in stats['effects']:
        pairs.append(dict(axis=e['axis'],condition_1=e['condition'][0],condition_2=e['condition'][1],workload=e['condition'][2],
            baseline=e['before'],variant=e['after'],n=5,baseline_bytes_per_request=e['baseline_mean_bytes'],variant_bytes_per_request=e['variant_mean_bytes'],
            saving_pct=e['effect']['mean'],ci95_lower=e['effect']['ci95'][0],ci95_upper=e['effect']['ci95'][1],
            source_sha256=sha(source)))
    write_csv('IR_DWB_40_comparisons.csv',pairs)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'svg.fonttype':'none','figure.dpi':150,'savefig.dpi':180})
    outputs=[]
    def finish(fig,name):
        for ext in ('pdf','svg','png'):
            p=out/f'{name}.{ext}';fig.savefig(p,bbox_inches='tight');outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
        plt.close(fig)
    configs=[('uniform',False),('depth',False),('uniform',True),('depth',True)]
    labels=['Uniform\nDWB off','Depth\nDWB off','Uniform\nDWB on','Depth\nDWB on']
    fig,axes=plt.subplots(1,2,figsize=(10.0,4.0),sharey=True)
    for ax,workload,title in zip(axes,('uniform','hot90'),('Uniform workload','Hot 90% workload')):
        for base,color,offset,label in [('path','#486da6',-.18,'SDE vs Path'),('deferred','#188977',.18,'SDE vs Deferred')]:
            for i,(layout,dwb) in enumerate(configs):
                e=next(e for e in stats['effects'] if e['axis']=='backend' and e['before']==base and e['condition']==[layout,dwb,workload])
                mean=e['effect']['mean'];lo,hi=e['effect']['ci95']
                ax.bar(i+offset,mean,.32,color=color,label=label if i==0 else None)
                ax.errorbar(i+offset,mean,yerr=[[mean-lo],[hi-mean]],fmt='none',color='#303030',capsize=3,linewidth=1)
                ax.text(i+offset,hi+.35,f'{mean:.1f}',ha='center',va='bottom',fontsize=8)
        ax.set(title=title,xticks=range(4),xticklabels=labels,ylim=(0,25));ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    axes[0].set_ylabel('Reduction in total serialized bytes (%)')
    handles,legend=axes[0].get_legend_handles_labels();fig.legend(handles,legend,loc='upper center',bbox_to_anchor=(.5,1.03),ncol=2,frameon=False)
    fig.subplots_adjust(top=.81,bottom=.23,wspace=.12)
    fig.text(.085,.02,'FINITE PREFIX  |  N = 4,096; B = 64 B; 128 warmup + 256 measured application requests.\nFive paired runs per cell; 95% t intervals. Same 2,048 measured public slots. IR-Stash is not included.',fontsize=8,color='#555555')
    finish(fig,'ir_integrated_finite_gain')
    fig,axes=plt.subplots(1,2,figsize=(9.3,4.3),sharey=True)
    segments=[('Data slots','#5979a6'),('Data nonces','#aac0d7'),('Headers','#dfac57'),('Authentication','#936c9b'),('Framing','#949da6')]
    breakdown=[]
    for ax,workload,title in zip(axes,('uniform','hot90'),('Uniform workload','Hot 90% workload')):
        for i,kind in enumerate(('path','deferred','sde')):
            runs=[r for r in by_id.values() if r['spec']['layout']=='depth' and r['spec']['dwb'] and r['spec']['workload']==workload and r['spec']['kind']==kind]
            assert len(runs)==5
            values=[]
            for r in runs:
                s=r['spec'];c=r['phases']['measurement']['bills'][0]['components'];data=c['data_download']+c['data_upload']
                assert data%(s['B']+16)==0;nonces=data//(s['B']+16)*16
                parts=[data-nonces,nonces,c['headers_download']+c['headers_upload'],c['authentication_download']+c['authentication_upload'],c['framing_and_control']]
                assert sum(parts)==r['phases']['measurement']['total_bytes'];values.append([v/s['requests']/1024 for v in parts])
            means=[statistics.mean(v[j] for v in values) for j in range(5)];bottom=0
            for j,(name,color) in enumerate(segments):
                ax.bar(i,means[j],.6,bottom=bottom,label=name if i==0 else None,color=color);bottom+=means[j]
            ax.text(i,bottom+.8,f'{bottom:.1f}',ha='center',va='bottom',fontsize=9)
            breakdown.append(dict(workload=workload,kind=kind,n=5,mean_KiB_per_request=bottom,segments=dict(zip([x[0] for x in segments],means))))
        ax.set(title=title,xticks=range(3),xticklabels=['Path','Deferred','SDE'],ylim=(0,76));ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    axes[0].set_ylabel('Total communication (KiB / application request)')
    handles,legend=axes[0].get_legend_handles_labels();fig.legend(handles,legend,loc='upper center',bbox_to_anchor=(.5,1.025),ncol=5,frameon=False,fontsize=8)
    fig.subplots_adjust(top=.80,bottom=.22,wspace=.12)
    fig.text(.08,.015,'FINITE PREFIX  |  Depth profile + DWB on; N = 4,096; B = 64 B; 5 runs per bar.\nData includes real and dummy slots. Metadata/authentication explain the baseline ordering.\nPublic-slot padding and all maintenance are included; no latency or full-native-system claim.',fontsize=8,color='#555555')
    finish(fig,'ir_integrated_finite_breakdown')
    save(out/'ir_integrated_finite_data.json',dict(source_sha256=sha(source),paired_effects=stats['effects'],breakdown=breakdown,
        finite_prefix=True,full_native_IR=False,latency_claim=False))
    for name in ('IR_DWB_120_runs.csv','IR_DWB_40_comparisons.csv'):
        p=tables/name;outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    save(out/'ir_integrated_finite_receipt.json',dict(status='generated',source_sha256=sha(source),generator_sha256=sha(__file__),outputs=outputs,
        completed_runs=120,comparisons=40,repeat_gate_triggered=False,visual_review_pending=True))
    print(json.dumps(dict(runs=120,comparisons=40,figures=2,formats=['pdf','svg','png'],csv_tables=2)))


if __name__=='__main__':main()
