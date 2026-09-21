"""Negative evidence checks for the integrated fixed-horizon IR audit."""
from common import *
import copy
from analyze_ir_dwb import inputs,audit_record,matched,pair_group


def rejected(fn):
    try:fn()
    except (AssertionError,KeyError):return
    raise AssertionError('corrupted evidence accepted')


def main():
    plan,kwargs=inputs()
    def load(layout,kind,dwb):
        sid=f'IRDWB_{layout}_{kind}_dwb{int(dwb)}_uniform_seed101'
        s=next(s for s in plan['specs'] if s['id']==sid)
        r=json.loads((PACKAGE/'results/formal_ir_dwb'/f'{sid}.json').read_text())
        assert audit_record(r,s,**kwargs)
        return r
    r=load('depth','sde',True);s=r['spec'];labels=[]
    edits=[('answer_digest',lambda x:x.__setitem__('answer_sha256','0'*64)),
        ('wrong_source',lambda x:x['source_hashes'].clear()),
        ('wrong_controller_proof',lambda x:x.__setitem__('controller_proof_sha256','0'*64)),
        ('unchecked_requests',lambda x:x.__setitem__('correctness_checked_requests',1)),
        ('wrong_population',lambda x:x['configs'][0].__setitem__('N',4096)),
        ('false_security_closure',lambda x:x['capacity_model_binding'].__setitem__('protocol_closure',True)),
        ('unearned_latency_claim',lambda x:x.__setitem__('latency_claim',True)),
        ('rpc_sequence_gap',lambda x:x['phases']['measurement']['bills'][0].__setitem__('first_sequence',0)),
        ('time_horizon',lambda x:x['phases']['measurement'].__setitem__('public_slots',2047)),
        ('schedule_slot_count',lambda x:x['phases']['measurement']['schedules'][0].__setitem__('slots',2047)),
        ('dummy_under_count',lambda x:x['phases']['measurement']['frontend_metrics'].__setitem__('dummy_slots',1)),
        ('foreground_under_count',lambda x:x['phases']['measurement']['frontend_metrics'].__setitem__('foreground_data_slots',1)),
        ('unfinished_request',lambda x:x['phases']['measurement']['frontend_metrics'].__setitem__('unfinished_foreground',1)),
        ('storage_excludes_bucket',lambda x:x['server_storage'].__setitem__('physical_bucket_records',1)),
        ('wrong_cache_budget',lambda x:x['frontend_memory_representation'].__setitem__('llc_payload_capacity',1))]
    for label,edit in edits:
        x=copy.deepcopy(r);edit(x);rejected(lambda:audit_record(x,s,**kwargs));labels.append(label)
    # Preserve both aggregate sums but misattribute one component to a stage.
    x=copy.deepcopy(r);part=x['phases']['measurement']['bills'][0]['by_stage']['logical']
    part['data_download']-=1;part['headers_download']+=1
    rejected(lambda:audit_record(x,s,**kwargs));labels.append('component_shift_with_total_unchanged')
    a=load('depth','deferred',True);matched(a,r,'backend')
    for label,edit in [('pair_seed',lambda x:x['spec'].__setitem__('trace_seed',999)),
                       ('pair_schedule',lambda x:x['phases']['measurement']['schedules'][0].__setitem__('remove_admit_sha256','0'*64)),
                       ('pair_dirty_endpoint',lambda x:x['phases']['measurement']['frontend_metrics'].__setitem__('dirty_resident',0))]:
        x=copy.deepcopy(r);edit(x);rejected(lambda:matched(a,x,'backend'));labels.append(label)
    off=load('depth','deferred',False);matched(off,a,'dwb')
    assert pair_group([off,a],'dwb',False,True)['effect']['mean']==0
    assert pair_group([off,a],'dwb',False,True)['effect']['ci95'] is None
    x=copy.deepcopy(a);x['phases']['measurement']['total_bytes']-=1
    rejected(lambda:matched(off,x,'dwb'));labels.append('invented_dwb_byte_saving_on_full_paths')
    save(PACKAGE/'results/ir_dwb_analysis_checks.json',dict(status='passed',rejected=labels,
        valid_backend_pair=True,valid_dwb_pair_with_different_work=True,partial_no_ci=True,
        analyzer_sha256=sha(Path(__file__).parent/'analyze_ir_dwb.py'),checker_sha256=sha(__file__)))
    print(json.dumps(dict(status='passed',negative_checks=len(labels))))


if __name__=='__main__':main()
