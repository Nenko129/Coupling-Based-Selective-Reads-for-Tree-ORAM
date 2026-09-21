"""Continue the new paired experiment after target validation, never on failure."""
from common import *
import argparse,time,traceback
from start_ab_dummy_first_validation import alive
from prepare_ab_dummy_first_periodic import main as prepare
from dispatch_ab_dummy_first_periodic import main as dispatch


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dependency-pid',type=int,required=True);args=parser.parse_args()
    path=PACKAGE/'results/ab_dummy_first_batch_dependency.json';base=dict(pid=os.getpid(),dependency_pid=args.dependency_pid)
    try:
        while alive(args.dependency_pid):
            save(path,dict(base,stage='waiting_for_live_validation',time=time.time()));time.sleep(5)
        prepare();save(path,dict(base,stage='dispatching_verified_revision',time=time.time()));dispatch()
        save(path,dict(base,stage='passed',time=time.time()))
    except Exception:
        save(path,dict(base,stage='failed',time=time.time(),error=traceback.format_exc()));raise


if __name__=='__main__':main()
