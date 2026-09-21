"""Independent byte/resource/answer checks and logical schedule cross-check."""
from common import *
from functools import lru_cache
from run_ir_guarded_periodic import identity,evidence
from analyze_ir_dwb import bill,expected_answers
from audit_ir_compressed import audit_reset
from freeze_ir_compressed_completed import resource
from ir_reset_window_replay import replay,nonzero


@lru_cache(None)
def logical(spec_json):return replay(json.loads(spec_json),tail_periods=1)


def answer_lists(r):
    s=r['spec'];trace=json.loads((PACKAGE/r['trace']['path']).read_text())
    truth={a:a.to_bytes(8,'big')+bytes(s['B']-8) for a in range(s['N'])};values=[]
    for a,v in trace['rows']:
        values.append(truth[a])
        if v is not None:truth[a]=hashlib.shake_256(b'SOC3-EVAL-PAYLOAD-v1'+a.to_bytes(8,'big')+v.to_bytes(8,'big')).digest(s['B'])
    return {'warmup':values[:s['warmup']],'measurement':values[s['warmup']:]}


def audit_record(r,s):
    assert r['status']=='passed' and r['spec']==s and r['source_hashes']==identity() and r['proof_hashes']==evidence()
    assert not any(r[k] for k in ('original_75_outcomes_replaced','native_full_paper_reproduction','adaptive_security_proof','latency_claim','true_client_peak_measured'))
    assert s['kind'] in ('path','deferred','sde') and s['map_mode']=='compressed' and s['tail_periods']==1
    assert s['arrival_gap']==s['slots_per_request']==8 and s['warmup']*8==s['period_slots'] and s['requests']*8==4*s['period_slots']
    assert r['correctness_checked_requests']==s['warmup']+s['requests']
    assert r['answer_sha256']==expected_answers(r['trace']['path'],r['trace']['sha256'],s['N'],s['B'],
        s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    counts=[s['N']]
    while counts[-1]>1:counts.append((counts[-1]+s['X']-1)//s['X'])
    L=1;population=sum(counts)
    while 3*2**L<2*population:L+=1
    assert r['map_counts']==counts and s['period_slots']==s['profile'][1]*2**L
    c,=r['configs'];assert c==dict(kind=s['kind'],L=L,N=population,B=s['B'],Z=s['profile'][0],A=s['profile'][1],
        S=s['profile'][2],R=s['R'],tree=0,compact=True,fused=True,Z_by_depth=s['Z_by_depth'],S_by_depth=[])
    assert r['periodic_extension']==dict(period_slots=s['period_slots'],warmup_complete_periods=2,measurement_complete_periods=5,
        public_tail_periods_per_phase=1,no_steady_state_claim=True,path_uses_reference_window=s['kind']=='path')
    bill(r['setup']);assert r['setup']['first_sequence']==0
    align=r['alignment'];bill(align['bill']);pad=(-population)%s['period_slots']
    assert align['public_slots']==align['schedule']['slots']==pad and align['start_t']==population and align['end_t']==population+pad
    assert align['bill']['first_sequence']==r['setup']['next_sequence'];last=align['bill']['next_sequence'];clock=pad
    canonical=dict(s,kind='path',id='logical',experiment_class='model');model=logical(json.dumps(canonical,sort_keys=True))
    assert model['trace']==r['trace'];answers=answer_lists(r);previous_reset=None
    for phase,Q in [('warmup',s['warmup']),('measurement',s['requests'])]:
        p=r['phases'][phase];x=next(x for x in model['phases'] if x['phase']==phase);W=Q*8;G=s['period_slots'];total=W+G
        assert p['requests']==p['completed']==Q and p['public_slots']==total and p['active_arrival_window_slots']==W and p['guard_slots']==G
        assert p['start_clock']==clock and p['end_clock']==clock+total
        assert p['start_t']==population+clock and p['end_t']==population+clock+total
        assert p['start_t']%G==p['end_t']%G==0;clock+=total
        b,=p['bills'];bill(b);assert b['first_sequence']==last;last=b['next_sequence']
        assert p['total_bytes']==b['total_bytes'] and p['rpc']==b['rpc'] and p['bytes_per_public_slot']==b['total_bytes']/total
        assert p['schedules']==[x['schedule']] and p['schedules'][0]['slots']==total
        for k in ('frontend_metrics','map_metrics'):assert nonzero(p[k])==nonzero(x[k]),(phase,k)
        for k in ('reset_start','reset_end','clearance_slot','tail_slots_to_clear'):assert p[k]==x[k],(phase,k)
        assert p['reset_start']==previous_reset;previous_reset=p['reset_end']
        for reset in (p['reset_start'],p['reset_end']):audit_reset(reset,counts,s['X'])
        m=p['frontend_metrics'];fm=p['map_metrics']
        assert m['public_slots']==total and m['application_completed']==Q and m['unfinished_foreground']==0
        assert m['group_reset_slots']==sum(m.get(k,0) for k in ('foreground_group_reset_slots','dwb_group_reset_slots','maintenance_reset_slots'))==fm.get('group_backend_slots',0)
        assert total==sum(m.get(k,0) for k in ('foreground_slots','dwb_posmap_slots','dwb_data_slots','dwb_group_reset_slots','maintenance_reset_slots','dummy_slots'))
        assert fm.get('group_resets',0)-fm.get('group_resets_completed',0)==int(p['reset_end'] is not None)-int(p['reset_start'] is not None)
        cut=p['original_cut'];expected_cut=x['original_cut'];bill(cut['bill'])
        assert cut['public_slots']==W and cut['bill']['first_sequence']==b['first_sequence'] and cut['bill']['next_sequence']<=b['next_sequence']
        for k in ('completed','queued','foreground','reset','schedule'):assert cut[k]==expected_cut[k],(phase,k)
        assert cut['answer_sha256']==hashlib.sha256(b''.join(answers[phase][:cut['completed']])).hexdigest()
        assert p['answer_sha256']==hashlib.sha256(b''.join(answers[phase])).hexdigest()
        assert p['guard_bytes']==b['total_bytes']-cut['bill']['total_bytes']>0
        assert p['guard_rpc']==b['rpc']-cut['bill']['rpc']>0
        assert all(b['components'][k]>=v for k,v in cut['bill']['components'].items())
    m=r['phases']['measurement'];assert r['bytes_per_request']==m['total_bytes']/s['requests']
    assert r['rpc_per_request']==m['rpc']/s['requests'] and r['bytes_per_public_slot']==m['bytes_per_public_slot']
    assert r['final_clock']['t']==population+clock
    assert r['final_clock']['g']==(r['final_clock']['t'] if s['kind']=='path' else r['final_clock']['t']//s['profile'][1])
    mem=r['frontend_memory_representation'];assert mem['llc_payload_capacity']==s['llc_sets']*s['llc_ways']*s['B']
    assert mem['plb']==dict(plb_payload_bytes=s['plb']*s['B'],plb_leaf_and_address_bytes=s['plb']*12,terminal_leaf_bytes=4*counts[-1],
        stash_reserved_bytes=s['R']*s['B'],full_private_posmap_present=False,measured_peak=False,reset_descriptors_max=1,
        reset_scalar_fields=5,reset_additional_payload_bytes=0,reset_parent_payload_in_plb=True)
    return dict(status='passed',resource=resource(r),complete_requests=s['warmup']+s['requests'],
        measurement_guard_bytes=m['guard_bytes'],measurement_reset_slots=m['frontend_metrics']['group_reset_slots'],
        logical_schedule_matched=True,original_75_unchanged=True,security_admission=False)


def tool_hashes():
    return {n:sha(Path(__file__).parent/n) for n in ('audit_ir_guarded_periodic.py','ir_reset_window_replay.py',
        'freeze_ir_compressed_completed.py','analyze_ir_dwb.py','audit_ir_compressed.py','audit_frontend_batches.py')}
