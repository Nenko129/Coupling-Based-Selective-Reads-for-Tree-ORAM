"""Wait for frozen shards, close both matrices, and assemble non-XLSX evidence."""

from pathlib import Path
import ctypes
import json
import os
import subprocess
import sys
import time


HOME=Path(__file__).resolve().parents[1]
EVAL=HOME.parent/"论文带宽实验_2026-09-16"
STATE=HOME/"results"/"paper_completion_state.json"


def save(obj):
    STATE.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def alive(pid):
    if os.name!="nt":
        try:os.kill(pid,0);return True
        except OSError:return False
    api=ctypes.windll.kernel32;api.OpenProcess.restype=ctypes.c_void_p
    h=api.OpenProcess(0x1000,False,pid)
    if not h:return False
    try:
        code=ctypes.c_ulong();api.GetExitCodeProcess(ctypes.c_void_p(h),ctypes.byref(code));return code.value==259
    finally:api.CloseHandle(ctypes.c_void_p(h))


def terminate(pid):
    if not alive(pid):return
    api=ctypes.windll.kernel32;api.OpenProcess.restype=ctypes.c_void_p
    h=api.OpenProcess(0x0001,False,pid)
    if not h:raise RuntimeError(f"cannot open process {pid}")
    try:
        if not api.TerminateProcess(ctypes.c_void_p(h),0):raise RuntimeError(f"cannot terminate {pid}")
    finally:api.CloseHandle(ctypes.c_void_p(h))


def run(label,cmd,cwd):
    log=HOME/"logs"/f"completion_{label}.log";log.parent.mkdir(exist_ok=True)
    save({"stage":label,"command":cmd,"log":str(log),"time":time.time()})
    with log.open("w",encoding="utf-8") as stream:
        p=subprocess.run(cmd,cwd=str(cwd),stdout=stream,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f"{label} failed: {p.returncode}, inspect {log}")


def main():
    proc=json.loads((HOME/"results"/"shards"/"dispatcher_processes.json").read_text(encoding="utf-8"))
    while any(alive(int(x["pid"])) for x in proc):
        save({"stage":"waiting_for_formal_shards","formal_receipts":len(list((HOME/"results"/"formal").glob("*.json"))),"time":time.time()})
        time.sleep(30)
    states=[json.loads(p.read_text(encoding="utf-8")) for p in sorted((HOME/"results"/"shards").glob("shard_*_of_08.json"))]
    assert len(states)==8 and all(s["stage"]=="complete" for s in states),states
    assert len(list((HOME/"results"/"formal").glob("*.json")))==120

    py=sys.executable
    run("formal_canonical_validation",[py,"-B","-X","utf8",str(HOME/"src"/"dispatch.py"),"--suite","formal","--wait"],HOME)
    run("minimal_finalizer",[py,"-B","-X","utf8",str(HOME/"tools"/"finalize.py")],HOME)

    old_state=json.loads((EVAL/"results"/"extended_scale_queue_bulk_state.json").read_text(encoding="utf-8"))
    old_pid=old_state.get("pid")
    if old_pid and alive(int(old_pid)):
        assert old_state.get("stage")=="waiting_for_available_memory",old_state
        terminate(int(old_pid));time.sleep(2)
    run("scale_pending",[py,"-B","-X","utf8",str(EVAL/"src"/"dispatch_scale_pending.py"),"--queue",str(EVAL/"extended_scale_queue.json"),"--minimum-free-gb","2.5"],EVAL)
    run("scale_canonical_validation",[py,"-B","-X","utf8",str(EVAL/"src"/"dispatch_bulk_scale.py"),"--queue",str(EVAL/"extended_scale_queue.json")],EVAL)
    run("assemble_paper_evidence",[py,"-B","-X","utf8",str(HOME/"tools"/"assemble_paper_evidence.py")],HOME)
    save({"stage":"non_xlsx_complete","formal_receipts":120,"scale_receipts":125,"output":str(HOME/"论文实验章节完整证据_2026-09-16"),"time":time.time()})


if __name__=="__main__":
    try:main()
    except Exception as exc:
        save({"stage":"failed","error":repr(exc),"time":time.time()});raise
