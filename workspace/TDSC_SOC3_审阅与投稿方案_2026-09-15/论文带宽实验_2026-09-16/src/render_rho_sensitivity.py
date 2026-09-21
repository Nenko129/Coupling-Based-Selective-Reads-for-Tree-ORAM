"""Completed rho sensitivity: vector SVG plus review PNG, no new PDF."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import math


def main():
    source=PACKAGE/'results/rho_sensitivity_completed_snapshot.json';a=json.loads(source.read_text(encoding='utf-8'))
    check=PACKAGE/'results/rho_sensitivity_checks.json';v=json.loads(check.read_text(encoding='utf-8'))
    assert a['status']=='complete_receipts_audited' and a['completed']==180
    assert v['status']=='passed' and v['source_sha256']==sha(source) and v['all_planned_runs_complete']
    assert len(a['cells'])==36 and len(a['effects'])==18 and not a['additional_repeat_groups']
    for r in a['receipts']:assert sha(PACKAGE/r['path'])==r['sha256']
    order=[('uniform/ratio1','Uniform / n = 1'),('uniform/base','Uniform / n = 3'),('uniform/ratio5','Uniform / n = 5'),
        ('hot90/llc8','Hot-90 / LLC = 8'),('hot90/base','Hot-90 / LLC = 32'),('hot90/llc128','Hot-90 / LLC = 128'),
        ('zipf09/rho32','Zipf(0.9) / rho = 32'),('zipf09/base','Zipf(0.9) / rho = 128'),('zipf09/rho512','Zipf(0.9) / rho = 512')]
    colors={'deferred':'#8BA4B6','sde':'#237AA5','ring':'#D5AC75','r0':'#A45B27'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'svg.fonttype':'path',
        'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    fig,axes=plt.subplots(1,2,figsize=(14.4,8.1),gridspec_kw={'width_ratios':[1.0,1.1]})
    series=[];absolute_max=math.ceil(max(c['bytes']['ci95'][1] for c in a['cells'])/1024/10)*10
    for j,(key,label) in enumerate(order):
        for k,(base,new,short) in enumerate((('deferred','sde','SDE vs Deferred'),('ring','r0','R0 vs Ring'))):
            e=next(x for x in a['effects'] if x['name']==f'{key}: {base} -> {new}')
            x=e['bytes_saving_pct'];m=x['mean'];lo,hi=x['ci95'];y=j+(-.18,.18)[k];gid=f'selective_{j}_{k}'
            bars=axes[0].barh(y,m,height=.31,color=colors[new],label=short if j==0 else None);bars[0].set_gid(gid)
            axes[0].errorbar(m,y,xerr=[[m-lo],[hi-m]],fmt='none',color='#333333',capsize=2,lw=.8)
            axes[0].text(hi+.25,y,f'{m:.2f}',ha='left',va='center',fontsize=8)
            series.append(dict(panel='selective',configuration=key,baseline=base,variant=new,gid=gid,
                ids=[[p['baseline_id'],p['variant_id']] for p in e['pairs']],**x))
        for k,(kind,name) in enumerate((('deferred','Deferred'),('sde','SDE'),('ring','Ring'),('r0','R0'))):
            c=next(x for x in a['cells'] if x['configuration']==key and x['kind']==kind)
            x=c['bytes'];m=x['mean']/1024;lo,hi=[z/1024 for z in x['ci95']];y=j+(k-1.5)*.18;gid=f'absolute_{j}_{k}'
            bars=axes[1].barh(y,m,height=.165,color=colors[kind],label=name if j==0 else None);bars[0].set_gid(gid)
            axes[1].errorbar(m,y,xerr=[[m-lo],[hi-m]],fmt='none',color='#333333',capsize=1.6,lw=.65)
            series.append(dict(panel='absolute',configuration=key,kind=kind,gid=gid,ids=c['ids'],**x))
    for ax,limit,prefix in zip(axes,(20,absolute_max),('selective','absolute')):
        ax.set(yticks=range(9),ylim=(-.6,8.6),xlim=(0,limit));ax.invert_yaxis();ax.grid(axis='x',alpha=.17);ax.set_axisbelow(True)
        for y in (2.5,5.5):ax.axhline(y,color='#bbbbbb',ls=':',lw=.8)
        # Invisible reference paths let the independent SVG checker recover
        # actual plotted widths in data units, not merely trust the data JSON.
        ax.axvline(0,alpha=0,gid=prefix+'_reference_zero')
        ax.axvline(limit,alpha=0,gid=prefix+'_reference_max')
    axes[0].set(yticklabels=[label for key,label in order],xlabel='Paired total communication reduction (%)',title='(a) Benefit changes with frontend traffic share')
    axes[1].set(yticklabels=[],xlabel='Total communication (KiB / request)',title='(b) Absolute cost under the same settings')
    axes[0].legend(frameon=False,ncol=2,loc='lower left',bbox_to_anchor=(0,1.04),fontsize=8)
    axes[1].legend(frameon=False,ncol=4,loc='lower left',bbox_to_anchor=(0,1.04),fontsize=8)
    fig.subplots_adjust(left=.19,right=.98,top=.81,bottom=.30,wspace=.25)
    fig.text(.025,.955,'Rho-inspired composition: completed frontend sensitivity',fontsize=14,weight='bold')
    fig.text(.025,.17,'N = 4,096; B = 64B; backend Z4/A3/S4, R = 256; 2,048 warmup + 4,096 measured requests; five paired seeds.\n'
        'Bars show means and 95% t intervals. n denotes front-tree Transfers per backend Transfer; defaults: n = 3, LLC = 32, rho = 128.',fontsize=9,color='#444444')
    fig.text(.025,.09,'All serialized protocol bytes include authentication and maintenance; frontend and backend are both counted.\n'
        'Cache changes use different resources. Finite windows; address-LRU, public frame counts and full trusted backend PosMap; no native ECC or latency claim.',fontsize=9,color='#444444')
    outputs=[]
    for suffix in ('svg','png'):
        path=PACKAGE/f'figures/completed_rho_sensitivity.{suffix}';fig.savefig(path,bbox_inches='tight')
        outputs.append(dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path)))
    plt.close(fig)
    dp=PACKAGE/'figures/completed_rho_sensitivity_data.json'
    save(dp,dict(source_sha256=sha(source),runs=180,new_runs=120,reused=60,series=series,
        axes_max=dict(selective=20,absolute=absolute_max),absolute_scale=1024,configurations=order))
    save(PACKAGE/'results/rho_sensitivity_exports.json',dict(status='generated',source_sha256=sha(source),
        checks_sha256=sha(check),data_sha256=sha(dp),generator_sha256=sha(__file__),outputs=outputs,visual_review_pending=True))
    print(json.dumps(dict(status='generated',runs=180,series=len(series),formats=['svg','png'])))


if __name__=='__main__':main()
