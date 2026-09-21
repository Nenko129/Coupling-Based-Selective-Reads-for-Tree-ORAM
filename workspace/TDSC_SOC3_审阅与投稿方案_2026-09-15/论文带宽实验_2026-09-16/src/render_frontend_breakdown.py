"""Publication vector breakdown, keeping fixed authentication costs visible."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p=PACKAGE/'results/frontend_effects.json';data=json.loads(p.read_text())
    rows=[r for r in data['cost_breakdown'] if r['family'] in ('free_compressed','rho') and r['workload']=='uniform']
    assert len(rows)==8 and all(r['n']==5 for r in rows)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(8.8,4.5),sharey=True)
    parts=[('data_slots_excluding_nonce','Data slots','#3b6fb6'),('data_nonce','Data nonces','#83b3da'),
           ('headers','Headers','#bca785'),('authentication','Authentication','#d47866'),('framing','Framing/control','#666c75')]
    kinds=['deferred','sde','ring','r0'];labels=['Deferred','SDE','Ring','R0'];used=[]
    for ax,family,title in zip(axes,['free_compressed','rho'],['Freecursive components','Restricted rho components']):
        costs=[next(r for r in rows if r['family']==family and r['kind']==k) for k in kinds];used+=costs
        bottom=[0.0]*4
        for key,label,color in parts:
            heights=[r['components_bytes_per_request'][key]/1024 for r in costs]
            ax.bar(range(4),heights,bottom=bottom,color=color,label=label,width=.66,edgecolor='white',linewidth=.3)
            bottom=[a+b for a,b in zip(bottom,heights)]
        for i,total in enumerate(bottom):ax.text(i,total+.8,f'{total:.1f}',ha='center',fontsize=9)
        ax.set(xticks=range(4),xticklabels=labels,title=title,ylim=(0,66));ax.set_axisbelow(True);ax.grid(axis='y',alpha=.16)
    axes[0].set_ylabel('Total serialized KiB / application request')
    fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,.99),ncol=3,frameon=False,fontsize=9)
    fig.subplots_adjust(top=.77,bottom=.21,wspace=.14)
    fig.text(.08,.04,'Uniform workload; N = 4,096; B = 64 B; means of five runs.\nData slots include real and dummy contents. Headers retain their own nonces.',fontsize=8,color='#555555')
    out=PACKAGE/'figures';files=[]
    for ext in ('pdf','svg','png'):
        dst=out/f'frontend_bandwidth_breakdown.{ext}';fig.savefig(dst,dpi=180,bbox_inches='tight');files.append(dict(path=str(dst.relative_to(PACKAGE)),sha256=sha(dst)))
    plt.close(fig)
    save(out/'frontend_bandwidth_breakdown_data.json',dict(rows=used,source_sha256=sha(p),generator_sha256=sha(__file__),outputs=files))
    print(json.dumps(dict(figures=1,means=8,n=5)))

if __name__=='__main__':main()
