"""Actual small-domain driver, invoice and hostile receipt checks."""
from common import *
import copy
from run_ir_compressed_periodic import run,identity
from audit_ir_compressed import audit_record,inputs,matched

def main():
    source=identity();kw=inputs();rows=[]
    base=dict(id='',kind='sde',N=64,B=64,X=8,beta=2,map_mode='compressed',profile=[4,3,3],R=480,cached_levels=2,
        Z_by_depth=[4,4,2,2,3,4,4],plb=3,llc_sets=4,llc_ways=2,layout='depth',dwb=True,warmup=24,requests=96,
        arrival_gap=4,slots_per_request=8,trace_seed=1981,oram_seed=2981,workload='uniform',
        experiment_class='pilot_ir_compressed_periodic',period_slots=192,cohort='small_pipeline_check')
    for enabled in (False,True):
        for kind in ('path','deferred','sde'):
            s=dict(base,id=f'IRCMcheck_{kind}_dwb{int(enabled)}',kind=kind,dwb=enabled)
            p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
            if not p.exists():run(s)
            r=json.loads(p.read_text())
            audit_record(r,s,**kw)
            assert r['phases']['measurement']['frontend_metrics']['group_reset_slots']>0
            rows.append(r)
    for enabled in (False,True):
        group=[r for r in rows if r['spec']['dwb']==enabled]
        for r in group[1:]:matched(group[0],r,'backend')
    for kind in ('path','deferred','sde'):
        a,b=[r for r in rows if r['spec']['kind']==kind];matched(a,b,'dwb')
    base_row=rows[-1];neg=[]
    mutations=[
        ('answer_digest',lambda r:r.__setitem__('answer_sha256','0'*64)),
        ('missing_alignment_charge',lambda r:r['alignment']['bill'].__setitem__('total_bytes',0)),
        ('misaligned_phase',lambda r:r['phases']['measurement'].__setitem__('start_t',1)),
        ('short_window',lambda r:r['phases']['measurement'].__setitem__('end_clock',1)),
        ('map_population',lambda r:r['configs'][0].__setitem__('N',r['configs'][0]['N']-1)),
        ('reset_transfer_omitted',lambda r:r['phases']['measurement']['map_metrics'].__setitem__('group_backend_slots',0)),
        ('reset_conservation',lambda r:r['phases']['measurement']['map_metrics'].__setitem__('group_resets_completed',9999)),
        ('pending_reset_flag',lambda r:r['phases']['measurement']['frontend_metrics'].__setitem__('group_reset_pending',not r['phases']['measurement']['frontend_metrics']['group_reset_pending'])),
        ('hidden_descriptor_budget',lambda r:r['frontend_memory_representation']['plb'].__setitem__('reset_descriptors_max',0)),
        ('proof_chain',lambda r:r['proof_hashes'].__setitem__('ir_compressed_stage_checks.json','0'*64)),
        ('RPC_sequence',lambda r:r['phases']['measurement']['bills'][0].__setitem__('first_sequence',0)),
        ('false_security_closure',lambda r:r['capacity_model_binding'].__setitem__('protocol_closure',True)),
    ]
    for label,edit in mutations:
        r=copy.deepcopy(base_row);edit(r)
        try:audit_record(r,base_row['spec'],**kw)
        except AssertionError:neg.append(label)
        else:raise AssertionError('damaged receipt accepted: '+label)
    # Keep a deliberately overloaded window as a failure receipt: no hidden
    # drain, automatic retry or false bytes/completed-request performance row.
    s=dict(base,id='IRCMcheck_expected_short_horizon',warmup=192,requests=768,slots_per_request=1,arrival_gap=1,beta=1)
    try:run(s)
    except AssertionError as e:assert 'fixed horizon' in str(e)
    else:raise AssertionError('overloaded fixed window unexpectedly succeeded')
    fail=PACKAGE/'results/failures'/f"{s['id']}.json";failure=json.loads(fail.read_text())
    assert failure['phase']=='warmup' and failure['clock']-failure['context']['phase_start_clock']==192
    assert failure['completed_this_phase']<192 and failure['partial_bill']['total_bytes']>0
    assert not (PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json").exists()
    assert source==identity() and kw==inputs()
    save(PACKAGE/'results/ir_compressed_runner_checks.json',dict(status='passed',source_hashes=source,
        proof_hashes=kw['proofs'],checker_sha256=sha(__file__),auditor_sha256=sha(Path(__file__).with_name('audit_ir_compressed.py')),
        cases=[dict(id=r['spec']['id'],path=f"results/{r['spec']['experiment_class']}/{r['spec']['id']}.json",
            sha256=sha(PACKAGE/'results'/r['spec']['experiment_class']/f"{r['spec']['id']}.json")) for r in rows],
        rejected_receipts=neg,expected_failure=dict(path=str(fail.relative_to(PACKAGE)),sha256=sha(fail)),
        scope='small-domain driver and independent artifact audit; no native IR security or target-scale performance claim'))
    print(json.dumps(dict(status='passed',cases=len(rows),rejected=len(neg),expected_horizon_failure=True)),flush=True)

if __name__=='__main__':main()
