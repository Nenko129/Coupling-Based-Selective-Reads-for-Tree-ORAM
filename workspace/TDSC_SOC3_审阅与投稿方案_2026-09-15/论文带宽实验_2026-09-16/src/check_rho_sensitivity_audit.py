"""Verify partial/full rho statistics and reject meaningful corruptions."""
from common import *
import copy, math
from fractions import Fraction
from verify_free_sensitivity_tables import check_stat
from audit_rho_sensitivity import audit


def main():
    p=PACKAGE/'results/rho_sensitivity_audit.json';a=json.loads(p.read_text(encoding='utf-8'))
    assert a['auditor_sha256']==sha(Path(__file__).parent/'audit_rho_sensitivity.py')
    assert a['completed']+len(a['missing'])+len(a['pending_final_receipt'])==180
    assert a['completed']==a['new_completed']+60 and a['new_expected']==120
    for field in ('plan_hashes','proof_hashes'):
        for path,value in a[field].items():assert sha(PACKAGE/path)==value
    for path,value in a['helpers'].items():assert sha(Path(__file__).parent/path)==value
    records={}
    for x in a['receipts']:
        path=PACKAGE/x['path'];assert sha(path)==x['sha256'];records[x['id']]=json.loads(path.read_text(encoding='utf-8'))
    assert len(records)==a['completed']
    for c in a['cells']:
        rs=[records[i] for i in c['ids']];assert [r['spec']['trace_seed'] for r in rs]==list(range(101,106))
        for r in rs:
            s=r['spec'];assert s['kind']==c['kind']
            assert s['workload']+'/'+s.get('condition','base')==c['configuration']
            assert (s['llc'],s['rho'],s.get('frame_ratio',3))==(c['llc'],c['rho'],c['frame_ratio'])
        ms=[r['phases']['measurement'] for r in rs]
        check_stat(c['bytes'],[x['total_bytes']/4096 for x in ms]);check_stat(c['rpc'],[x['rpc']/4096 for x in ms])
        check_stat(c['front_bytes'],[x['bills'][0]['total_bytes']/4096 for x in ms])
        check_stat(c['backend_bytes'],[x['bills'][1]['total_bytes']/4096 for x in ms])
        for k,s in c['frontend_metrics'].items():check_stat(s,[x['frontend_metrics'].get(k,0) for x in ms])
    for e in a['effects']+a['parameter_effects']:
        values=[];rpc=[];shares=[];backend=[];left=[];right=[]
        for pair in e['pairs']:
            l,r=[records[pair[k]] for k in ('baseline_id','variant_id')]
            x,y=[v['phases']['measurement'] for v in (l,r)]
            assert l['trace']==r['trace'] and l['answer_sha256']==r['answer_sha256']
            values.append(100*(1-y['total_bytes']/x['total_bytes']));rpc.append(100*(1-y['rpc']/x['rpc']))
            assert pair['baseline_bytes']==x['total_bytes']/4096 and pair['variant_bytes']==y['total_bytes']/4096
            left.append(pair['baseline_bytes']);right.append(pair['variant_bytes'])
            if 'backend_share_pct' in pair:
                f,b=x['bills'][0]['total_bytes'],x['bills'][1]['total_bytes'];nb=y['bills'][1]['total_bytes']
                assert x['bills'][0]==y['bills'][0]
                assert Fraction(b-nb,f+b)==Fraction(b,f+b)*Fraction(b-nb,b)
                shares.append(100*b/(f+b));backend.append(100*(1-nb/b))
        check_stat(e['bytes_saving_pct'],values);check_stat(e['rpc_saving_pct'],rpc)
        if shares:check_stat(e['backend_share_pct'],shares);check_stat(e['backend_saving_pct'],backend)
        assert math.isclose(e['baseline_mean'],sum(left)/5) and math.isclose(e['variant_mean'],sum(right)/5)
        cvs=[math.sqrt(sum((v-sum(vs)/5)**2 for v in vs)/4)/(sum(vs)/5) for vs in (left,right)]
        needs=max(cvs)>.10 or (e['bytes_saving_pct']['ci95'][1]-e['bytes_saving_pct']['ci95'][0])/2>5
        assert needs==e['needs_more_repeats']
    sample=next(r for r in records.values() if r['spec'].get('condition')=='llc8' and r['spec']['kind']=='sde')
    mutations=[]
    def case(name,fn):
        r=copy.deepcopy(sample);fn(r)
        try:audit(r,sample['spec'],True,{}, {})
        except (AssertionError,KeyError):mutations.append(name)
        else:raise AssertionError('accepted corrupted receipt: '+name)
    def change_hits(r):
        m=r['phases']['measurement']['frontend_metrics']
        m['llc_hits']+=1;m['llc_misses']-=1;m['rho_hits']-=1
    case('self-consistent but wrong cache-hit totals',change_hits)
    case('wrong front remove/admit stream',lambda r:r['phases']['measurement']['schedules'][0].update(remove_admit_sha256='0'*64))
    case('wrong backend slots',lambda r:r['phases']['measurement']['schedules'][1].update(slots=1))
    case('missing full backend position map',lambda r:r['frontend_memory_representation'].update(flat_backend_posmap_bytes=0))
    case('wrong answer digest',lambda r:r.update(answer_sha256='0'*64))
    case('wrong frame-ratio claim',lambda r:r['extended_experiment']['parameters'].update(frame_ratio=1))
    report=PACKAGE/'50_rho敏感性独立统计.md'
    out=dict(status='passed',source_sha256=sha(p),report_sha256=sha(report),checker_sha256=sha(__file__),
        statistical_helper_sha256=sha(Path(__file__).parent/'verify_free_sensitivity_tables.py'),
        checked_runs=len(records),checked_cells=len(a['cells']),checked_effects=len(a['effects'])+len(a['parameter_effects']),
        rejected_corruptions=mutations,all_planned_runs_complete=a['completed']==180,new_security_proof=False)
    save(PACKAGE/'results/rho_sensitivity_checks.json',out)
    print(json.dumps(out))


if __name__=='__main__':main()
