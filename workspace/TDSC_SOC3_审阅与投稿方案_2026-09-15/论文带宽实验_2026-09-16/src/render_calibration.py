"""Completed model calibration: independently recompute errors, then export."""
from common import *
import csv,math,statistics
from collections import defaultdict
from analyze_extended_results import audit_record
from optimized_oram import Config
from optimized_cost import expected_tree,sum_rows
sys.path.insert(0,str(PACKAGE/'.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def stats(values):
    assert len(values)==5
    mean=statistics.mean(values);half=2.7764451051977987*statistics.stdev(values)/math.sqrt(5)
    return dict(n=5,mean=mean,ci95=[mean-half,mean+half],per_seed=values)


def answer_digest(record):
    s=record['spec'];p=PACKAGE/record['trace']['path'];assert sha(p)==record['trace']['sha256']
    t=json.loads(p.read_text());assert (t['N'],t['count'],t['seed'],t['workload'])==(s['N'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    versions=[0]*s['N'];h=hashlib.sha256()
    for a,v in t['rows']:
        h.update(hashlib.shake_256(b'SOC3-EVAL-PAYLOAD-v1'+a.to_bytes(8,'big')+versions[a].to_bytes(8,'big')).digest(s['B']))
        if v is not None:versions[a]=v
    assert len(t['rows'])==s['warmup']+s['requests'];return h.hexdigest()


def main():
    path=PACKAGE/'formal_calibration_plan.json';plan=json.loads(path.read_text());assert len(plan['items'])==40
    grouped=defaultdict(list);raw=[];receipts=[];models={}
    for item in plan['items']:
        s=item['spec'];p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json";r=json.loads(p.read_text())
        assert audit_record(r,s,item['entry']) and r['answer_sha256']==answer_digest(r)
        c,=r['configs'];assert s['N']==256 and s['B']==64 and s['requests']==3072 and s['period_slots']==768
        assert s['requests']==4*s['period_slots'] and (r['final_clock'][0]['t']-s['requests'])%s['period_slots']==0
        assert r['phases']['measurement']['backend_requests']==[s['requests']]
        model=sum_rows([expected_tree(Config(**c))]);assert model==r['expected_periodic_cost']
        key=(s['kind'],tuple(s['profile']));v=r['phases']['measurement']['total_bytes']/s['requests']
        expected=(float(model['total']['lower'])+float(model['total']['upper']))/2
        models[key]=expected;grouped[key].append(dict(seed=s['trace_seed'],actual=v,error_pct=100*(v/expected-1)))
        row=dict(id=s['id'],kind=s['kind'],Z=s['profile'][0],A=s['profile'][1],S=s['profile'][2],L=c['L'],N=s['N'],B=s['B'],
            seed=s['trace_seed'],warmup=s['warmup'],requests=s['requests'],model_bytes_per_request=expected,actual_bytes_per_request=v,
            model_relative_error_pct=100*(v/expected-1),measurement_total_bytes=r['phases']['measurement']['total_bytes'],
            source_path=str(p.relative_to(PACKAGE)),source_sha256=sha(p))
        raw.append(row);receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    order=[(k,(4,3,3)) for k in ('path','deferred','sde','ring','gc_ring','r0')]+[(k,(7,6,6)) for k in ('ring','r0')]
    groups=[]
    for key in order:
        rs=sorted(grouped[key],key=lambda x:x['seed']);assert [r['seed'] for r in rs]==list(range(101,106))
        groups.append(dict(kind=key[0],profile=list(key[1]),model_bytes=models[key],observed_bytes=stats([r['actual'] for r in rs]),
            model_relative_error_pct=stats([r['error_pct'] for r in rs])))
    snapshot=dict(plan_sha256=sha(path),receipts=receipts,groups=groups,runs=40,configs=8,
        scope='N256/B64, no recursion, uniform accesses, four aligned measurement reference windows; no steady-state or large-scale accuracy claim')
    snap=PACKAGE/'results/calibration_completed_snapshot.json'
    if snap.exists():assert json.loads(snap.read_text())==snapshot
    else:save(snap,snapshot)
    outputs=[]
    def csv_out(name,rows):
        p=PACKAGE/'tables'/name
        with p.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    csv_out('Calibration_40_runs.csv',raw)
    csv_out('Calibration_8_configurations.csv',[dict(kind=g['kind'],Z=g['profile'][0],A=g['profile'][1],S=g['profile'][2],n=5,
        model_bytes_per_request=g['model_bytes'],actual_mean_bytes=g['observed_bytes']['mean'],actual_ci95_lower=g['observed_bytes']['ci95'][0],
        actual_ci95_upper=g['observed_bytes']['ci95'][1],mean_error_pct=g['model_relative_error_pct']['mean'],
        error_ci95_lower=g['model_relative_error_pct']['ci95'][0],error_ci95_upper=g['model_relative_error_pct']['ci95'][1],
        source_snapshot_sha256=sha(snap)) for g in groups])
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'svg.fonttype':'none','figure.dpi':150,'savefig.dpi':180})
    names={'path':'Path','deferred':'Deferred','sde':'SDE','ring':'Ring','gc_ring':'GC-Ring','r0':'R0'}
    labels=[names[g['kind']]+' ('+','.join(map(str,g['profile']))+')' for g in groups]
    fig,(left,right)=plt.subplots(1,2,figsize=(10.5,5.3),gridspec_kw={'width_ratios':[1.1,1]},sharey=True)
    for i,g in enumerate(groups):
        left.barh(i-.17,g['model_bytes']/1024,.29,color='#b7bec7',label='Analytic expectation' if i==0 else None)
        mean=g['observed_bytes']['mean'];lo,hi=g['observed_bytes']['ci95']
        left.barh(i+.17,mean/1024,.29,color='#486da6',label='Measured mean' if i==0 else None)
        left.errorbar(mean/1024,i+.17,xerr=[[(mean-lo)/1024],[(hi-mean)/1024]],fmt='none',color='#222222',capsize=2,linewidth=.9)
        error=g['model_relative_error_pct'];m=error['mean'];lo,hi=error['ci95']
        right.errorbar(m,i,xerr=[[m-lo],[hi-m]],fmt='o',markersize=5,color='#188977',capsize=3)
        right.text(.80,i,f'{m:+.3f}%',va='center',ha='right',fontsize=8)
    left.set(yticks=range(8),yticklabels=labels,xlabel='Total serialized communication (KiB / request)',xlim=(0,21),title='Expected and measured traffic')
    left.invert_yaxis();left.legend(loc='lower right',frameon=False,fontsize=8)
    right.set(xlabel='100 x (measured / model - 1) (%)',xlim=(-.55,.85),xticks=[-.4,-.2,0,.2,.4],title='Model error with 95% t intervals')
    right.axvline(0,color='#666666',linewidth=1,linestyle='--');right.tick_params(axis='y',left=False)
    for ax in (left,right):ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
    fig.subplots_adjust(left=.16,right=.98,top=.88,bottom=.23,wspace=.17)
    fig.text(.035,.035,'COMPLETE CALIBRATION  |  N = 256; B = 64 B; 8 configurations x 5 runs; 3,072 measured requests per run.\nLabels show (Z,A,S). Path uses an equal-length reference window; other protocols cover four full maintenance cycles.\nNo recursive maps or network latency are measured. Model agreement at this scale does not certify larger configurations.',fontsize=8,color='#555555')
    for ext in ('pdf','svg','png'):
        p=PACKAGE/'figures'/f'completed_model_calibration.{ext}';fig.savefig(p,bbox_inches='tight');outputs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    plt.close(fig)
    save(PACKAGE/'results/calibration_exports.json',dict(status='generated',source_snapshot_sha256=sha(snap),generator_sha256=sha(__file__),
        outputs=outputs,model_recomputed_for_all_runs=True,answers_independently_recomputed=True,visual_review_pending=True))
    print(json.dumps(dict(runs=40,groups=8,max_absolute_mean_error_pct=max(abs(g['model_relative_error_pct']['mean']) for g in groups))))


if __name__=='__main__':main()
