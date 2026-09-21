"""Retain all 75 cases; failed stress windows are outcomes, not bandwidth wins."""
from common import *
import time
from resume_fast_batches import alive
from start_ir_compressed_validation import execute,validate_plan
from audit_ir_compressed import inputs,audit_record
from audit_ir_compressed_failure import audit_failure

def main():
    path=PACKAGE/'formal_ir_compressed_plan.json';plan=json.loads(path.read_text());validate_plan(plan)
    ap=PACKAGE/'ir_compressed_observation_amendment.json';amend=json.loads(ap.read_text())
    assert amend['original_plan_sha256']==sha(path)
    for name,value in amend['sources'].items():assert sha(Path(__file__).parent/name)==value
    assert amend['specs_unchanged']==True and amend['expected_observations']==75
    for x,s in zip(amend['pilot_outcomes'],plan['pilots']):
        p=PACKAGE/x['path'];assert sha(p)==x['sha256'];r=json.loads(p.read_text())
        if x['status']=='passed':audit_record(r,s,**inputs())
        else:assert audit_failure(r,s)==x['audit']
    state=PACKAGE/'results/ir_compressed_observation_queue_state.json'
    for dep in plan['dependencies']:
        while alive(dep['pid']):
            save(state,dict(stage='waiting_for_live_raw_IR_batch',pid=os.getpid(),dependency_pid=dep['pid'],time=time.time()));time.sleep(5)
        done=json.loads((PACKAGE/dep['completion']).read_text())
        assert done['status']=='passed' and done['plan_sha256']==sha(PACKAGE/dep['plan'])==plan['comparison_raw_plan_sha256']
    observations=[]
    for s in plan['specs']:
        validate_plan(plan)
        f=PACKAGE/'results/failures'/f"{s['id']}.json"
        try:
            if f.exists():raise RuntimeError('preserved previous outcome; inspect without retry')
            result=execute(s,plan,state,len(observations),len(plan['specs']));result['status']='passed'
        except RuntimeError:
            if s['cohort']!='reset_stress_beta4' or not f.exists():raise
            failure=json.loads(f.read_text());audit=audit_failure(failure,s)
            result=dict(id=s['id'],status='incomplete_horizon',path=str(f.relative_to(PACKAGE)),sha256=sha(f),audit=audit)
        observations.append(result)
        save(PACKAGE/'results/ir_compressed_observations.json',dict(status='in_progress',observations=observations,
             plan_sha256=sha(path),amendment_sha256=sha(ap),expected=75))
        print(json.dumps(result),flush=True)
    incomplete=sum(x['status']!='passed' for x in observations)
    status='completed_with_incomplete_windows' if incomplete else 'passed'
    save(PACKAGE/'results/ir_compressed_observation_completion.json',dict(status=status,observations=observations,expected=75,
        plan_sha256=sha(path),amendment_sha256=sha(ap),incomplete_windows=incomplete))
    save(state,dict(stage=status,pid=os.getpid(),completed=len(observations),incomplete_windows=incomplete,time=time.time()))

if __name__=='__main__':main()

