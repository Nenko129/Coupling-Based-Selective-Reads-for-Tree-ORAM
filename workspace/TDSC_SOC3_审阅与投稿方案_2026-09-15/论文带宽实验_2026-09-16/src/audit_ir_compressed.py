"""Independent receipts, phase boundaries and compressed-reset conservation."""
from common import *
from run_ir_compressed_periodic import identity,evidence
from analyze_ir_dwb import expected_answers,bill

def inputs():
    cap=PACKAGE/'numerics/IR43_scaled_L12_c480_m128_audit.json';a=json.loads(cap.read_text())
    return dict(source=identity(),proofs=evidence(),capacity_hash=sha(cap),lifetime=next(x['lifetime_log2'] for x in a['tested'] if x['R']==480))

def audit_reset(d,counts,X):
    if d is None:return
    assert set(d)=={'level','parent_i','parent_address','group','cursor'}
    assert all(isinstance(v,int) and v>=0 for v in d.values())
    level=d['level'];assert level<len(counts)-1 and d['parent_i']<counts[level+1]
    assert d['parent_address']==sum(counts[:level+1])+d['parent_i']
    assert 0<d['cursor']<min(X,counts[level]-d['parent_i']*X)
    assert d['group']<(1<<64)-1

def audit_record(r,s,source,proofs,capacity_hash,lifetime):
    assert r['status']=='passed' and r['spec']==s and r['source_hashes']==source and r['proof_hashes']==proofs
    assert s['map_mode']=='compressed' and s['kind'] in ('path','deferred','sde') and 64+s['X']*s['beta']<=8*s['B']
    assert not r['native_full_paper_reproduction'] and not r['latency_claim'] and not r['true_client_peak_measured']
    assert r['correctness_checked_requests']==s['warmup']+s['requests']
    assert r['answer_sha256']==expected_answers(r['trace']['path'],r['trace']['sha256'],s['N'],s['B'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    counts=[s['N']]
    while counts[-1]>1:counts.append((counts[-1]+s['X']-1)//s['X'])
    population=sum(counts);L=1
    while 3*2**L<2*population:L+=1
    assert r['map_counts']==counts
    c,=r['configs'];assert c==dict(kind=s['kind'],L=L,N=population,B=s['B'],Z=s['profile'][0],A=s['profile'][1],
        S=s['profile'][2],R=s['R'],tree=0,compact=True,fused=True,Z_by_depth=s['Z_by_depth'],S_by_depth=[])
    profile=s['Z_by_depth'] or [c['Z']]*(L+1)
    ref=[4,4,4,4,4,4,2,2,2,3,3,4,4]
    model=(L==12 and c['A']==3 and population<=6144 and s['R']>=480 and len(profile)==13 and all(x>=y for x,y in zip(profile,ref)))
    assert r['capacity_model_binding']==dict(matches_profile_and_population=model,population_including_maps=population,
        audit_sha256=capacity_hash,selective_reference_R=480,lifetime_log2=lifetime,protocol_closure=False,baseline_theorem_not_supplied=s['kind']!='sde')
    period=c['A']*2**L
    assert s['period_slots']==period and s['warmup']*s['slots_per_request']==period and s['requests']*s['slots_per_request']==4*period
    assert r['periodic_extension']==dict(period_slots=period,warmup_complete_periods=1,measurement_complete_periods=4,no_steady_state_claim=True,path_uses_reference_window=s['kind']=='path')
    bill(r['setup']);assert r['setup']['first_sequence']==0
    a=r['alignment'];bill(a['bill'])
    assert a['public_slots']==(-population)%period and a['start_t']==population and a['end_t']==population+a['public_slots']
    assert a['end_t']%period==0 and a['schedule']['slots']==a['public_slots']
    assert a['bill']['first_sequence']==r['setup']['next_sequence']
    lastseq=a['bill']['next_sequence'];clock=a['public_slots'];previous_reset=None
    for phase,Q in [('warmup',s['warmup']),('measurement',s['requests'])]:
        p=r['phases'][phase];W=Q*s['slots_per_request'];m=p['frontend_metrics'];fm=p['map_metrics']
        assert p['requests']==Q and p['public_slots']==W and p['start_clock']==clock and p['end_clock']==clock+W
        assert p['start_t']==population+clock and p['end_t']==population+clock+W
        assert p['start_t']%period==0 and p['end_t']%period==0
        clock+=W
        b,=p['bills'];bill(b);assert b['first_sequence']==lastseq;lastseq=b['next_sequence']
        assert p['total_bytes']==b['total_bytes'] and p['rpc']==b['rpc'] and p['bytes_per_public_slot']==b['total_bytes']/W
        schedule,=p['schedules'];assert schedule['slots']==W and len(schedule['remove_admit_sha256'])==64
        assert m['public_slots']==W and m['application_completed']==Q and m['unfinished_foreground']==0
        assert all(isinstance(v,(int,bool)) and v>=0 for v in m.values())
        assert all(isinstance(v,int) and v>=0 for v in fm.values())
        assert m.get('llc_hits',0)+m.get('llc_misses',0)==Q
        assert m.get('foreground_slots',0)==sum(m.get(k,0) for k in ('foreground_data_slots','foreground_posmap_slots','foreground_group_reset_slots'))
        assert m.get('foreground_data_slots',0)==m.get('llc_misses',0)+m.get('foreground_writebacks',0)
        assert m.get('dwb_data_slots',0)==m.get('dwb_completed',0)
        assert W==sum(m.get(k,0) for k in ('foreground_slots','dwb_posmap_slots','dwb_data_slots','dwb_group_reset_slots','maintenance_reset_slots','dummy_slots'))
        assert m['group_reset_slots']==sum(m.get(k,0) for k in ('foreground_group_reset_slots','dwb_group_reset_slots','maintenance_reset_slots'))==fm.get('group_backend_slots',0)
        assert 0<=m['dirty_resident']<=s['llc_sets']*s['llc_ways']
        if not s['dwb']:assert not m['dwb_pending'] and all(not v for k,v in m.items() if k.startswith('dwb_'))
        assert p['reset_start']==previous_reset
        for d in (p['reset_start'],p['reset_end']):audit_reset(d,counts,s['X'])
        assert m['group_reset_pending']==(p['reset_end'] is not None)
        assert fm.get('group_resets',0)-fm.get('group_resets_completed',0)==int(p['reset_end'] is not None)-int(p['reset_start'] is not None)
        previous_reset=p['reset_end']
    p=r['phases']['measurement']
    assert r['bytes_per_request']==p['total_bytes']/s['requests'] and r['rpc_per_request']==p['rpc']/s['requests']
    assert r['bytes_per_public_slot']==p['bytes_per_public_slot'] and r['final_clock']['t']==population+clock
    assert r['final_clock']['g']==r['final_clock']['t']//c['A'] if s['kind']!='path' else r['final_clock']['g']==r['final_clock']['t']
    storage=r['server_storage'];assert storage['total_bytes']==sum(storage['components'].values())
    assert storage['physical_bucket_records']==2**(L+1)-2**s['cached_levels']
    cache=r['cache_representation'];assert cache['bucket_records']==cache['global_tag_records']==2**s['cached_levels']-1
    mem=r['frontend_memory_representation'];assert mem['llc_payload_capacity']==s['llc_sets']*s['llc_ways']*s['B'] and mem['logical_metadata_not_peak']
    assert mem['plb']==dict(plb_payload_bytes=s['plb']*s['B'],plb_leaf_and_address_bytes=s['plb']*12,terminal_leaf_bytes=4*counts[-1],
        stash_reserved_bytes=s['R']*s['B'],full_private_posmap_present=False,measured_peak=False,reset_descriptors_max=1,reset_scalar_fields=5,
        reset_additional_payload_bytes=0,reset_parent_payload_in_plb=True)
    assert r['endpoint_policy']=='dirty LLC and pending private reset may remain; no unbilled draining or durability barrier'
    return True

def matched(a,b,axis):
    allowed={'id'}|{'backend':{'kind'},'dwb':{'dwb'},'beta':{'beta','cohort'}}[axis]
    assert {k:v for k,v in a['spec'].items() if k not in allowed}=={k:v for k,v in b['spec'].items() if k not in allowed}
    assert a['trace']==b['trace'] and a['answer_sha256']==b['answer_sha256']
    for phase in ('warmup','measurement'):
        x,y=a['phases'][phase],b['phases'][phase]
        assert all(x[k]==y[k] for k in ('requests','public_slots','start_t','end_t','start_clock','end_clock'))
        if axis=='backend':
            assert all(x[k]==y[k] for k in ('schedules','frontend_metrics','map_metrics','reset_start','reset_end'))
    assert a['cache_representation']==b['cache_representation'] and a['frontend_memory_representation']==b['frontend_memory_representation']
    if axis in ('dwb','beta') and a['spec']['kind'] in ('path','deferred'):
        assert a['phases']['measurement']['total_bytes']==b['phases']['measurement']['total_bytes']

