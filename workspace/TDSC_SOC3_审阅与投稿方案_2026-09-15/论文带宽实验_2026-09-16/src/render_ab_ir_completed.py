"""Two publication vector figures; explicitly show strong controls/failures."""
from common import *
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Patch


COLORS={'gc_ring':'#237AA5','r0':'#A45B27','path':'#648DA3','deferred':'#B4783C'}


def plot_effect(ax,e,y,color,label,gid,height=.32):
    x=e['paired_saving_pct'];m=x['mean'];lo,hi=x['ci95']
    bars=ax.barh(y,m,height=height,color=color,label=label);bars[0].set_gid(gid)
    ax.errorbar(m,y,xerr=[[m-lo],[hi-m]],fmt='none',color='#333333',capsize=3,lw=.9)
    return dict(gid=gid,axis=e['axis'],condition=e.get('condition'),cohort=e.get('cohort'),workload=e['workload'],
        dwb=e.get('dwb'),baseline=e['baseline'],variant=e['variant'],**x,
        ids=[[p.get('baseline_id',p.get('before')),p.get('variant_id',p.get('after'))] for p in e['pairs']])


def references(ax,prefix,maximum):
    ax.axvline(0,alpha=0,gid=prefix+'_reference_zero')
    ax.axvline(maximum,alpha=0,gid=prefix+'_reference_max')


def export(fig,stem,source,series,axes_max,table_audit,extra=None):
    outputs=[]
    for suffix in ('svg','png'):
        p=PACKAGE/f'figures/{stem}.{suffix}';fig.savefig(p,bbox_inches='tight');outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    plt.close(fig);dp=PACKAGE/f'figures/{stem}_data.json'
    save(dp,dict(source_sha256=sha(source),series=series,axes_max=axes_max,extra=extra or {}))
    return dict(stem=stem,source_path=str(source.relative_to(PACKAGE)),source_sha256=sha(source),data_sha256=sha(dp),
        table_audit_sha256=sha(table_audit),outputs=outputs,visual_review_pending=True)


def main():
    table=PACKAGE/'results/ab_ir_completed_tables_audit.json';checked=json.loads(table.read_text());assert checked['status']=='passed'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'svg.fonttype':'path',
        'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    sources=[PACKAGE/'results/ab_dummy_first_completed_snapshot.json',PACKAGE/'results/ir_compressed_completed_snapshot.json']
    data=[json.loads(p.read_text()) for p in sources]
    for a,p,ref in zip(data,sources,checked['artifacts']):
        assert ref['source_sha256']==sha(p)
        for receipt in a['receipts']:assert sha(PACKAGE/receipt['path'])==receipt['sha256']
    ab,ir=data;exports=[]
    # Figure 1: preserve an honest zoom near zero for GC-Ring -> R0.
    fig,axes=plt.subplots(1,2,figsize=(12.6,6.6),gridspec_kw={'width_ratios':[1.25,1]})
    order=[('D3','uniform','Uniform D3 / Uniform'),('D3','hot90','Uniform D3 / Hot-90'),
        ('bottom_D0','uniform','Bottom D0 / Uniform'),('bottom_D0','hot90','Bottom D0 / Hot-90')]
    series=[]
    for j,(layout,workload,label) in enumerate(order):
        for k,(new,name) in enumerate((('gc_ring','GC-Ring vs Ring'),('r0','R0 vs Ring'))):
            e=next(e for e in ab['effects'] if e['axis']=='backend' and e['condition']==layout and e['workload']==workload and e['baseline']=='ring' and e['variant']==new)
            y=j+(-.18,.18)[k];s=plot_effect(axes[0],e,y,COLORS[new],name if j==0 else None,f'ab_main_{j}_{k}')
            s['panel']='ab_main';series.append(s);axes[0].text(s['ci95'][1]+.18,y,f"{s['mean']:.2f}",va='center',fontsize=8)
        e=next(e for e in ab['effects'] if e['axis']=='backend' and e['condition']==layout and e['workload']==workload and e['baseline']=='gc_ring')
        s=plot_effect(axes[1],e,j,COLORS['r0'],None,f'ab_extra_{j}',height=.27);s['panel']='ab_extra';series.append(s)
        axes[1].text(.0094,j+.23,f"{s['mean']:+.4f}%",ha='right',va='center',fontsize=8)
        assert s['ci95'][0]<=0<=s['ci95'][1]
    axes[0].set(yticks=range(4),yticklabels=[x[2] for x in order],ylim=(-.6,3.6),xlim=(0,24),
        xlabel='Paired total communication reduction (%)',title='(a) Gain relative to Ring+CB')
    axes[1].set(yticks=range(4),yticklabels=[],ylim=(-.6,3.6),xlim=(-.008,.010),
        xlabel='R0 relative to GC-Ring+CB (%)',title='(b) Increment beyond the stronger control')
    axes[1].set_xticks([-.008,-.004,0,.004,.008])
    axes[1].axvline(0,color='#555555',ls='--',lw=.85)
    for ax in axes:ax.invert_yaxis();ax.grid(axis='x',alpha=.18);ax.set_axisbelow(True);ax.axhline(1.5,color='#bbbbbb',ls=':',lw=.8)
    references(axes[0],'ab_main',24);references(axes[1],'ab_extra',.010)
    axes[0].legend(frameon=False,ncol=2,loc='lower left',bbox_to_anchor=(0,1.06),fontsize=8)
    fig.subplots_adjust(left=.21,right=.975,top=.80,bottom=.32,wspace=.27)
    fig.text(.025,.95,'AB-CB adaptation: complete conditional bandwidth comparison',fontsize=13,weight='bold')
    fig.text(.025,.19,'N = 4,096; B = 64B; C5/A5/Y4, R = 500; top six levels cached; PLB8, LLC8 x 2; five paired seeds, 95% t intervals.\n'
        'One aligned warmup period + four measured periods; 2,560 measured requests, 40,960 public slots; authentication and maintenance included.',fontsize=8.5,color='#444444')
    fig.text(.025,.075,'The root is cached in both controls. All four GC-Ring-to-R0 intervals include zero; RPC counts are unchanged.\n'
        'Dummy-first with green fallback; no DeadQ, native AB, green-capacity/security proof, peak-memory or latency claim. Absolute costs are in Report 56.',fontsize=8.5,color='#444444')
    exports.append(export(fig,'completed_ab_cb_bandwidth',sources[0],series,dict(ab_main=24,ab_extra=.010),table))
    # Figure 2: main performance and every low-beta stress outcome.
    fig,axes=plt.subplots(1,2,figsize=(13.3,7.0),gridspec_kw={'width_ratios':[1.06,1.08]})
    order=[('uniform',False,'Uniform / DWB off'),('uniform',True,'Uniform / DWB on'),('hot90',False,'Hot-90 / DWB off'),('hot90',True,'Hot-90 / DWB on')]
    series=[]
    for j,(workload,dwb,label) in enumerate(order):
        for k,(base,name) in enumerate((('path','SDE vs Path'),('deferred','SDE vs Deferred'))):
            e=next(e for e in ir['effects'] if e['axis']=='backend' and e['cohort']=='main_beta14' and e['workload']==workload and e['dwb']==dwb and e['baseline']==base)
            y=j+(-.18,.18)[k];s=plot_effect(axes[0],e,y,COLORS[base],name if j==0 else None,f'ir_main_{j}_{k}')
            s['panel']='ir_main';series.append(s);axes[0].text(s['ci95'][1]+.20,y,f"{s['mean']:.2f}",va='center',fontsize=8)
    axes[0].set(yticks=range(4),yticklabels=[x[2] for x in order],ylim=(-.6,3.6),xlim=(0,22),
        xlabel='Paired total communication reduction (%)',title='(a) Main beta14 cohort: all 60 runs complete')
    axes[0].invert_yaxis();axes[0].grid(axis='x',alpha=.18);axes[0].set_axisbelow(True)
    axes[0].legend(frameon=False,ncol=2,loc='lower left',bbox_to_anchor=(0,1.07),fontsize=8)
    references(axes[0],'ir_main',22)
    outcomes=[];passed_color='#C2DCCB';stopped_color='#EFCEAD'
    for yi,kind in enumerate(('path','deferred','sde')):
        for xi,seed in enumerate(range(101,106)):
            o=next(o for o in ir['outcomes'] if o['spec']['cohort']=='reset_stress_beta4' and o['spec']['kind']==kind and o['spec']['trace_seed']==seed)
            success=o['status']=='passed';gid=f'stress_{kind}_{seed}';color=passed_color if success else stopped_color
            patch=Rectangle((xi-.47,yi-.43),.94,.86,facecolor=color,edgecolor='white',lw=1.5);patch.set_gid(gid);axes[1].add_patch(patch)
            if success:label='Full run\ncomplete'
            else:
                x=o['audit'];assert x['phase']=='warmup';label=f"Warmup\n{x['completed_requests']}/{x['offered_requests']}"
            axes[1].text(xi,yi,label,ha='center',va='center',fontsize=8)
            outcomes.append(dict(id=o['id'],gid=gid,kind=kind,seed=seed,status=o['status'],color=color,
                phase='measurement' if success else o['audit']['phase'],completed=o.get('completed',o.get('audit',{}).get('completed_requests')),
                offered=o.get('offered',o.get('audit',{}).get('offered_requests'))))
    axes[1].set(xticks=range(5),xticklabels=range(101,106),yticks=range(3),yticklabels=['Path','Deferred','SDE'],
        xlim=(-.5,4.5),ylim=(2.5,-.5),xlabel='Trace seed',title='(b) beta4 stress: 12/15 stop during warmup')
    axes[1].legend(handles=[Patch(facecolor=passed_color,label='All stages complete'),Patch(facecolor=stopped_color,label='Warmup unfinished')],
        frameon=False,ncol=2,loc='lower left',bbox_to_anchor=(-.03,1.07),fontsize=8)
    axes[1].spines[['bottom','left']].set_visible(False);axes[1].tick_params(length=0)
    fig.subplots_adjust(left=.17,right=.985,top=.79,bottom=.33,wspace=.35)
    fig.text(.025,.95,'IR-style compressed maps: bandwidth and counter-reset stress',fontsize=13,weight='bold')
    fig.text(.025,.20,'N = 4,096; B = 64B; X = 32; heterogeneous buckets, L12/A3/R480; cached levels 0-5; PLB8, LLC8 x 2.\n'
        'Main cohort: 1,536 warmup + 6,144 measured requests; 12,288 + 49,152 public slots; five paired seeds and 95% t intervals.',fontsize=8.5,color='#444444')
    fig.text(.025,.085,'Stress cohort: Hot-90, DWB on, beta4; all 15 predeclared outcomes are shown. Unfinished runs are excluded from performance ratios; no survivor-only mean.\n'
        'All protocol bytes counted. Dirty LLC/reset state may remain; finite windows; no native IR-Stash/PMMAC, complete security proof or latency claim.',fontsize=8.5,color='#444444')
    exports.append(export(fig,'completed_ir_compressed',sources[1],series,dict(ir_main=22),table,dict(stress_outcomes=outcomes)))
    save(PACKAGE/'results/ab_ir_completed_exports.json',dict(status='generated',generator_sha256=sha(__file__),figures=exports))
    print(json.dumps(dict(status='generated',figures=2,numeric_bars=20,stress_cells=15,formats=['svg','png'])))


if __name__=='__main__':main()
