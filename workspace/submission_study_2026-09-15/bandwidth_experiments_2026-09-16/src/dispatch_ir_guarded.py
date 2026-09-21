"""Serial memory-gated worker; existing logs/outcomes never silently retried."""
from common import *
import subprocess,time
from queued_core_batch import free_memory
from run_ir_guarded_periodic import identity,evidence
from audit_ir_guarded_periodic import audit_record,tool_hashes


def validate(plan):
    assert plan['source_hashes']==identity() and plan['proof_hashes']==evidence() and plan['audit_tools']==tool_hashes()
    assert plan['dispatcher_sha256']==sha(__file__)
    assert plan['generator_sha256']==sha(Path(__file__).with_name('prepare_ir_guarded.py'))
    assert plan['runner_gate_sha256']==sha(PACKAGE/'results/ir_guarded_runner_checks.json')
    assert plan['original_completed_snapshot_sha256']==sha(PACKAGE/'results/ir_compressed_completed_snapshot.json')
    assert plan['original_plan_sha256']==sha(PACKAGE/'formal_ir_compressed_plan.json')
    assert plan['logical_diagnosis_sha256']==sha(PACKAGE/'results/ir_reset_window_replay.json')


def execute(s,plan,state,completed,total):
    validate(plan);dest=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
    if not dest.exists():
        assert not (PACKAGE/'results/failures'/f"{s['id']}.json").exists(),'preserve failed outcome; no implicit retry'
        log=PACKAGE/'results/logs'/f"{s['id']}.log";assert not log.exists(),'inspect existing attempt before restart'
        while free_memory()<1.5*(1<<30):
            save(state,dict(stage='waiting_for_available_memory',pid=os.getpid(),completed=completed,next=s['id'],time=time.time()));time.sleep(5)
        sp=PACKAGE/'specs'/f"{s['id']}.json";save(sp,s)
        cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('run_ir_guarded_periodic.py')),'--spec',str(sp)]
        with log.open('w',encoding='utf-8') as out:
            child=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            save(PACKAGE/'results/processes'/f"{s['id']}.json",dict(pid=child.pid,parent_pid=os.getpid(),command=cmd,spec=s,started=time.time()))
            save(state,dict(stage='running',pid=os.getpid(),child_pid=child.pid,completed=completed,total=total,next=s['id'],time=time.time()))
            code=child.wait()
        if code:
            save(state,dict(stage='failed',pid=os.getpid(),id=s['id'],exit_code=code,time=time.time()))
            raise RuntimeError('preserved failed supplemental run: '+s['id'])
    validate(plan);r=json.loads(dest.read_text());checked=audit_record(r,s)
    return dict(id=s['id'],path=str(dest.relative_to(PACKAGE)),sha256=sha(dest),audit=checked)


def main():
    pp=PACKAGE/'formal_ir_guarded_plan.json';plan=json.loads(pp.read_text());validate(plan)
    state=PACKAGE/'results/ir_guarded_queue_state.json';pilots=[];rows=[]
    for s in plan['pilots']:
        row=execute(s,plan,state,len(pilots),2);pilots.append(row)
        if s['beta']==4:assert row['audit']['measurement_reset_slots']>0
        print(json.dumps(dict(stage='pilot_passed',id=s['id'])),flush=True)
    save(PACKAGE/'results/ir_guarded_target_checks.json',dict(status='passed',plan_sha256=sha(pp),cases=pilots,source_hashes=identity(),auditors=tool_hashes()))
    for s in plan['specs']:
        row=execute(s,plan,state,len(rows),len(plan['specs']));rows.append(row)
        save(PACKAGE/'results/ir_guarded_observations.json',dict(status='in_progress',plan_sha256=sha(pp),observations=rows,expected=30))
        print(json.dumps(dict(stage='formal_passed',id=s['id'],completed=len(rows))),flush=True)
    save(PACKAGE/'results/ir_guarded_completion.json',dict(status='passed',plan_sha256=sha(pp),source_hashes=identity(),observations=rows,expected=30))
    save(state,dict(stage='passed',pid=os.getpid(),completed=len(rows),time=time.time()))


if __name__=='__main__':main()
