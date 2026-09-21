"""Finish only missing frozen scale receipts with bounded sequential execution.

The original dispatcher uses a deliberately conservative 1.6x memory gate.
This companion keeps execution serial and uses the same frozen runner/specs,
but allows a lower operator-supplied free-memory floor.  Receipt validation is
identical; the original dispatcher is rerun afterwards for canonical closure.
"""

from common import *
from dispatch_bulk_scale import validate
import argparse
import subprocess
import time


def available_bytes():
    if os.name != "nt": return 2**63
    import ctypes
    class M(ctypes.Structure):
        _fields_=[("length",ctypes.c_ulong),("load",ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ("total","available","page_total","page_available","virtual_total","virtual_available","extended")]
    m=M();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.available


def main():
    p=argparse.ArgumentParser();p.add_argument("--queue",required=True);p.add_argument("--minimum-free-gb",type=float,default=2.5);a=p.parse_args()
    path=Path(a.queue);plan=json.loads(path.read_text(encoding="utf-8"))
    for source,digest in plan["source_plan_hashes"].items():assert sha(PACKAGE/source)==digest
    floor=int(a.minimum_free_gb*(1<<30));state=PACKAGE/"results"/"scale_pending_state.json";rows=[]
    for item in plan["items"]:
        s=item["spec"];dest=PACKAGE/"results"/s["experiment_class"]/f"{s['id']}.json"
        if dest.exists():
            validate(json.loads(dest.read_text(encoding="utf-8")),item);rows.append({"id":s["id"],"status":"reused"});continue
        while available_bytes()<floor:
            save(state,{"stage":"waiting_for_available_memory","next":s["id"],"minimum_bytes":floor,"available_bytes":available_bytes(),"time":time.time()});time.sleep(20)
        sp=PACKAGE/"specs"/f"{s['id']}.json"
        if sp.exists():assert json.loads(sp.read_text(encoding="utf-8"))==s
        else:save(sp,s)
        log=PACKAGE/"results"/"logs"/"scale_pending"/f"{s['id']}.log";log.parent.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,"-B","-X","utf8",str(Path(__file__).parent/"run_bulk_scale.py"),"--spec",str(sp)]
        with log.open("w",encoding="utf-8") as stream:
            child=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,cwd=str(PACKAGE),creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            save(state,{"stage":"running","next":s["id"],"child_pid":child.pid,"completed":len(rows),"total":len(plan["items"]),"time":time.time()})
            code=child.wait()
        if code:
            save(state,{"stage":"failed","id":s["id"],"returncode":code,"log":str(log),"time":time.time()});raise SystemExit(code)
        row=json.loads(dest.read_text(encoding="utf-8"));validate(row,item);rows.append({"id":s["id"],"status":"passed","bytes_per_request":row["bytes_per_request"]})
    save(PACKAGE/"results"/"extended_scale_queue_accelerated_completion.json",{"status":"passed","rows":rows,"queue_sha256":sha(path)})
    save(state,{"stage":"complete","completed":len(rows),"total":len(plan["items"]),"time":time.time()})
    print(json.dumps({"completed":len(rows),"total":len(plan["items"])}))


if __name__=="__main__":main()
