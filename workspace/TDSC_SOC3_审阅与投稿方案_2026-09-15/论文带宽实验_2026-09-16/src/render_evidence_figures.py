"""Vector figures from explicit model/measurement evidence; never join the two."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import math


def main():
    out=PACKAGE/'figures';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'svg.fonttype':'none','figure.dpi':160,'savefig.dpi':180})
    inputs={};outputs=[]
    def finish(fig,name):
        for ext in ('pdf','svg','png'):
            p=out/f'{name}.{ext}';fig.savefig(p,bbox_inches='tight');outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
        plt.close(fig)
    path=PACKAGE/'results/fair_tuning_candidates.json';tuning=json.loads(path.read_text());inputs[str(path.relative_to(PACKAGE))]=sha(path)
    colors={'path':'#868e96','deferred':'#bb8a32','sde':'#188977','ring':'#326ab3','r0':'#b43d59'}
    labels={'path':'Path','deferred':'Deferred','sde':'SDE','ring':'Ring','r0':'R0'}
    fig,ax=plt.subplots(figsize=(7.2,4.8));table=[]
    for kind in colors:
        rows=[c for c in tuning['candidates'] if c['spec']['kind']==kind and c['eligible']]
        points=sorted({(c['server_object_bytes']/(1<<20),float(c['periodic_model']['total']['upper'])/1024) for c in rows})
        ax.scatter([p[0] for p in points],[p[1] for p in points],s=28,c=colors[kind],label=labels[kind],alpha=.7)
        best=next(c for c in rows if c['candidate_id'] in tuning['selected'])
        x=best['server_object_bytes']/(1<<20);y=float(best['periodic_model']['total']['upper'])/1024
        ax.scatter([x],[y],marker='*',s=160,c=colors[kind],edgecolors='white',linewidths=.7,zorder=5)
        ax.annotate(labels[kind],(x,y),xytext=(7,6),textcoords='offset points',color=colors[kind],fontsize=9)
        table.append(dict(kind=kind,candidate_id=best['candidate_id'],server_MiB=x,periodic_KiB_per_request=y))
    ax.set(xlabel='Serialized server objects (MiB)',ylabel='Periodic model (KiB / application request)',
           title='Finite candidate tuning: bandwidth and storage')
    ax.grid(alpha=.18);ax.legend(ncol=3,loc='upper right',frameon=False)
    fig.subplots_adjust(bottom=.22)
    fig.text(.08,.02,'MODEL ONLY  |  N = 16,384; B = 4,096 B; 72 candidates. Stars mark selected minima.\nBaseline lifetime proofs and true peak client memory remain separate obligations.',fontsize=8,color='#555555')
    finish(fig,'finite_tuning_model')
    save(out/'finite_tuning_model_data.json',dict(source_sha256=sha(path),selected=table,evidence='periodic model, not measurement'))
    path=PACKAGE/'results/paired_statistics.json';statistics_=json.loads(path.read_text());inputs[str(path.relative_to(PACKAGE))]=sha(path)
    fig,axes=plt.subplots(1,2,figsize=(9.0,4.0),sharey=True);selected=[]
    workloads=['uniform','hot90','zipf09','scan'];names=['Uniform','Hot 90%','Zipf 0.9','Scan']
    for ax,family,title in zip(axes,['free_compressed','rho'],['Freecursive components','Restricted rho components']):
        for base,new,color,offset,label in [('deferred','sde','#188977',-.18,'SDE vs Deferred'),('ring','r0','#b43d59',.18,'R0 vs Ring')]:
            for i,w in enumerate(workloads):
                candidates=[r for r in statistics_['rows'] if r['family']==family and r['workload']==w and r['baseline']==base and r['selective']==new and r['N']==4096 and r['B']==64]
                if not candidates:continue
                assert len(candidates)==1
                r=candidates[0];selected.append(r);y=r['paired_mean_saving_pct']
                ax.bar(i+offset,y,.32,color=color,alpha=.82,label=label if i==0 else None)
                if r['ci95']:
                    lo,hi=r['ci95'];ax.errorbar(i+offset,y,yerr=[[y-lo],[hi-y]],color='#333333',capsize=3,fmt='none')
                ax.text(i+offset,y+.4,f'{y:.1f}%\nn={r["n"]}',ha='center',va='bottom',fontsize=7.5)
        ax.set(title=title,xticks=range(4),xticklabels=names,ylim=(0,32));ax.grid(axis='y',alpha=.18)
        ax.set_axisbelow(True)
    axes[0].set_ylabel('Paired reduction in total serialized bytes (%)')
    axes[0].legend(loc='upper left',ncol=2,frameon=False,fontsize=8)
    partial=any(r['n']<5 for r in selected)
    fig.suptitle(('PRELIMINARY — incomplete repeats' if partial else 'Paired communication results'),fontsize=12,y=1.04)
    fig.text(.08,-.04,'N = 4,096; B = 64 B; ciphertext, headers, authentication and framing included.\nNo CI is drawn for n < 5. These are implemented components, not full native systems or latency measurements.',fontsize=8,color='#555555')
    fig.tight_layout();finish(fig,'composition_paired_progress')
    save(out/'composition_paired_progress_data.json',dict(source_sha256=sha(path),rows=selected,partial=partial))
    save(out/'figure_receipt.json',dict(inputs=inputs,outputs=outputs,matplotlib_version=matplotlib.__version__,
                                      generator_sha256=sha(__file__),final_chapter_complete=False))
    print(json.dumps(dict(figures=2,formats=['pdf','svg','png'],composition_partial=partial)))

if __name__=='__main__':main()
