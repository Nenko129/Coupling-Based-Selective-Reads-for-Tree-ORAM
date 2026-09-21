"""Final reporting stage of the already-running experiment pipeline."""
from pathlib import Path
import sys,json,time,subprocess,ctypes,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minimal_runtime import *

def alive(pid):
    if os.name!='nt':return True
    api=ctypes.windll.kernel32;api.OpenProcess.restype=ctypes.c_void_p
    handle=api.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        code=ctypes.c_ulong();assert api.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code))
        return code.value==259
    finally:api.CloseHandle(ctypes.c_void_p(handle))

def main():
    if '--wait' in sys.argv:
        while True:
            state=json.loads((HOME/'results/queue_state.json').read_text(encoding='utf-8'))
            if state.get('stage')=='complete' and state.get('suite')=='formal':break
            if state.get('stage')=='failed' or ('pid' in state and not alive(state['pid'])):
                save(HOME/'results/finalization.json',dict(status='needs_attention',queue=state));return
            time.sleep(20)
    for name in ('analyze_and_freeze.py','preflight.py','render_figures.py','update_overview.py','build_evidence.py'):
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(HOME/'tools'/name)],cwd=str(HOME))
        if p.returncode:
            save(HOME/'results/finalization.json',dict(status='failed',tool=name,returncode=p.returncode));raise SystemExit(p.returncode)
    data=json.loads((HOME/'results/analysis.json').read_text(encoding='utf-8'))
    formal=[r for r in data['comparisons'] if r['suite']=='formal']
    done=len(list((HOME/'results/formal').glob('*.json')))==120
    save(HOME/'results/finalization.json',dict(status='complete' if done and all(r['headline_eligible'] for r in formal) else 'partial_or_needs_repeats',
        formal_complete=done,needs_more_repeats=[r for r in formal if r.get('needs_more_repeats')],
        note='does not claim native complete-system security, true trusted peak measurement or network latency'))
if __name__=='__main__':main()
