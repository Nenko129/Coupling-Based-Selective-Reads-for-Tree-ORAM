"""Resume predeclared inputs after draining legacy children; never replace receipts."""
from common import *
from run_fast import expected_identity, fast_sources
from queued_core_batch import free_memory
import argparse, concurrent.futures, ctypes, itertools, subprocess, threading, time


def alive(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    h=kernel.OpenProcess(0x1000,0,int(pid))
    if not h:
        if ctypes.get_last_error() in (87,1168):return False
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        code=ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(h,ctypes.byref(code)):raise ctypes.WinError(ctypes.get_last_error())
        return code.value==259
    finally:kernel.CloseHandle(h)


def validate(row,spec,mode):
    assert row['status']=='passed' and row['spec']==spec
    assert row['source_hashes'] in (source_identity(),expected_identity()), 'Unknown runtime revision'
    if row['source_hashes']==expected_identity():
        assert row['execution_revision']['name']=='hmac_prefix_reuse_v1'
        assert row['execution_revision']['proof_sha256']==sha(PACKAGE/'results/fast_prf_regression.json')
    if mode=='cached':
        assert 'cache_representation' in row
        assert all(sha(Path(__file__).parent/n)==v for n,v in row['cache_and_heterogeneous_sources'].items())


def main():
    p=argparse.ArgumentParser();p.add_argument('--queue',required=True);p.add_argument('--workers',type=int,default=3)
    p.add_argument('--min-free-gib',type=float,default=1.5);args=p.parse_args()
    path=Path(args.queue);plan=json.loads(path.read_text(encoding='utf-8'));name=path.stem
    proof=json.loads((PACKAGE/'results/fast_runner_checks.json').read_text())
    assert proof['status']=='passed' and proof['runner_sha256']==sha(Path(__file__).parent/'run_fast.py')
    for pid in plan.get('drain_pids',[]):
        while alive(pid):
            save(PACKAGE/'results'/f'{name}_state.json',dict(stage='draining_verified_legacy_child',pid=os.getpid(),child=pid,time=time.time()))
            time.sleep(5)
    # The inputs are copied into this queue, with hashes of the immutable parent plans.
    for source,digest_ in plan['source_plan_hashes'].items():assert sha(PACKAGE/source)==digest_
    items=plan['items']; lock=threading.Lock(); results=[]
    def launch(item):
        spec=item['spec'];mode=item['mode'];dest=PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json"
        if dest.exists():
            validate(json.loads(dest.read_text(encoding='utf-8')),spec,mode)
            return dict(id=spec['id'],status='reused')
        while True:
            with lock:
                if free_memory()>=args.min_free_gib*(1<<30):
                    sp=PACKAGE/'specs'/f"{spec['id']}.json"
                    if sp.exists():assert json.loads(sp.read_text(encoding='utf-8'))==spec
                    else:save(sp,spec)
                    logpath=PACKAGE/'results/logs'/f"{spec['id']}_fast.log"
                    assert not logpath.exists(), 'Inspect prior fast job before a retry'
                    log=logpath.open('w',encoding='utf-8')
                    cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_fast.py'),'--spec',str(sp),'--mode',mode]
                    proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    save(PACKAGE/'results/processes'/f"{spec['id']}_fast.json",dict(pid=proc.pid,parent_pid=os.getpid(),spec=spec,mode=mode,command=cmd,started=time.time()))
                    # Brief staggering lets the new process allocate before another launch.
                    time.sleep(2)
                    break
            time.sleep(5)
        code=proc.wait();log.close()
        if code:
            save(PACKAGE/'results/failures'/f"{spec['id']}_fast.json",dict(spec=spec,exit_code=code,log=logpath.read_text(encoding='utf-8')))
            raise RuntimeError('Fast batch failure: '+spec['id'])
        row=json.loads(dest.read_text(encoding='utf-8'));validate(row,spec,mode)
        return dict(id=spec['id'],status='passed',bytes_per_request=row['bytes_per_request'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(launch,item) for item in items]
        for f in concurrent.futures.as_completed(futures):
            result=f.result();results.append(result)
            save(PACKAGE/'results'/f'{name}_state.json',dict(stage='running',pid=os.getpid(),completed=len(results),total=len(items),last=result,time=time.time()))
            print(json.dumps(result),flush=True)
    save(PACKAGE/'results'/f'{name}_completion.json',dict(status='passed',rows=results,queue_sha256=sha(path)))

if __name__=='__main__':main()
