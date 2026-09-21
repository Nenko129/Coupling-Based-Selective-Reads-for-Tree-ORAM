from common import *
import argparse,concurrent.futures,subprocess,time
import composition_runtime as runtime
from workloads import stored_trace

def prepare():
    specs=[]
    for seed in range(101,106):
        for workload in ('uniform','hot90','zipf09','scan'):
            stored_trace(4096,6144,seed,workload)
            for family in ('free_raw','free_compressed','rho'):
                for kind in ('deferred','sde','ring','r0'):
                    specs.append(dict(id=f'C_{family}_{kind}_{workload}_N4096_B64_seed{seed}',family=family,kind=kind,N=4096,B=64,
                                      profile=[4,3,4],plb=8,llc=32,rho=128,R=256,warmup=2048,requests=4096,
                                      trace_seed=seed,oram_seed=seed+900,workload=workload,experiment_class='formal_composition'))
    plan=dict(specs=specs,runs=len(specs),source_hashes=runtime.identity(),
              scope='restricted executable Freecursive/rho compositions; no native PMMAC/ECC/async; see each run contract',
              selection='predeclared 4 distributions x3 frontends x4 corresponding backends x5 independent keys/traces',
              rho_frame_policy='one continuous warmup batch and one measurement batch; final public frame padded; no per-window padding',
              warmup_and_sample='finite prefixes; not complete periodic/steady-state claims',
              enlarged_relative_to_previous='N256->4096; 5 independent keys; 4096 measured application requests/run')
    save(PACKAGE/'formal_composition_plan.json',plan);return plan

def launch(spec,identity):
    assert runtime.identity()==identity,'composition source changed after predeclaration'
    dest=PACKAGE/'results/formal_composition'/f"{spec['id']}.json"
    if dest.exists():
        row=json.loads(dest.read_text(encoding='utf-8'))
        assert row['source_hashes']==identity and row['spec']==spec and row['status']=='passed'
        return dict(id=spec['id'],status='reused')
    path=PACKAGE/'specs'/f"{spec['id']}.json";save(path,spec)
    logpath=PACKAGE/'results/logs'/f"{spec['id']}.log";logpath.parent.mkdir(parents=True,exist_ok=True)
    with logpath.open('w',encoding='utf-8') as log:
        p=subprocess.Popen([sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_composition.py'),'--spec',str(path)],
                           stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        save(PACKAGE/'results/processes'/f"{spec['id']}.json",dict(pid=p.pid,started=time.time(),spec=spec,log=str(logpath)))
        code=p.wait()
    if code:return dict(id=spec['id'],status='failed',code=code)
    row=json.loads(dest.read_text(encoding='utf-8'))
    return dict(id=spec['id'],status='passed',seconds=row['elapsed_seconds'],bytes_per_request=row['bytes_per_request'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=2);p.add_argument('--prepare-only',action='store_true');args=p.parse_args()
    path=PACKAGE/'formal_composition_plan.json';plan=json.loads(path.read_text(encoding='utf-8')) if path.exists() else prepare()
    if args.prepare_only:print(json.dumps(dict(runs=plan['runs'])));return
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        fs=[pool.submit(launch,s,plan['source_hashes']) for s in plan['specs']]
        for f in concurrent.futures.as_completed(fs):
            row=f.result();rows.append(row);print(json.dumps(row),flush=True)
    save(PACKAGE/'results/composition_batch_completion.json',dict(rows=rows,passed=all(r['status'] in ('passed','reused') for r in rows)))
    if any(r['status']=='failed' for r in rows):raise SystemExit(1)
if __name__=='__main__':main()
