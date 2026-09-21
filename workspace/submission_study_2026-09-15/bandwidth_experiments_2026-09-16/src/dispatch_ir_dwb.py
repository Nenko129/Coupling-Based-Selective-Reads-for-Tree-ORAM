"""One memory-aware worker for the predeclared IR integration batch."""
from common import *
from run_ir_dwb import identity
from queued_core_batch import free_memory
import subprocess,time

def main():
    planpath=PACKAGE/'formal_ir_dwb_plan.json';plan=json.loads(planpath.read_text());expected=identity()
    # Only a reporting typo in initial-data byte order changed after pilot.
    # Preserve the original binding, with zero formal receipts allowed here.
    if plan['source_hashes']!=expected:
        assert not list((PACKAGE/'results/formal_ir_dwb').glob('*.json'))
        assert plan['source_hashes']['runtime']==expected['runtime']
        revision=PACKAGE/'results/ir_dwb_plan_metadata_revision.json';assert not revision.exists()
        save(revision,dict(before=plan['source_hashes'],after=expected,reason='Initial-data description corrected from little-endian to big-endian; no execution or input changes; before all formal runs'))
        plan['source_hashes']=expected;plan['metadata_revision']=str(revision.relative_to(PACKAGE));save(planpath,plan)
    proof=json.loads((PACKAGE/'results/ir_dwb_controller_checks.json').read_text());assert proof['status']=='passed'
    assert proof['runtime_identity']==expected['runtime'];rows=[]
    for s in plan['specs']:
        assert identity()==expected
        dest=PACKAGE/'results/formal_ir_dwb'/f"{s['id']}.json"
        if dest.exists():
            r=json.loads(dest.read_text());assert r['status']=='passed' and r['spec']==s and r['source_hashes']==expected
            rows.append(dict(id=s['id'],status='reused'));continue
        while free_memory()<1.5*(1<<30):
            save(PACKAGE/'results/ir_dwb_queue_state.json',dict(stage='waiting_for_available_memory',pid=os.getpid(),completed=len(rows),next=s['id'],time=time.time()));time.sleep(5)
        sp=PACKAGE/'specs'/f"{s['id']}.json";save(sp,s)
        lp=PACKAGE/'results/logs'/f"{s['id']}.log";assert not lp.exists(),'inspect any prior run before retry'
        cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_ir_dwb.py'),'--spec',str(sp)]
        with lp.open('w',encoding='utf-8') as log:
            child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            save(PACKAGE/'results/processes'/f"{s['id']}.json",dict(pid=child.pid,parent_pid=os.getpid(),command=cmd,spec=s,started=time.time()))
            save(PACKAGE/'results/ir_dwb_queue_state.json',dict(stage='running',pid=os.getpid(),child_pid=child.pid,completed=len(rows),total=len(plan['specs']),next=s['id'],time=time.time()))
            code=child.wait()
        if code:
            save(PACKAGE/'results/ir_dwb_queue_state.json',dict(stage='failed',id=s['id'],exit_code=code,log=str(lp),time=time.time()));raise RuntimeError(s['id'])
        r=json.loads(dest.read_text());assert r['status']=='passed' and r['spec']==s and r['source_hashes']==expected
        row=dict(id=s['id'],status='passed',bytes_per_request=r['bytes_per_request']);rows.append(row);print(json.dumps(row),flush=True)
    save(PACKAGE/'results/ir_dwb_queue_completion.json',dict(status='passed',rows=rows,plan_sha256=sha(planpath)))
    save(PACKAGE/'results/ir_dwb_queue_state.json',dict(stage='passed',pid=os.getpid(),completed=len(rows),time=time.time()))

if __name__=='__main__':main()
