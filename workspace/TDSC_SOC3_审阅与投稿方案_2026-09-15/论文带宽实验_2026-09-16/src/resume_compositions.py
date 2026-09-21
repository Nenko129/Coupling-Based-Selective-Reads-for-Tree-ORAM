"""Resume unchanged Freecursive cases and run every rho pair under the fix."""
from common import *
import argparse,concurrent.futures,subprocess,time
from batch_composition import launch
import composition_runtime as runtime

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['free','rho'],required=True);args=p.parse_args()
    plan=json.loads((PACKAGE/'formal_composition_plan.json').read_text(encoding='utf-8'))
    if args.mode=='free':
        specs=[s for s in plan['specs'] if s['family']!='rho']
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(launch,s,plan['source_hashes']) for s in specs]
            rows=[]
            for f in concurrent.futures.as_completed(futures):
                r=f.result();rows.append(r);print(json.dumps(r),flush=True)
        save(PACKAGE/'results/free_continuation_completion.json',dict(rows=rows,passed=all(r['status'] in ('passed','reused') for r in rows)))
    else:
        specs=[dict(s,id=s['id'].replace('C_rho','C2_rho',1),experiment_class='formal_rho_fixed') for s in plan['specs'] if s['family']=='rho']
        save(PACKAGE/'formal_rho_fixed_plan.json',dict(specs=specs,reason='rerun all 80 rho configurations consistently after reachable Path pool guard bug',
             original_plan_sha256=sha(PACKAGE/'formal_composition_plan.json'),fix_sha256=sha(Path(__file__).parent/'transfer_backend_fixed.py')))
        for s in specs:
            path=PACKAGE/'specs'/f"{s['id']}.json";save(path,s)
            result=PACKAGE/'results/formal_rho_fixed'/f"{s['id']}.json"
            if result.exists():raise RuntimeError('explicitly audit existing rho fixed receipt before resume')
            logpath=PACKAGE/'results/logs'/f"{s['id']}.log"
            with logpath.open('w',encoding='utf-8') as log:
                proc=subprocess.Popen([sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_rho_fixed.py'),'--spec',str(path)],
                         stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                save(PACKAGE/'results/processes'/f"{s['id']}.json",dict(pid=proc.pid,started=time.time(),spec=s,log=str(logpath)))
                code=proc.wait()
            if code:raise RuntimeError(f'fixed rho failed: {s["id"]}; preserve log')
            r=json.loads(result.read_text(encoding='utf-8'));print(json.dumps(dict(id=s['id'],bytes_per_request=r['bytes_per_request'])),flush=True)
        save(PACKAGE/'results/rho_fixed_completion.json',dict(passed=True,runs=len(specs)))
if __name__=='__main__':main()
