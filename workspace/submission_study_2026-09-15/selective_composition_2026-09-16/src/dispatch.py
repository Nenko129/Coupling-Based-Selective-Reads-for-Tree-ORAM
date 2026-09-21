"""Serial, resumable, frozen-input dispatch; no task or service installation."""
from minimal_runtime import *
import argparse,subprocess,time,os,ctypes

class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]

def free_memory():
    if os.name!='nt':return 2**63
    m=Memory();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.available

def main():
    p=argparse.ArgumentParser();p.add_argument('--suite',choices=['pilot','formal'],required=True);p.add_argument('--limit',type=int);p.add_argument('--only-id');p.add_argument('--wait',action='store_true');a=p.parse_args()
    plan=json.loads((HOME/f'{a.suite}_plan.json').read_text(encoding='utf-8'));frozen=json.loads((HOME/'source_lock.json').read_text(encoding='utf-8'))
    assert frozen['source_hashes']==identity(),'runtime changed: prepare a new revision rather than mixing results'
    checks=json.loads((HOME/'results/minimal_contract_checks.json').read_text(encoding='utf-8'))
    assert checks['status']=='passed' and checks['source_hashes']==identity()
    chosen=[s for s in plan['specs'] if not a.only_id or s['id']==a.only_id]
    if a.only_id:assert len(chosen)==1
    count=0
    for s in chosen:
        out=HOME/'results'/a.suite/f"{s['id']}.json"
        if out.exists():
            row=json.loads(out.read_text(encoding='utf-8'));assert row['spec']==s and row['status']=='passed'
            recorded=row['source_hashes'];recorded=recorded['minimal'] if 'minimal' in recorded else recorded
            assert recorded==identity(),'stale receipt';continue
        required=1.25*2**30 if s['B']==4096 else 0.6*2**30
        while free_memory()<required:
            save(HOME/'results/queue_state.json',dict(stage='waiting_for_available_memory',id=s['id'],pid=os.getpid(),required_bytes=required,time=time.time()))
            if not a.wait:print('Insufficient free memory; queue is resumable.');return
            time.sleep(20)
        assert frozen['source_hashes']==identity()
        cmd=[sys.executable,'-B','-X','utf8',str(HOME/'src'/s['driver']),'--spec',str(HOME/'specs'/a.suite/f"{s['id']}.json")]
        log=HOME/'logs'/f"{s['id']}.log";log.parent.mkdir(exist_ok=True)
        with log.open('w',encoding='utf-8') as stream:
            child=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,cwd=str(HOME))
            save(HOME/'results/queue_state.json',dict(stage='running',id=s['id'],pid=os.getpid(),child_pid=child.pid,time=time.time()))
            rc=child.wait()
        if rc:
            save(HOME/'results/queue_state.json',dict(stage='failed',id=s['id'],returncode=rc,log=str(log),time=time.time()));raise SystemExit(rc)
        count+=1
        if a.limit and count>=a.limit:break
    done=sum((HOME/'results'/a.suite/f"{s['id']}.json").exists() for s in plan['specs'])
    save(HOME/'results/queue_state.json',dict(stage='complete' if done==len(plan['specs']) else 'partial',suite=a.suite,completed=done,total=len(plan['specs']),time=time.time()))
    print(json.dumps(dict(completed=done,total=len(plan['specs']))))
if __name__=='__main__':main()
