"""Target-scale gate; do not change a failed public horizon."""
from common import *
import subprocess,time
from run_ir_compressed_periodic import identity,evidence
from audit_ir_compressed import audit_record,inputs
from queued_core_batch import free_memory

def validate_plan(plan):
    assert plan['source_hashes']==identity() and plan['proof_hashes']==evidence()
    for name,value in plan['execution_tools'].items():assert sha(Path(__file__).parent/name)==value
    assert sha(PACKAGE/'results/ir_compressed_runner_checks.json')==plan['runner_checks_sha256']

def execute(s,plan,state,completed,total):
    validate_plan(plan);dest=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
    if not dest.exists():
        while free_memory()<1.5*(1<<30):
            save(state,dict(stage='waiting_for_available_memory',pid=os.getpid(),completed=completed,next=s['id'],time=time.time()));time.sleep(5)
        sp=PACKAGE/'specs'/f"{s['id']}.json";save(sp,s)
        log=PACKAGE/'results/logs'/f"{s['id']}.log";assert not log.exists(),'inspect existing attempt; no implicit restart'
        cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('run_ir_compressed_periodic.py')),'--spec',str(sp)]
        with log.open('w',encoding='utf-8') as out:
            child=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            save(PACKAGE/'results/processes'/f"{s['id']}.json",dict(pid=child.pid,parent_pid=os.getpid(),command=cmd,spec=s,started=time.time()))
            save(state,dict(stage='running',pid=os.getpid(),child_pid=child.pid,completed=completed,total=total,next=s['id'],time=time.time()))
            code=child.wait()
        if code:
            save(state,dict(stage='failed',pid=os.getpid(),id=s['id'],exit_code=code,time=time.time()))
            raise RuntimeError('preserved failed compressed-map run: '+s['id'])
    r=json.loads(dest.read_text());audit_record(r,s,**inputs())
    return dict(id=s['id'],path=str(dest.relative_to(PACKAGE)),sha256=sha(dest),bytes_per_request=r['bytes_per_request'])

def main():
    p=PACKAGE/'formal_ir_compressed_plan.json';plan=json.loads(p.read_text());state=PACKAGE/'results/ir_compressed_validation_state.json';rows=[]
    for s in plan['pilots']:
        row=execute(s,plan,state,len(rows),len(plan['pilots']));r=json.loads((PACKAGE/row['path']).read_text())
        if s['beta']==4:assert r['phases']['measurement']['frontend_metrics']['group_reset_slots']>0
        rows.append(row);print(json.dumps(row),flush=True)
    validate_plan(plan)
    save(PACKAGE/'results/ir_compressed_target_checks.json',dict(status='passed',plan_sha256=sha(p),source_hashes=identity(),
        cases=rows,runner_checks_sha256=plan['runner_checks_sha256'],validator_sha256=sha(__file__)))
    save(state,dict(stage='passed',pid=os.getpid(),completed=len(rows),time=time.time()))

if __name__=='__main__':main()

