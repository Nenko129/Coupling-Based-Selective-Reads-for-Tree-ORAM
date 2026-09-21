"""Audit AB-CB integration artifacts without claiming native security closure."""
from common import *
import argparse
from run_ab_cb import identity
from analyze_ir_dwb import expected_answers,bill


def inputs(plan_name='pilot_ab_cb_plan.json'):
    planpath=PACKAGE/plan_name;plan=json.loads(planpath.read_text())
    periodic=bool(plan.get('periodic',False))
    paced=bool(plan.get('paced_initialization',False))
    if paced:
        assert periodic
        from run_ab_paced_periodic import identity as bound_identity
    elif periodic:
        from run_ab_periodic import identity as bound_identity
    else:bound_identity=identity
    assert plan['source_hashes']==bound_identity()
    p=PACKAGE/'results/ab_cb_frontend_checks.json';proof=json.loads(p.read_text())
    assert proof['status']=='passed' and proof['source_hashes']==plan['source_hashes']['runtime']
    manifest=json.loads((COMPOSITION.parent/'MANIFEST.sha256.json').read_text());files=manifest.get('files',manifest)
    for name in ('frontends.py','transfer_backend.py'):assert sha(COMPOSITION/name)==files['src/'+name]
    return plan,dict(source=plan['source_hashes'],proof_hash=sha(p),periodic=periodic,paced=paced)


def audit_record(r,s,source,proof_hash,periodic=False,paced=False):
    assert r['status']=='passed' and r['spec']==s and r['source_hashes']==source
    assert r['frontend_proof_sha256']==proof_hash
    for key in ('native_full_paper_reproduction','deadq_implemented','capacity_certificate','adaptive_security_proof','latency_claim','true_client_peak_measured'):
        assert r[key] is False
    assert r['correctness_checked_requests']==s['warmup']+s['requests']
    assert r['answer_sha256']==expected_answers(r['trace']['path'],r['trace']['sha256'],s['N'],s['B'],
        s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    population=n=s['N']
    while n>1:n=(n+s['X']-1)//s['X'];population+=n
    c,=r['configs'];z,a,tau=s['profile'];y=s['Y']
    sd=[] if s['bottom_dummy'] is None else [tau if d<s['L']-2 else s['bottom_dummy']+y for d in range(s['L']+1)]
    assert c==dict(kind=s['kind'],L=s['L'],N=population,B=s['B'],Z=z,A=a,S=tau,Y=y,R=s['R'],tree=0,
        compact=True,fused=True,Z_by_depth=[],S_by_depth=sd,Y_by_depth=[])
    assert r['population_including_maps']==population and r['leaf_load']==population/2**s['L']
    assert population<=a*2**(s['L']-1)  # Declared geometric load, not a CB tail proof.
    assert (s['pressure_high'] is None)==(s['pressure_low'] is None)
    if s['pressure_high'] is not None:assert 0<=s['pressure_low']<s['pressure_high']<s['R']
    initial_clock=population
    if paced:
        assert periodic and s['initialization_stride']==a
        initial_clock=population*a;init=r['initialization']
        assert (init['stride'],init['initial_clock'],init['admitted_records'])==(a,initial_clock,population)
        full=hashlib.sha256();useful=hashlib.sha256()
        for address in range(population):
            value=json.dumps([None,address],separators=(',',':')).encode()+b'\n';full.update(value);useful.update(value)
            for _ in range(a-1):full.update(b'[null,null]\n')
        assert init['schedule']==dict(slots=initial_clock,remove_admit_sha256=full.hexdigest())
        assert init['useful_schedule']==dict(slots=population,remove_admit_sha256=useful.hexdigest())
    bill(r['setup']);lastseq=r['setup']['next_sequence'];clock=0;largest=0
    if periodic:
        period=a*2**s['L'];alignment=r['alignment'];bill(alignment['bill'])
        assert s['period_slots']==period and s['warmup']*s['slots_per_request']==period and s['requests']*s['slots_per_request']==4*period
        assert (alignment['public_slots'],alignment['start_t'],alignment['end_t'])==((-initial_clock)%period,initial_clock,initial_clock+(-initial_clock)%period)
        assert alignment['schedule']['slots']==alignment['public_slots'] and alignment['bill']['first_sequence']==lastseq
        assert r['periodic_extension']==dict(period_slots=period,warmup_complete_periods=1,measurement_complete_periods=4,no_steady_state_claim=True)
        hist={int(k):v for k,v in alignment['boundary_stash_histogram'].items()}
        assert sum(hist.values())==alignment['public_slots'] and all(0<=k<=s['R'] and v>0 for k,v in hist.items())
        largest=max(hist,default=0);clock=alignment['public_slots'];lastseq=alignment['bill']['next_sequence']
    for phase,Q in [('warmup',s['warmup']),('measurement',s['requests'])]:
        p=r['phases'][phase];W=Q*s['slots_per_request'];m=p['frontend_metrics']
        assert p['requests']==Q and p['public_slots']==W and (p['start_clock'],p['end_clock'])==(clock,clock+W)
        if periodic:assert (initial_clock+clock)%period==0 and (initial_clock+clock+W)%period==0
        clock+=W;b,=p['bills'];bill(b)
        assert b['first_sequence']==lastseq;lastseq=b['next_sequence']
        assert (p['total_bytes'],p['rpc'])==(b['total_bytes'],b['rpc'])
        schedule,=p['schedules'];assert schedule['slots']==W and len(schedule['remove_admit_sha256'])==64
        useful=p['useful_schedule'];assert useful['slots']==m.get('foreground_slots',0) and len(useful['remove_admit_sha256'])==64
        assert all(isinstance(v,(int,bool)) and v>=0 for v in m.values())
        assert m['public_slots']==W and m['application_completed']==Q and m['unfinished_foreground']==0 and not m['dwb_pending']
        assert not any(v for k,v in m.items() if k.startswith('dwb_'))
        assert m.get('llc_hits',0)+m.get('llc_misses',0)==Q
        assert m.get('foreground_slots',0)==m.get('foreground_data_slots',0)+m.get('foreground_posmap_slots',0)
        assert m.get('foreground_data_slots',0)==m.get('llc_misses',0)+m.get('foreground_writebacks',0)
        assert W==sum(m.get(k,0) for k in ('foreground_slots','dummy_slots','background_slots'))
        assert 0<=m['dirty_resident']<=s['llc_sets']*s['llc_ways']
        assert all(isinstance(v,int) and v>=0 for v in p['cb_metrics'].values())
        assert m.get('background_green_promotions',0)<=p['cb_metrics'].get('green_promotions',0)
        if s['pressure_high'] is None:assert not any(v for k,v in m.items() if k.startswith('background_'))
        hist={int(k):v for k,v in p['boundary_stash_histogram'].items()}
        assert hist and all(0<=k<=s['R'] and isinstance(v,int) and v>0 for k,v in hist.items()) and sum(hist.values())==W
        largest=max(largest,max(hist))
    m=r['phases']['measurement'];assert r['bytes_per_request']==m['total_bytes']/s['requests']
    assert r['bytes_per_public_slot']==m['total_bytes']/m['public_slots'] and r['rpc_per_request']==m['rpc']/s['requests']
    assert r['final_clock']['t']==initial_clock+clock and r['final_clock']['g']==(initial_clock+clock)//a
    assert 0<=r['setup_peak_boundary_stash']<=r['max_boundary_stash']<=s['R'] and largest<=r['max_boundary_stash']
    storage=r['server_storage'];assert storage['total_bytes']==sum(storage['components'].values())
    assert storage['physical_bucket_records']==2**(s['L']+1)-2**s['cached_levels']
    cache=r['cache_representation'];assert cache['bucket_records']==cache['global_tag_records']==2**s['cached_levels']-1
    # Reconstruct physical object sizes independently, including the empty
    # root's two retained tags and the unpadded local authentication tree.
    expected_remote={k:0 for k in ('headers','ciphertext_slots','local_authentication','bucket_tags','global_tags')};expected_cache=0
    for d in range(s['L']+1):
        nslots=z+(sd[d] if sd else tau)-y;leaves=1<<(nslots-1).bit_length();nodes=set()
        for j in range(nslots):
            node=leaves+j
            while node:nodes.add(node);node//=2
        parts=dict(headers=76+((16+30*z+31)//32)*32,ciphertext_slots=nslots*(s['B']+16),
            local_authentication=64*len(nodes),bucket_tags=64,global_tags=64)
        if d==0 and s['kind']=='r0':parts.update(headers=0,ciphertext_slots=0,local_authentication=0)
        if d<s['cached_levels']:expected_cache+=2**d*sum(parts.values())
        else:
            for key,value in parts.items():expected_remote[key]+=2**d*value
    assert storage['components']==expected_remote and cache['bytes']==expected_cache
    mem=r['frontend_memory_representation'];assert mem['llc_payload_capacity']==s['llc_sets']*s['llc_ways']*s['B']
    assert mem['plb']['plb_payload_bytes']==s['plb']*s['B'] and mem['logical_metadata_not_peak']
    return True


def matched(a,b,axis):
    fields={'backend':{'kind'},'layout':{'bottom_dummy'},'pressure':{'pressure_high','pressure_low'}}[axis]|{'id','experiment_class'}
    assert {k:v for k,v in a['spec'].items() if k not in fields}=={k:v for k,v in b['spec'].items() if k not in fields}
    assert a['trace']==b['trace'] and a['answer_sha256']==b['answer_sha256'] and a['source_hashes']==b['source_hashes']
    for phase in ('warmup','measurement'):
        x,y=a['phases'][phase],b['phases'][phase]
        assert (x['requests'],x['public_slots'],x['start_clock'],x['end_clock'])==(y['requests'],y['public_slots'],y['start_clock'],y['end_clock'])
        assert x['useful_schedule']==y['useful_schedule']
        # Extra dummy/background slots can move useful transfers in time.
        # Do not require equality of the padded global schedule.
        def useful(m):return {k:v for k,v in m.items() if k.startswith(('foreground_','llc_')) or k in ('application_completed','unfinished_foreground','dirty_resident')}
        assert useful(x['frontend_metrics'])==useful(y['frontend_metrics'])
    assert all(a['cache_representation'][k]==b['cache_representation'][k] for k in ('bucket_records','global_tag_records'))
    assert a['frontend_memory_representation']==b['frontend_memory_representation']
    return True


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',default='pilot_ab_cb_plan.json');args=parser.parse_args()
    plan,kwargs=inputs(args.plan);rows=[];receipts=[];missing=[]
    for s in plan['specs']:
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        if not p.exists():missing.append(s['id']);continue
        r=json.loads(p.read_text());audit_record(r,s,**kwargs);rows.append(r)
        receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    pairs=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            different={k for k in a['spec'] if k not in ('id','experiment_class') and a['spec'][k]!=b['spec'][k]}
            for axis,fields in [('backend',{'kind'}),('layout',{'bottom_dummy'}),('pressure',{'pressure_high','pressure_low'})]:
                if different and different<=fields:
                    matched(a,b,axis);pairs.append(dict(axis=axis,before=a['spec']['id'],after=b['spec']['id'],
                        saving_pct=100*(1-b['bytes_per_request']/a['bytes_per_request'])))
    name=Path(args.plan).stem.replace('_plan','')
    save(PACKAGE/'results'/f'{name}_audit.json',dict(status='complete_receipts_audited' if not missing else 'partial_receipts_audited',
        expected=len(plan['specs']),completed=len(rows),missing=missing,receipts=receipts,pairs=pairs,
        source_hashes=kwargs['source'],plan_sha256=sha(PACKAGE/args.plan),checker_sha256=sha(__file__),
        numerical_or_security_admission=False,formal_performance_estimate=False))
    print(json.dumps(dict(plan=args.plan,completed=len(rows),expected=len(plan['specs']),matched_pairs=len(pairs))))


if __name__=='__main__':main()
