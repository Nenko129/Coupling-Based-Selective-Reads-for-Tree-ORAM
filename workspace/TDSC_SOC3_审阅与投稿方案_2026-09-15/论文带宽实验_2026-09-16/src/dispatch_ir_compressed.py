"""One guarded worker for the predeclared compressed-map IR matrix."""
from common import *
import argparse,time
from resume_fast_batches import alive
from start_ir_compressed_validation import execute,validate_plan
from audit_ir_compressed import audit_record,inputs

def main():
    p=argparse.ArgumentParser();p.add_argument('--validation-pid',type=int,required=True);args=p.parse_args()
    path=PACKAGE/'formal_ir_compressed_plan.json';plan=json.loads(path.read_text());validate_plan(plan)
    state=PACKAGE/'results/ir_compressed_queue_state.json'
    while alive(args.validation_pid):
        save(state,dict(stage='waiting_for_live_target_validation',pid=os.getpid(),dependency_pid=args.validation_pid,time=time.time()));time.sleep(5)
    proofpath=PACKAGE/'results/ir_compressed_target_checks.json';proof=json.loads(proofpath.read_text())
    assert proof['status']=='passed' and proof['plan_sha256']==sha(path) and proof['source_hashes']==plan['source_hashes']
    assert len(proof['cases'])==2 and proof['runner_checks_sha256']==plan['runner_checks_sha256']
    assert proof['validator_sha256']==plan['execution_tools']['start_ir_compressed_validation.py']
    for x,s in zip(proof['cases'],plan['pilots']):
        f=PACKAGE/x['path'];assert sha(f)==x['sha256'];audit_record(json.loads(f.read_text()),s,**inputs())
    for dep in plan['dependencies']:
        while alive(dep['pid']):
            save(state,dict(stage='waiting_for_live_raw_IR_batch',pid=os.getpid(),dependency_pid=dep['pid'],time=time.time()));time.sleep(5)
        done=json.loads((PACKAGE/dep['completion']).read_text())
        assert done['status']=='passed' and done['plan_sha256']==sha(PACKAGE/dep['plan'])==plan['comparison_raw_plan_sha256']
    rows=[]
    for s in plan['specs']:
        row=execute(s,plan,state,len(rows),len(plan['specs']));rows.append(row);print(json.dumps(row),flush=True)
    validate_plan(plan)
    save(PACKAGE/'results/ir_compressed_queue_completion.json',dict(status='passed',plan_sha256=sha(path),rows=rows,target_checks_sha256=sha(proofpath)))
    save(state,dict(stage='passed',pid=os.getpid(),completed=len(rows),time=time.time()))

if __name__=='__main__':main()

