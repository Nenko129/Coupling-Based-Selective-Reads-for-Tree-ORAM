"""One memory-aware worker for extended matrices; never repeats a live core run."""
from common import *
import argparse,ctypes,time
from batch_core import launch

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('totalPhys','availPhys','totalPageFile','availPageFile','totalVirtual','availVirtual','availExtendedVirtual')]

def free_memory():
    x=MEMORYSTATUSEX();x.length=ctypes.sizeof(x)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(x)):raise OSError('memory query failed')
    return x.availPhys

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--min-free-gib',type=float,default=3);args=p.parse_args()
    path=Path(args.plan);plan=json.loads(path.read_text(encoding='utf-8'));name=path.stem;rows=[]
    for spec in plan['specs']:
        while free_memory()<args.min_free_gib*(1<<30):
            save(PACKAGE/'results'/f'{name}_queue_state.json',dict(pid=os.getpid(),stage='waiting_for_available_memory',run_id=spec['id'],minimum_free_gib=args.min_free_gib,time=time.time()))
            time.sleep(10)
        assert plan['source_hashes']==source_identity(),'source changed since predeclaration'
        save(PACKAGE/'results'/f'{name}_queue_state.json',dict(pid=os.getpid(),stage='running',run_id=spec['id'],time=time.time()))
        result=launch(spec);rows.append(result);print(json.dumps(result),flush=True)
        if result['status']=='failed':raise SystemExit(1)
    save(PACKAGE/'results'/f'{name}_queue_completion.json',dict(status='passed',rows=rows,aliases_not_reexecuted=plan.get('aliases',[])))
    save(PACKAGE/'results'/f'{name}_queue_state.json',dict(pid=os.getpid(),stage='passed',time=time.time()))
if __name__=='__main__':main()
