"""Bounded sequential extended experiments; completed identities are immutable."""
from common import *
from queued_core_batch import free_memory
from resume_fast_batches import alive
from run_extended import identity as core_identity
from run_extended_composition import identity as composition_identity
from run_core import configs_for
from prepare_fair_tuning import object_storage
import argparse,math,subprocess,time

def memory_threshold(item):
    s=item['spec']
    if item['entry']=='core':size=object_storage(configs_for(s))
    else:
        # Conservative dispatch estimate only, never reported as measured trusted memory.
        size=16*s['N']*(s['B']+1024)
        if s['family']=='rho':size+=32*s['rho']*(s['B']+512)
    return max(1.5*(1<<30),1.6*size+0.75*(1<<30))

def validate(row,item):
    assert row['status']=='passed' and row['spec']==item['spec']
    expected=core_identity() if item['entry']=='core' else composition_identity()
    assert row['source_hashes']==expected and row['extended_experiment']['source_identity']==expected

def main():
    p=argparse.ArgumentParser();p.add_argument('--queue',required=True);args=p.parse_args()
    path=Path(args.queue);plan=json.loads(path.read_text(encoding='utf-8'));name=path.stem;results=[]
    statepath=PACKAGE/'results'/f'{name}_state.json'
    proof=json.loads((PACKAGE/'results/extended_runner_checks.json').read_text())
    assert proof['status']=='passed'
    assert all(sha(Path(__file__).parent/n)==digest for n,digest in proof['adapters'].items())
    for dep in plan.get('dependencies',[]):
        while alive(dep['pid']):
            save(statepath,dict(stage='waiting_for_verified_process',pid=os.getpid(),dependency=dep,time=time.time()));time.sleep(5)
        done=json.loads((PACKAGE/dep['completion']).read_text())
        assert done.get('passed',done.get('status')=='passed'), 'Dependency did not complete successfully'
    for source,digest in plan['source_plan_hashes'].items():assert sha(PACKAGE/source)==digest
    for item in plan['items']:
        s=item['spec'];dest=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        if dest.exists():
            validate(json.loads(dest.read_text(encoding='utf-8')),item);results.append(dict(id=s['id'],status='reused'));continue
        minimum=memory_threshold(item)
        while free_memory()<minimum:
            save(statepath,dict(stage='waiting_for_available_memory',pid=os.getpid(),next=s['id'],minimum_bytes=minimum,time=time.time()));time.sleep(5)
        sp=PACKAGE/'specs'/f"{s['id']}.json"
        if sp.exists():assert json.loads(sp.read_text(encoding='utf-8'))==s
        else:save(sp,s)
        lp=PACKAGE/'results/logs'/f"{s['id']}_extended.log";assert not lp.exists(),'Inspect prior job before retry'
        script='run_extended.py' if item['entry']=='core' else 'run_extended_composition.py'
        cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).parent/script),'--spec',str(sp)]
        with lp.open('w',encoding='utf-8') as log:
            proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            save(PACKAGE/'results/processes'/f"{s['id']}_extended.json",dict(pid=proc.pid,parent_pid=os.getpid(),command=cmd,spec=s,started=time.time()))
            save(statepath,dict(stage='running',pid=os.getpid(),child_pid=proc.pid,next=s['id'],completed=len(results),total=len(plan['items']),time=time.time()))
            code=proc.wait()
        if code:
            save(statepath,dict(stage='failed',id=s['id'],exit_code=code,log=str(lp),time=time.time()));raise RuntimeError('Extended run failed: '+s['id'])
        row=json.loads(dest.read_text(encoding='utf-8'));validate(row,item)
        result=dict(id=s['id'],status='passed',bytes_per_request=row['bytes_per_request']);results.append(result);print(json.dumps(result),flush=True)
    save(PACKAGE/'results'/f'{name}_completion.json',dict(status='passed',rows=results,queue_sha256=sha(path)))
    save(statepath,dict(stage='passed',pid=os.getpid(),completed=len(results),time=time.time()))

if __name__=='__main__':main()
