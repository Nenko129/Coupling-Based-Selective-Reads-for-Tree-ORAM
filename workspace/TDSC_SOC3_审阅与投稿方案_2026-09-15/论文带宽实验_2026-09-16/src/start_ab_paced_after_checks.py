"""Continue the authorized batch only after the known control-check process exits."""
from common import *
import argparse,time,traceback
from resume_fast_batches import alive
from prepare_ab_paced_periodic import main as prepare
from dispatch_ab_paced_periodic import main as dispatch


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dependency-pid',type=int,required=True);args=parser.parse_args()
    state=PACKAGE/'results/ab_paced_dependency_state.json'
    try:
        while alive(args.dependency_pid):
            save(state,dict(stage='waiting_for_verified_process',pid=os.getpid(),dependency_pid=args.dependency_pid,time=time.time()));time.sleep(5)
        proof=PACKAGE/'results/ab_paced_controlled_checks.json'
        assert proof.exists() and json.loads(proof.read_text())['status']=='passed','target-scale controller checks did not complete successfully'
        prepare();save(state,dict(stage='dispatching_verified_revision',pid=os.getpid(),dependency_pid=args.dependency_pid,time=time.time()))
        dispatch()
        save(state,dict(stage='passed',pid=os.getpid(),time=time.time()))
    except Exception:
        save(state,dict(stage='failed',pid=os.getpid(),dependency_pid=args.dependency_pid,error=traceback.format_exc(),time=time.time()));raise


if __name__=='__main__':main()
