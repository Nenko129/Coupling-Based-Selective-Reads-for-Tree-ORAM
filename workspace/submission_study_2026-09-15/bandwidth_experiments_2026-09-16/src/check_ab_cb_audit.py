"""Reject damaged AB artifacts, including changes hidden by aggregate totals."""
from common import *
import copy
from audit_ab_cb import inputs,audit_record,matched


def reject(call):
    try:call()
    except (AssertionError,KeyError,ValueError):return
    raise AssertionError('damaged receipt accepted')


def main():
    plan,kwargs=inputs();rows=[]
    for s in plan['specs']:
        r=json.loads((PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json").read_text())
        assert audit_record(r,s,**kwargs);rows.append(r)
    r=next(r for r in rows if r['spec']['kind']=='r0' and r['spec']['bottom_dummy']==0);s=r['spec'];labels=[]
    edits=[('answer',lambda x:x.__setitem__('answer_sha256','0'*64)),
        ('source',lambda x:x['source_hashes'].clear()),
        ('proof',lambda x:x.__setitem__('frontend_proof_sha256','0'*64)),
        ('full_native_claim',lambda x:x.__setitem__('native_full_paper_reproduction',True)),
        ('unsupported_capacity',lambda x:x.__setitem__('capacity_certificate',True)),
        ('deadq_claim',lambda x:x.__setitem__('deadq_implemented',True)),
        ('geometry',lambda x:x['configs'][0].__setitem__('L',9)),
        ('background_under_count',lambda x:x['phases']['warmup']['frontend_metrics'].__setitem__('background_slots',0)),
        ('histogram',lambda x:x['phases']['measurement']['boundary_stash_histogram'].clear()),
        ('global_clock',lambda x:x['final_clock'].__setitem__('t',1)),
        ('useful_slots',lambda x:x['phases']['measurement']['useful_schedule'].__setitem__('slots',1)),
        ('uncompleted_requests',lambda x:x['phases']['measurement']['frontend_metrics'].__setitem__('application_completed',1)),
        ('unchecked_requests',lambda x:x.__setitem__('correctness_checked_requests',0)),
        ('extra_green',lambda x:x['phases']['warmup']['frontend_metrics'].__setitem__('background_green_promotions',10**9)),
        ('rpc_sequence',lambda x:x['phases']['measurement']['bills'][0].__setitem__('first_sequence',0)),
        ('cache_payload',lambda x:x['cache_representation'].__setitem__('bytes',13972)),
        ('server_bucket_count',lambda x:x['server_storage'].__setitem__('physical_bucket_records',1))]
    for label,edit in edits:
        x=copy.deepcopy(r);edit(x);reject(lambda:audit_record(x,s,**kwargs));labels.append(label)
    x=copy.deepcopy(r);part=x['phases']['measurement']['bills'][0]['by_stage']['logical']
    part['data_download']-=1;part['headers_download']+=1
    reject(lambda:audit_record(x,s,**kwargs));labels.append('misattributed_component_same_total')
    a=next(a for a in rows if a['spec']['kind']=='ring' and a['spec']['bottom_dummy']==0);matched(a,r,'backend')
    for label,edit in [('pair_seed',lambda x:x['spec'].__setitem__('trace_seed',999)),
        ('pair_useful_schedule',lambda x:x['phases']['warmup']['useful_schedule'].__setitem__('remove_admit_sha256','0'*64)),
        ('pair_dirty_endpoint',lambda x:x['phases']['measurement']['frontend_metrics'].__setitem__('dirty_resident',0))]:
        x=copy.deepcopy(r);edit(x);reject(lambda:matched(a,x,'backend'));labels.append(label)
    save(PACKAGE/'results/ab_cb_audit_checks.json',dict(status='passed',valid_runs=len(rows),rejected=labels,
        auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py'),checker_sha256=sha(__file__),source_hashes=kwargs['source']))
    print(json.dumps(dict(status='passed',valid_runs=len(rows),negative_checks=len(labels))))


if __name__=='__main__':main()
