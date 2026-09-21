from pathlib import Path
import csv,json,sys
sys.path.insert(0,'D:/projects/SDE-R0/TDSC_SOC3_审阅与投稿方案_2026-09-15/论文带宽实验_2026-09-16/.plot-deps')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path('D:/projects/SDE-R0/TDSC_SOC3_审阅与投稿方案_2026-09-15')
P=ROOT/'Selective_通用组合与投稿实验准备_2026-09-16/论文实验章节完整证据_2026-09-16'
O=ROOT/'投稿证据复核与文献整理_2026-09-17/写作修订稿/figures'
O.mkdir(parents=True,exist_ok=True)
def read(name):
 with (P/'tables'/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(fig,name):
 for ext in ['png','svg','pdf']:fig.savefig(O/(name+'.'+ext),dpi=220,bbox_inches='tight')
 plt.close(fig)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
names={'free_compressed':'Freecursive-style','rho':'rho-style','IR':'IR-style','AB':'AB-style'}
rows=read('table_03_minimal_composition.csv')
rows=sorted(rows,key=lambda r:(r['layout']=='uniform',list(names).index(r['family']),int(r['B'])))
labels=[f"{names[r['family']]}, B={int(r['B']):,}"+(" (uniform-layout control)" if r['layout']=='uniform' else '') for r in rows]
vals=np.array([float(r['bytes_saving_pct']) for r in rows]);low=np.array([float(r['ci95_low_pct']) for r in rows]);high=np.array([float(r['ci95_high_pct']) for r in rows])
fig,ax=plt.subplots(figsize=(9,5.2));y=np.arange(len(rows))
ax.barh(y,vals,xerr=[vals-low,high-vals],color=['#8a919c' if r['layout']=='uniform' else '#0f8b8d' for r in rows],capsize=3,height=.66)
ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlim(0,30);ax.set_xlabel('Paired communication saving (%)');ax.set_title('Architecture-adapted minimal compositions')
ax.set_axisbelow(True);ax.grid(axis='x',alpha=.18)
for yy,v in zip(y,vals):ax.text(v+.35,yy,f'{v:.2f}%',va='center',fontsize=9)
fig.text(.03,.005,'Eight main configurations + two layout controls; n=5. Error bars: 95% paired t intervals.',fontsize=9)
fig.tight_layout(rect=(0,.025,1,1));save(fig,'fig_03_minimal_composition_reviewed')

base={(r['family'],r['layout'],r['B']):r for r in rows}
ctr=read('table_04_attribution_controls.csv');x=np.arange(len(ctr));width=.34
fig,ax=plt.subplots(figsize=(8.6,4.5))
for off,label,color,rr in [(-width/2,'Adapted base → selective','#17324d',[base[(r['family'],r['layout'],r['B'])] for r in ctr]),(width/2,'Full-probe → selective','#d89b2b',ctr)]:
 v=np.array([float(r['bytes_saving_pct']) for r in rr]);lo=np.array([float(r['ci95_low_pct']) for r in rr]);hi=np.array([float(r['ci95_high_pct']) for r in rr])
 ax.bar(x+off,v,width,yerr=[v-lo,hi-v],label=label,color=color,capsize=3)
ax.set_xticks(x,[f"{r['family']}-style\nB={int(r['B']):,}" for r in ctr]);ax.set_ylim(0,31)
ax.set_ylabel('Paired communication saving (%)');ax.set_title('Net composition and placement-controlled attribution');ax.legend(frameon=False,loc='upper right')
ax.set_axisbelow(True);ax.grid(axis='y',alpha=.18);fig.tight_layout();save(fig,'fig_04_attribution_control_reviewed')

rows=read('table_06_public_workloads.csv');workloads=list(dict.fromkeys(r['workload'] for r in rows))
fig,axs=plt.subplots(1,len(workloads),figsize=(11,4),sharex=True)
for ax,wl in zip(axs,workloads):
 rr=[r for r in rows if r['workload']==wl];v=np.array([float(r['bytes_saving_pct']) for r in rr]);lo=np.array([float(r['ci95_low_pct']) for r in rr]);hi=np.array([float(r['ci95_high_pct']) for r in rr]);y=np.arange(len(rr))
 ax.barh(y,v,xerr=[v-lo,hi-v],color=['#17324d' if r['variant']=='sde' else '#0f8b8d' for r in rr],capsize=3,height=.58)
 ax.set_yticks(y,[names[r['family']]+'\n'+r['baseline']+' → '+r['variant'] for r in rr]);ax.invert_yaxis();ax.set_xlim(0,29)
 for yy,vv in zip(y,v):ax.text(vv+.35,yy,f'{vv:.2f}%',va='center',fontsize=9)
 ax.set_title(wl.replace('_startkey',''));ax.set_xlabel('Communication saving (%)');ax.set_axisbelow(True);ax.grid(axis='x',alpha=.18)
fig.suptitle('Public-workload results for integrated adapters',fontsize=12)
fig.tight_layout();save(fig,'fig_06_public_workloads_reviewed')
(O/'README.md').write_text('这三幅图沿用原CSV与置信区间，未修改实验数据。Fig.3区分8个主格与2个布局控制并收紧标题；Fig.4移除误导性的native/base标识；Fig.6改为分面横条图，消除原图长标签重叠，并明确属于integrated adapters。原冻结包保持不变。\n',encoding='utf-8')
print(str(O))
