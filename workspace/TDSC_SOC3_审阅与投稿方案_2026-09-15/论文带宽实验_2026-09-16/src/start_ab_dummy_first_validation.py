"""Wait on the actual diagnostic process; do not bypass a failed diagnosis."""
from common import *
import argparse,ctypes,time,traceback,subprocess


def alive(pid):
    kernel=ctypes.windll.kernel32;handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        code=ctypes.c_ulong();assert kernel.GetExitCodeProcess(handle,ctypes.byref(code));return code.value==259
    finally:kernel.CloseHandle(handle)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dependency-pid',type=int,required=True);args=parser.parse_args()
    state=PACKAGE/'results/ab_dummy_first_validation_dependency.json';base=dict(pid=os.getpid(),dependency_pid=args.dependency_pid)
    try:
        while alive(args.dependency_pid):
            save(state,dict(base,stage='waiting_for_live_diagnostic',time=time.time()));time.sleep(5)
        path=PACKAGE/'results/ab_selection_diagnostic.json';d=json.loads(path.read_text())
        assert d['status']=='diagnostic_completed'
        row,=[r for r in d['cases'] if r['spec']['policy']=='dummy_first']
        assert row['status']=='completed' and row['checked_answers']==4096 and row['clock']==65536
        import ab_dummy_first_runtime as rt
        assert row['source_hashes']['revised']==rt.identity()
        proof=json.loads((PACKAGE/'results/ab_dummy_first_checks.json').read_text())
        assert proof['status']=='passed' and proof['source_hashes']==rt.identity()
        save(state,dict(base,stage='running_six_target_cases',time=time.time(),diagnostic_sha256=sha(path)))
        command=[sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('check_ab_dummy_first_controlled.py'))]
        result=subprocess.run(command,cwd=PACKAGE);assert result.returncode==0,'full-scale revision validation failed'
        save(state,dict(base,stage='six_target_cases_passed',time=time.time(),diagnostic_sha256=sha(path)))
    except Exception:
        save(state,dict(base,stage='failed',time=time.time(),error=traceback.format_exc()));raise


if __name__=='__main__':main()
