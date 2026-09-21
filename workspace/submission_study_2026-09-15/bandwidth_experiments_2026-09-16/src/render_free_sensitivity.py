"""One completed Freecursive sensitivity figure, bound to raw run identities."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=PACKAGE/'results/free_sensitivity_completed_audit.json';a=json.loads(p.read_text(encoding='utf-8'))
    q=PACKAGE/'results/free_sensitivity_tables_audit.json';v=json.loads(q.read_text(encoding='utf-8'))
    assert a['status']==v['status']=='passed' and v['source_sha256']==sha(p)
    assert a['runs']==160 and not a['additional_repeat_groups']
    for r in a['receipts']:assert sha(PACKAGE/r['path'])==r['sha256']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,'svg.fonttype':'none',
        'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    configs=[('free_raw/uniform/B64_base','64B raw / Uniform'),
        ('free_compressed/uniform/B64_base','64B compressed / Uniform'),
        ('free_raw/uniform/B4096','4KiB raw / Uniform'),
        ('free_compressed/uniform/B4096','4KiB compressed / Uniform'),
        ('free_compressed/hot90/B64_base','64B / Hot-90 / PLB8'),
        ('free_compressed/hot90/plb4','64B / Hot-90 / PLB4'),
        ('free_compressed/hot90/plb32','64B / Hot-90 / PLB32'),
        ('free_compressed/hot90/beta4','64B / Hot-90 / beta4')]
    fig,axes=plt.subplots(1,2,figsize=(12.9,7.2),gridspec_kw={'width_ratios':[1.12,1]})
    colors={'deferred':'#8BA4B6','sde':'#237AA5','ring':'#D5AC75','r0':'#A45B27'}
    series=[]
    for j,(key,label) in enumerate(configs):
        for index,(base,new,short) in enumerate((('deferred','sde','SDE vs Deferred'),('ring','r0','R0 vs Ring'))):
            e=next(x for x in a['selective_effects'] if x['name']==f'{key}: {base} -> {new}')
            x=e['bytes_saving_pct'];m=x['mean'];lo,hi=x['ci95'];y=j+(-.19,.19)[index]
            axes[0].barh(y,m,height=.32,color=colors[new],label=short if j==0 else None)
            axes[0].errorbar(m,y,xerr=[[m-lo],[hi-m]],fmt='none',color='#333333',capsize=2,lw=.8)
            axes[0].text(hi+.25,y,f'{m:.2f}',ha='left',va='center',fontsize=8)
            series.append(dict(panel='selective',configuration=key,baseline=base,variant=new,
                ids=[[t['baseline_id'],t['variant_id']] for t in e['pairs']],**x))
    axes[0].set(yticks=range(8),yticklabels=[x[1] for x in configs],xlim=(0,28),
        xlabel='Paired total communication reduction (%)',title='(a) Selective benefit within each configuration')
    axes[0].invert_yaxis();axes[0].grid(axis='x',alpha=.18);axes[0].set_axisbelow(True)
    axes[0].axhline(3.5,color='#bbbbbb',lw=.7,ls=':')
    axes[0].legend(frameon=False,ncol=2,loc='lower left',bbox_to_anchor=(0,1.04),fontsize=8)
    order=['B64_base','plb4','plb32','beta4'];names={'deferred':'Deferred','sde':'SDE','ring':'Ring','r0':'R0'}
    for ki,(kind,name) in enumerate(names.items()):
        for j,condition in enumerate(order):
            key='free_compressed/hot90/'+condition
            c=next(x for x in a['cells'] if x['configuration']==key and x['kind']==kind)
            x=c['bytes'];m=x['mean']/1024;lo,hi=[z/1024 for z in x['ci95']];pos=j+(ki-1.5)*.19
            axes[1].bar(pos,m,width=.175,color=colors[kind],label=name if j==0 else None)
            axes[1].errorbar(pos,m,yerr=[[m-lo],[hi-m]],fmt='none',color='#333333',capsize=2,lw=.8)
            series.append(dict(panel='absolute',configuration=key,kind=kind,ids=c['ids'],**x))
    axes[1].set(xticks=range(4),xticklabels=['PLB8\nbeta14','PLB4\nbeta14','PLB32\nbeta14','PLB8\nbeta4'],
        ylabel='Total communication (KiB / request)',ylim=(0,120),title='(b) Frontend settings change absolute cost')
    axes[1].grid(axis='y',alpha=.18);axes[1].set_axisbelow(True)
    axes[1].legend(frameon=False,ncol=4,loc='lower left',bbox_to_anchor=(-.05,1.04),fontsize=8)
    fig.subplots_adjust(left=.20,right=.985,top=.80,bottom=.27,wspace=.37)
    fig.text(.025,.95,'Freecursive-style composition: selective gains and frontend costs',fontsize=13,weight='bold')
    fig.text(.025,.17,'N = 4,096; Z4/A3/S4; R = 256; 2,048 warmup + 4,096 measured requests; five paired seeds, mean and 95% t intervals.\n'
        'All serialized protocol bytes, including authentication and maintenance. Panel (b): 64B compressed map, Hot-90, X = 32.',fontsize=9,color='#444444')
    fig.text(.025,.09,'At 4KiB, X = 1,024 (raw) or 2,048 (compressed); at 64B, X = 16 or 32. Block-size slices also change packing and PLB bytes.\n'
        'PLB changes use different client resources. Finite windows; no native PMMAC/hardware controller, peak-memory or latency claim.',fontsize=9,color='#444444')
    stem='completed_free_sensitivity';outputs=[]
    for suffix,folder in (('pdf','output/pdf'),('svg','figures'),('png','figures')):
        path=PACKAGE/folder/f'{stem}.{suffix}';path.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(path,bbox_inches='tight');outputs.append(dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path)))
    plt.close(fig)
    data=PACKAGE/'figures/completed_free_sensitivity_data.json'
    save(data,dict(source_sha256=sha(p),series=series,absolute_scale=1024,
        total_audited_runs=160,new_sensitivity_runs=100,reused_controls=60))
    save(PACKAGE/'results/free_sensitivity_exports.json',dict(status='generated',source_sha256=sha(p),
        tables_audit_sha256=sha(q),data_sha256=sha(data),outputs=outputs,generator_sha256=sha(__file__),visual_review_pending=True))
    print(json.dumps(dict(status='generated',pdfs=1,series=len(series),runs=160)))


if __name__=='__main__':main()
