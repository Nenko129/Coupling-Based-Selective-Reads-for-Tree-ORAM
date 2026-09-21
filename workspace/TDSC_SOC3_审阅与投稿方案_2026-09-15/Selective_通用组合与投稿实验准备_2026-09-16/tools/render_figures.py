from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minimal_runtime import *
sys.path.insert(0,str(EVAL/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    pilot='--pilot' in sys.argv;suite='pilot' if pilot else 'formal'
    data=json.loads((HOME/'results/analysis.json').read_text(encoding='utf-8'))
    names={'free_compressed':'Freecursive-style','rho':'rho-style','IR':'IR-Alloc profile','AB':'AB static profile'}
    rows={(r['family'],r['B']):r for r in data['comparisons'] if r['suite']==suite and r['baseline']=='base' and r['layout']!='uniform'}
    sizes=(64,) if pilot else (64,4096)
    keys=[(f,b) for b in sizes for f in names]
    ready=all(k in rows and (pilot or rows[k]['headline_eligible']) for k in keys)
    if not ready:
        save(HOME/'results/figure_status.json',dict(status='waiting_for_complete_formal_pairs',needed=keys,available=[list(k) for k in rows]));return
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,len(sizes),figsize=(9.4 if pilot else 12.4,4.8),squeeze=False)
    for ax,B in zip(axes[0],sizes):
        for i,f in enumerate(names):
            r=rows[f,B];ax.bar(i-.18,r['baseline_bytes']/1024,.36,color='#718096',label='Host + full read' if i==0 else None)
            ax.bar(i+.18,r['selective_bytes']/1024,.36,color='#177c80',label='Host + selective read' if i==0 else None)
            ax.text(i,max(r['baseline_bytes'],r['selective_bytes'])/1024*1.025,f"{r['mean_saving_pct']:.1f}%",ha='center',fontsize=9)
        ax.set_xticks(range(4),list(names.values()),rotation=14,ha='right');ax.set_ylabel('Serialized bidirectional KiB / application request')
        ax.set_title(f'Block size: {B} bytes');ax.set_ylim(0,ax.get_ylim()[1]*1.14);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    title='PILOT: N=128, one seed; not final paper results' if pilot else 'Minimal composition: N=4096, five paired seeds'
    fig.suptitle(title,fontsize=13,fontweight='bold');handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False);fig.tight_layout(rect=(0,.09,1,.91))
    out=HOME/'figures';out.mkdir(exist_ok=True);stem='pilot_minimal_composition' if pilot else 'formal_minimal_composition'
    for ext in ('png','svg'):fig.savefig(out/f'{stem}.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    save(out/f'{stem}_data.json',dict(suite=suite,rows=[rows[k] for k in keys],source_analysis_sha256=sha(HOME/'results/analysis.json'),
        uncertainty='n1 pilot has no CI' if pilot else 'paired savings CI retained in data/table; bars show absolute means'))
    print(json.dumps(dict(status='rendered',figure=stem)))
if __name__=='__main__':main()
