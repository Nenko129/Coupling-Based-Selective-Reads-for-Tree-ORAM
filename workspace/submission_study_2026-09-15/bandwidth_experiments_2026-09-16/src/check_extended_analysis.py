"""Reject bad accounting and unpaired input before presenting effect sizes."""
from common import *
import copy
from analyze_extended_results import audit_record,matched,paired_row

def rejected(fn):
    try:fn()
    except (AssertionError,KeyError):return True
    raise AssertionError('bad evidence was accepted')

def main():
    p=PACKAGE/'results/formal_calibration/CAL_path_43_seed101.json';r=json.loads(p.read_text());s=r['spec']
    assert audit_record(r,s,'core')
    bad=[]
    for label,edit in [('direction_total',lambda x:x['phases']['measurement'].__setitem__('response_bytes',1)),
                        ('stage_total',lambda x:x['phases']['measurement']['by_stage'].clear()),
                        ('rpc_sequence',lambda x:x['phases']['measurement'].__setitem__('next_sequence',0)),
                        ('wrong_source',lambda x:x['source_hashes'].clear()),
                        ('unchecked_requests',lambda x:x.__setitem__('correctness_checked_requests',0))]:
        x=copy.deepcopy(r);edit(x);assert rejected(lambda:audit_record(x,s,'core'));bad.append(label)
    x=copy.deepcopy(r);x['spec']['trace_seed']+=1;assert rejected(lambda:matched(r,x));bad.append('seed_mismatch')
    x=copy.deepcopy(r);x['answer_sha256']='0'*64;assert rejected(lambda:matched(r,x));bad.append('answer_mismatch')
    public=[]
    for kind in ('deferred','sde'):
        q=PACKAGE/'results/formal_public'/f'PUB_Financial1_free_compressed_{kind}_seed101.json';public.append(json.loads(q.read_text()))
    result=paired_row(public,'deferred','sde',True)
    assert result['effect']['ci95'] is None and result['needs_more_repeats'] is None
    # Tuned dispatch does not include a study field; audit this path using an
    # actual core receipt, with only the matching experimental identity changed.
    core=json.loads((PACKAGE/'results/formal_core/B1_path_uniform_N16384_B4096_seed101.json').read_text())
    core['spec']['experiment_class']='formal_tuned'
    assert audit_record(core,core['spec'],'core')
    save(PACKAGE/'results/extended_analysis_checks.json',dict(status='passed',rejected=bad,public_no_iid_ci=True,tuned_without_study_field=True,
        checker_sha256=sha(__file__),analyzer_sha256=sha(Path(__file__).parent/'analyze_extended_results.py')))
    print(json.dumps(dict(status='passed',negative_checks=len(bad))))

if __name__=='__main__':main()
