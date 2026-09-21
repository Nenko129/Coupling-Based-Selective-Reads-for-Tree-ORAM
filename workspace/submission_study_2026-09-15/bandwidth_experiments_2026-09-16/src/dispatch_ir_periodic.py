"""Run the predeclared aligned IR batch after the finite-prefix batch completes."""
from common import *
from run_ir_periodic import identity
from resume_fast_batches import alive
from queued_core_batch import free_memory
import subprocess,time


def main():
    path=PACKAGE/'formal_ir_periodic_plan.json';plan=json.loads(path.read_text());expected=identity()
    assert plan['source_hashes']==expected
    proof=json.loads((PACKAGE/'results/ir_periodic_runner_checks.json').read_text())
    assert proof['status']=='passed' and proof['source_hashes']==expected
    state=PACKAGE/'results/ir_periodic_queue_state.json';rows=[]
    for dep in plan['dependencies']:
        while alive(dep['pid']):
            save(state,dict(stage='waiting_for_verified_process',pid=os.getpid(),dependency=dep,time=time.time()));time.sleep(5)
        done=json.loads((PACKAGE/dep['completion']).read_text());assert done['status']=='passed'
        assert done['plan_sha256']==sha(PACKAGE/'formal_ir_dwb_plan.json')
    for s in plan['specs']:
        assert identity()==expected
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        if not p.exists():
            while free_memory()<1.5*(1<<30):
                save(state,dict(stage='waiting_for_available_memory',pid=os.getpid(),completed=len(rows),next=s['id'],time=time.time()));time.sleep(5)
            sp=PACKAGE/'specs'/f"{s['id']}.json";save(sp,s)
            lp=PACKAGE/'results/logs'/f"{s['id']}.log";assert not lp.exists(),'inspect prior process and log before any retry'
            cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_ir_periodic.py'),'--spec',str(sp)]
            with lp.open('w',encoding='utf-8') as log:
                child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                save(PACKAGE/'results/processes'/f"{s['id']}.json",dict(pid=child.pid,parent_pid=os.getpid(),command=cmd,spec=s,started=time.time()))
                save(state,dict(stage='running',pid=os.getpid(),child_pid=child.pid,completed=len(rows),total=len(plan['specs']),next=s['id'],time=time.time()))
                code=child.wait()
            if code:
                save(state,dict(stage='failed',id=s['id'],exit_code=code,log=str(lp),time=time.time()));raise RuntimeError(s['id'])
        r=json.loads(p.read_text());assert r['status']=='passed' and r['spec']==s and r['source_hashes']==expected
        row=dict(id=s['id'],status='passed',bytes_per_request=r['bytes_per_request']);rows.append(row);print(json.dumps(row),flush=True)
    save(PACKAGE/'results/ir_periodic_queue_completion.json',dict(status='passed',rows=rows,plan_sha256=sha(path)))
    save(state,dict(stage='passed',pid=os.getpid(),completed=len(rows),time=time.time()))


if __name__=='__main__':main()
