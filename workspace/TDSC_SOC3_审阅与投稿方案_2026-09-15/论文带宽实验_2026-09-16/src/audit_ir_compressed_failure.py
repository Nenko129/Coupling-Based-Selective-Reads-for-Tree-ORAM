"""Audit fixed-horizon noncompletion separately from usable performance."""
from common import *
from run_ir_compressed_periodic import identity
from audit_ir_compressed import audit_reset
from analyze_ir_dwb import bill

def audit_failure(r,s):
    assert r['status']=='failed' and r['spec']==s and r['source_hashes']==identity()
    assert r['error'].strip().splitlines()[-1]=='AssertionError: fixed horizon did not complete every request'
    assert r['phase'] in ('warmup','measurement')
    counts=[s['N']]
    while counts[-1]>1:counts.append((counts[-1]+s['X']-1)//s['X'])
    population=sum(counts);pad=(-population)%s['period_slots'];phase=r['phase'];Q=s['warmup'] if phase=='warmup' else s['requests']
    start=pad+(0 if phase=='warmup' else s['warmup']*s['slots_per_request']);W=Q*s['slots_per_request']
    prior=0 if phase=='warmup' else s['warmup'];completed=r['completed_this_phase']
    assert r['context']==dict(phase=phase,phase_start_clock=start,phase_start_returned=prior,phase_requests=Q,requested_slots=W)
    assert r['clock']==start+W and r['t']==population+r['clock'] and r['t']%s['period_slots']==0
    assert r['schedule']['slots']==W and len(r['schedule']['remove_admit_sha256'])==64
    bill(r['partial_bill']);assert r['partial_bill']['total_bytes']>0
    assert 0<=completed<Q and completed+int(r['foreground_pending'])+r['queued_requests']==Q
    m=r['controller_metrics'];assert m['public_slots']==r['clock'] and m['application_completed']==prior+completed
    assert m.get('foreground_slots',0)==sum(m.get(k,0) for k in ('foreground_data_slots','foreground_posmap_slots','foreground_group_reset_slots'))
    assert r['clock']==sum(m.get(k,0) for k in ('foreground_slots','dwb_posmap_slots','dwb_data_slots','dwb_group_reset_slots','maintenance_reset_slots','dummy_slots'))
    resets=sum(m.get(k,0) for k in ('foreground_group_reset_slots','dwb_group_reset_slots','maintenance_reset_slots'))
    assert resets==r['map_metrics'].get('group_backend_slots',0)
    audit_reset(r['reset'],counts,s['X'])
    assert r['map_metrics'].get('group_resets',0)-r['map_metrics'].get('group_resets_completed',0)==int(r['reset'] is not None)
    return dict(status='incomplete_horizon',phase=phase,offered_requests=Q,completed_requests=completed,public_slots=W,
        total_bytes=r['partial_bill']['total_bytes'],bytes_per_public_slot=r['partial_bill']['total_bytes']/W,
        eligible_for_completed_request_bandwidth_comparison=False,partial_answer_digest_available=False)

