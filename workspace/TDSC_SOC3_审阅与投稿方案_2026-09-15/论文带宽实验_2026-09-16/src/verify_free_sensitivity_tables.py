"""Independently recompute the frozen JSON and Markdown table from raw bills."""
from common import *
import math


def check_stat(got, values):
    assert len(values) == got['n'] == 5
    mean = sum(values)/5
    half = 2.7764451051977987*math.sqrt(sum((v-mean)**2 for v in values)/20)
    expected = [mean,mean-half,mean+half,*values]
    actual = [got['mean'],*got['ci95'],*got['values']]
    assert len(actual) == len(expected)
    assert all(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-9) for a,b in zip(actual,expected))


def main():
    p=PACKAGE/'results/free_sensitivity_completed_audit.json'; a=json.loads(p.read_text(encoding='utf-8'))
    assert a['status']=='passed' and a['runs']==160 and a['new_sensitivity_runs']==100 and a['reused_control_runs']==60
    assert a['auditor_sha256']==sha(Path(__file__).parent/'audit_free_sensitivity_completed.py')
    for container in ('plan_hashes','proof_hashes'):
        for path,value in a[container].items():assert sha(PACKAGE/path)==value
    for path,value in a['helper_sha256'].items():assert sha(Path(__file__).parent/path)==value
    assert not any(a[k] for k in ('native_full_system','security_proof','true_client_peak_measured','latency_claim'))
    records={}
    for entry in a['receipts']:
        path=PACKAGE/entry['path'];assert sha(path)==entry['sha256']
        r=json.loads(path.read_text(encoding='utf-8'));assert r['spec']['id']==entry['id']
        records[entry['id']]=r
    assert len(records)==160
    assert len(a['cells'])==32
    covered=[]
    for c in a['cells']:
        rs=[records[i] for i in c['ids']];covered+=c['ids']
        assert sorted(r['spec']['trace_seed'] for r in rs)==list(range(101,106))
        for r in rs:
            s=r['spec'];assert s['kind']==c['kind'] and '/'.join((s['family'],s['workload'],s.get('condition','B64_base')))==c['configuration']
        ms=[r['phases']['measurement'] for r in rs]
        check_stat(c['bytes'],[x['total_bytes']/x['requests'] for x in ms])
        check_stat(c['rpc'],[x['rpc']/x['requests'] for x in ms])
        check_stat(c['slots'],[x['schedules'][0]['slots'] for x in ms])
        for k,stat in c['frontend_metrics'].items():check_stat(stat,[x['frontend_metrics'].get(k,0) for x in ms])
    assert len(covered)==len(set(covered))==160
    report=PACKAGE/'49_Freecursive敏感性完整结果.md'; markdown=report.read_text(encoding='utf-8')
    groups=a['selective_effects']+a['parameter_effects'];assert len(groups)==36
    for e in groups:
        savings=[];rpcs=[];left=[];right=[]
        for pair in e['pairs']:
            aa=records[pair['baseline_id']];bb=records[pair['variant_id']]
            assert aa['trace']==bb['trace'] and aa['answer_sha256']==bb['answer_sha256']
            assert aa['spec']['B']==bb['spec']['B']
            x,y=aa['phases']['measurement'],bb['phases']['measurement']
            l=x['total_bytes']/x['requests'];r=y['total_bytes']/y['requests']
            saving=100*(1-y['total_bytes']/x['total_bytes']);rpc=100*(1-y['rpc']/x['rpc'])
            assert (l,r,saving,rpc)==(pair['baseline_bytes'],pair['variant_bytes'],pair['saving_pct'],pair['rpc_saving_pct'])
            left.append(l);right.append(r);savings.append(saving);rpcs.append(rpc)
        check_stat(e['bytes_saving_pct'],savings);check_stat(e['rpc_saving_pct'],rpcs)
        assert math.isclose(e['baseline_mean'],sum(left)/5) and math.isclose(e['variant_mean'],sum(right)/5)
        cvs=[math.sqrt(sum((v-sum(vs)/5)**2 for v in vs)/4)/(sum(vs)/5) for vs in (left,right)]
        needs=max(cvs)>.10 or (e['bytes_saving_pct']['ci95'][1]-e['bytes_saving_pct']['ci95'][0])/2>5
        assert needs==e['needs_more_repeats']
        x=e['bytes_saving_pct'];lo,hi=x['ci95']
        exact=f"| {e['name']} | {e['baseline_mean']:,.2f} | {e['variant_mean']:,.2f} | {x['mean']:.3f}% / [{lo:.3f}, {hi:.3f}]% |"
        assert markdown.count(exact)==1
    result=dict(status='passed',runs=160,cells=32,paired_comparisons=36,markdown_effect_rows=36,
        source_sha256=sha(p),report_sha256=sha(report),checker_sha256=sha(__file__),
        raw_references=len(records),security_proof=False,latency_claim=False)
    save(PACKAGE/'results/free_sensitivity_tables_audit.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
