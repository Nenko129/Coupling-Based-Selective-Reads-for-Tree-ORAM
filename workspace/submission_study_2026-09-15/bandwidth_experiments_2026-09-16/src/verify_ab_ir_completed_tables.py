"""Independent full-matrix/statistical checks, including incomplete IR cases."""
from common import *
import copy
import itertools
import math
from verify_free_sensitivity_tables import check_stat


def read_refs(a):
    records={}
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];r=json.loads(p.read_text())
        assert r['spec']['id']==ref['id'] and ref['id'] not in records;records[ref['id']]=r
    return records


def check_cell(c,records,ir=False):
    rs=[records[i] for i in c['ids']]
    assert [r['spec']['trace_seed'] for r in rs]==list(range(101,106))
    if ir:
        assert all((r['spec']['cohort'],r['spec']['workload'],r['spec']['dwb'],r['spec']['kind'])==(c['cohort'],c['workload'],c['dwb'],c['kind']) for r in rs)
        passed=sum(r['status']=='passed' for r in rs)
        assert c['completed']==passed and c['expected']==5 and c['eligible_for_performance']==(passed==5)
        if passed<5:
            assert not any(k in c for k in ('bytes','rpc','frontend','map_metrics','components'))
            return
    else:
        assert all(('D3' if r['spec']['bottom_dummy'] is None else 'bottom_D0',r['spec']['workload'],r['spec']['kind'])==(c['layout'],c['workload'],c['kind']) for r in rs)
    assert all(r['status']=='passed' for r in rs)
    ms=[r['phases']['measurement'] for r in rs]
    check_stat(c['bytes'],[m['total_bytes']/m['requests'] for m in ms])
    check_stat(c['rpc'],[m['rpc']/m['requests'] for m in ms])
    expected={k for m in ms for k in m['bills'][0]['components']};assert set(c['components'])==expected
    for key in expected:check_stat(c['components'][key],[m['bills'][0]['components'].get(key,0)/m['requests'] for m in ms])
    for dest,rawkey in [('frontend','frontend_metrics'),('map_metrics','map_metrics')] if ir else [('frontend','frontend_metrics'),('cb','cb_metrics')]:
        keys={k for m in ms for k in m[rawkey]};assert set(c[dest])==keys
        for key in keys:check_stat(c[dest][key],[m[rawkey].get(key,0) for m in ms])
    if not ir:
        assert set(c['stages'])=={k for m in ms for k in m['bills'][0]['by_stage']}
        for key in c['stages']:check_stat(c['stages'][key],[sum(m['bills'][0]['by_stage'].get(key,{}).values())/m['requests'] for m in ms])
        hs=[{int(k):v for k,v in m['boundary_stash_histogram'].items()} for m in ms]
        assert c['observed_boundary_stash_max']==[max(h) for h in hs]
        check_stat(c['observed_boundary_stash_mean'],[sum(k*v for k,v in h.items())/sum(h.values()) for h in hs])
    for r in rs:
        res=c['resource'];assert res['server']==r['server_storage'] and not res['actual_peak']
        p=r['frontend_memory_representation'];f=p['plb']
        expected=dict(tree_cache=r['cache_representation']['bytes'],stash_payload=f['stash_reserved_bytes'],plb_payload=f['plb_payload_bytes'],
            plb_leaf_address=f['plb_leaf_and_address_bytes'],terminal_leaf=f['terminal_leaf_bytes'],llc_payload=p['llc_payload_capacity'])
        assert res['selected_client']==expected and res['selected_client_sum']==sum(expected.values())


def check_effect(e,records,ir=False):
    values=[];rpcs=[];left=[];right=[];seeds=[];parts={}
    for p in e['pairs']:
        l,r=[records[p[k]] for k in (('before','after') if ir else ('baseline_id','variant_id'))]
        assert l['status']==r['status']=='passed' and l['trace']==r['trace'] and l['answer_sha256']==r['answer_sha256']
        sl,sr=l['spec'],r['spec'];assert sl['trace_seed']==sr['trace_seed']==p['seed'];seeds.append(p['seed'])
        assert sl['workload']==sr['workload']==e['workload']
        axis=e['axis']
        if axis=='backend':
            assert (sl['kind'],sr['kind'])==(e['baseline'],e['variant'])
            if ir:assert sl['cohort']==sr['cohort']==e['cohort'] and sl['dwb']==sr['dwb']==e['dwb']
            else:assert ('D3' if sl['bottom_dummy'] is None else 'bottom_D0')==('D3' if sr['bottom_dummy'] is None else 'bottom_D0')==e['condition']
        elif axis=='layout':assert sl['kind']==sr['kind']==e['condition'] and sl['bottom_dummy'] is None and sr['bottom_dummy']==0
        elif axis=='dwb':assert not sl['dwb'] and sr['dwb'] and sl['kind']==sr['kind']==e['variant']
        elif axis=='packing':assert sl['X']==16 and sr['X']==32 and sr['beta']==14 and sl['kind']==sr['kind']==e['variant']
        elif axis=='beta':assert sl['beta']==14 and sr['beta']==4 and sl['kind']==sr['kind']==e['variant']
        else:raise AssertionError(axis)
        ml,mr=[z['phases']['measurement'] for z in (l,r)]
        assert ml['requests']==mr['requests'] and ml['public_slots']==mr['public_slots']
        x,y=[m['total_bytes']/m['requests'] for m in (ml,mr)];left.append(x);right.append(y)
        value=100*(1-y/x);values.append(value);assert math.isclose(p['saving_pct'],value,abs_tol=1e-10)
        rpcs.append(100*(1-mr['rpc']/ml['rpc']))
        if not ir:
            keys=set(ml['bills'][0]['components'])|set(mr['bills'][0]['components']);assert set(p['component_saved_bytes'])==keys
            for key in keys:
                diff=(ml['bills'][0]['components'].get(key,0)-mr['bills'][0]['components'].get(key,0))/ml['requests']
                assert math.isclose(p['component_saved_bytes'][key],diff,abs_tol=1e-10);parts.setdefault(key,[]).append(diff)
    assert seeds==list(range(101,106));check_stat(e['paired_saving_pct'],values);check_stat(e['paired_rpc_saving_pct'],rpcs)
    assert math.isclose(e['baseline_mean'],sum(left)/5) and math.isclose(e['variant_mean'],sum(right)/5)
    if not ir:
        assert set(e['component_saved_bytes'])==set(parts)
        for key,xs in parts.items():check_stat(e['component_saved_bytes'][key],xs)
    cvs=[math.sqrt(sum((v-sum(xs)/5)**2 for v in xs)/4)/(sum(xs)/5) for xs in (left,right)]
    assert all(math.isclose(x,y,abs_tol=1e-12) for x,y in zip(cvs,e['run_cost_cv']))
    ci=e['paired_saving_pct']['ci95'];assert e['needs_more_repeats']==(max(cvs)>.10 or (ci[1]-ci[0])/2>5)


def verify_ab(a,records):
    assert len(records)==a['runs']==60 and len(a['cells'])==12 and len(a['effects'])==18
    assert not any(a[k] for k in ('security_admission','native_AB','DeadQ','true_client_peak_measured','latency_claim'))
    coords={(c['layout'],c['workload'],c['kind']) for c in a['cells']}
    assert coords==set(itertools.product(('D3','bottom_D0'),('uniform','hot90'),('ring','gc_ring','r0')))
    covered=[]
    for c in a['cells']:check_cell(c,records);covered+=c['ids']
    assert len(covered)==len(set(covered))==60
    keys={(e['axis'],e['condition'],e['workload'],e['baseline'],e['variant']) for e in a['effects']}
    expected={('backend',l,w,b,v) for l in ('D3','bottom_D0') for w in ('uniform','hot90') for b,v in (('ring','gc_ring'),('ring','r0'),('gc_ring','r0'))}
    expected|={('layout',k,w,'D3','bottom_D0') for k in ('ring','gc_ring','r0') for w in ('uniform','hot90')};assert keys==expected
    for e in a['effects']:check_effect(e,records)


def verify_ir(a,records):
    assert len(records)==135 and a['new_outcomes']==75 and a['reused_raw_controls']==60
    assert not any(a[k] for k in ('native_IR','IR_Stash','PMMAC','adaptive_security_proof','actual_peak_measured','latency_claim'))
    assert len(a['outcomes'])==75 and len({o['id'] for o in a['outcomes']})==75
    assert sum(o['status']=='passed' for o in a['outcomes'])==a['passed'] and a['passed']+a['incomplete']==75
    for o in a['outcomes']:
        r=records[o['id']];assert o['spec']==r['spec']
        if o['status']=='passed':assert r['status']=='passed' and o['completed']==o['offered']==r['spec']['requests']
        else:
            assert r['status']=='failed' and o['spec']['cohort']=='reset_stress_beta4'
            assert not o['audit']['eligible_for_completed_request_bandwidth_comparison']
            assert o['audit']['total_bytes']==r['partial_bill']['total_bytes']
            assert o['audit']['completed_requests']==r['completed_this_phase']<o['audit']['offered_requests']
    assert len(a['cells'])==15
    covered=[]
    for c in a['cells']:check_cell(c,records,True);covered+=c['ids']
    assert len(covered)==len(set(covered))==75
    assert set(covered)=={o['id'] for o in a['outcomes']}
    assert len(a['effects'])+len(a['excluded_effects'])==31
    key=lambda e:(e['axis'],e['cohort'],e['workload'],e['dwb'],e['baseline'],e['variant'])
    expected={('backend','main_beta14',w,d,b,'sde') for w in ('uniform','hot90') for d in (False,True) for b in ('path','deferred')}
    expected|={('backend','reset_stress_beta4','hot90',True,b,'sde') for b in ('path','deferred')}
    expected|={('dwb','main_beta14',w,True,k,k) for w in ('uniform','hot90') for k in ('path','deferred','sde')}
    expected|={('packing','main_beta14',w,d,k,k) for w in ('uniform','hot90') for d in (False,True) for k in ('path','deferred','sde')}
    expected|={('beta','beta14_to_beta4','hot90',True,k,k) for k in ('path','deferred','sde')}
    assert {key(e) for e in a['effects']+a['excluded_effects']}==expected
    for e in a['effects']:check_effect(e,records,True)
    for e in a['excluded_effects']:
        assert len(e['pairs'])==5 and any(records[l]['status']!='passed' or records[r]['status']!='passed' for l,r in e['pairs'])
        assert not any(k in e for k in ('paired_saving_pct','baseline_mean','variant_mean'))


def main():
    artifacts=[];negative=[]
    for family,verify,producer,report in (
        ('ab_dummy_first',verify_ab,'freeze_ab_dummy_first_completed.py','56_AB_CB完整结果与强基线.md'),
        ('ir_compressed',verify_ir,'freeze_ir_compressed_completed.py','58_IR压缩位置表完整结果.md')):
        source=PACKAGE/f'results/{family}_completed_snapshot.json';a=json.loads(source.read_text());records=read_refs(a)
        assert a['producer_sha256']==sha(Path(__file__).parent/producer)
        for name,value in a['helper_hashes'].items():assert sha(Path(__file__).parent/name)==value
        verify(a,records)
        md=(PACKAGE/report).read_text(encoding='utf-8')
        for e in a['effects']:
            x=e['paired_saving_pct'];lo,hi=x['ci95']
            assert f"{x['mean']:.4f}%" in md and f"[{lo:.4f}, {hi:.4f}]%" in md
        def reject(name,fn):
            damaged=copy.deepcopy(a);fn(damaged)
            try:verify(damaged,records)
            except (AssertionError,KeyError):negative.append(family+': '+name)
            else:raise AssertionError('bad snapshot accepted: '+name)
        reject('changed mean with intact runs',lambda x:x['effects'][0]['paired_saving_pct'].update(mean=99))
        reject('changed cell component mean',lambda x:x['cells'][0]['components']['data_download'].update(mean=0))
        reject('missing planned comparison',lambda x:x['effects'].pop())
        reject('duplicate comparison hides planned cell',lambda x:x['effects'].__setitem__(1,copy.deepcopy(x['effects'][0])))
        if family=='ab_dummy_first':reject('mislabel GC-Ring denominator',lambda x:x['effects'][0].update(baseline='gc_ring'))
        else:
            reject('drop failed outcome',lambda x:x['outcomes'].pop())
            reject('admit survivor-only stress cell',lambda x:next(c for c in x['cells'] if c['completed']<5).update(eligible_for_performance=True))
        artifacts.append(dict(family=family,source_sha256=sha(source),report_sha256=sha(PACKAGE/report),runs=len(records),cells=len(a['cells']),effects=len(a['effects']),incomplete=a.get('incomplete',0)))
    out=dict(status='passed',artifacts=artifacts,rejected_corruptions=negative,checker_sha256=sha(__file__),
        statistical_checker_sha256=sha(Path(__file__).parent/'verify_free_sensitivity_tables.py'),security_admission=False)
    save(PACKAGE/'results/ab_ir_completed_tables_audit.json',out)
    print(json.dumps(dict(status='passed',artifacts=artifacts,rejected_corruptions=len(negative))))


if __name__=='__main__':main()
