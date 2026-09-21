"""Revised public-cadence CB batch, isolated from the failed first plan."""
from common import *
import subprocess,time
from run_ab_paced_periodic import identity
from audit_ab_cb import inputs,audit_record
from queued_core_batch import free_memory


def main():
    path=PACKAGE/'ab_paced_periodic_plan.json';plan,kwargs=inputs(path.name)
    checks=PACKAGE/'results/ab_paced_periodic_checks.json';init=PACKAGE/'results/ab_paced_controlled_checks.json'
    assert sha(checks)==plan['runner_checks_sha256'] and sha(init)==plan['initialization_checks_sha256']
    assert json.loads(checks.read_text())['source_hashes']==identity()
    state=PACKAGE/'results/ab_paced_periodic_queue_state.json';rows=[]
    for s in plan['specs']:
        assert identity()==plan['source_hashes']
        p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        if not p.exists():
            while free_memory()<1.5*(1<<30):
                save(state,dict(stage='waiting_for_available_memory',pid=os.getpid(),completed=len(rows),next=s['id'],time=time.time()));time.sleep(5)
            sp=PACKAGE/'specs'/f"{s['id']}.json";save(sp,s)
            lp=PACKAGE/'results/logs'/f"{s['id']}.log";assert not lp.exists(),'inspect the earlier process and failure before retrying'
            cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_ab_paced_periodic.py'),'--spec',str(sp)]
            with lp.open('w',encoding='utf-8') as log:
                child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                save(PACKAGE/'results/processes'/f"{s['id']}.json",dict(pid=child.pid,parent_pid=os.getpid(),command=cmd,spec=s,started=time.time()))
                save(state,dict(stage='running',pid=os.getpid(),child_pid=child.pid,completed=len(rows),total=len(plan['specs']),next=s['id'],time=time.time()))
                code=child.wait()
            if code:
                save(state,dict(stage='failed',id=s['id'],exit_code=code,log=str(lp),time=time.time()));raise RuntimeError(s['id'])
        r=json.loads(p.read_text());audit_record(r,s,**kwargs)
        row=dict(id=s['id'],status='passed',bytes_per_request=r['bytes_per_request'],receipt_sha256=sha(p));rows.append(row)
        print(json.dumps(row),flush=True)
    save(PACKAGE/'results/ab_paced_periodic_queue_completion.json',dict(status='passed',rows=rows,plan_sha256=sha(path)))
    save(state,dict(stage='passed',pid=os.getpid(),completed=len(rows),time=time.time()))


if __name__=='__main__':main()
