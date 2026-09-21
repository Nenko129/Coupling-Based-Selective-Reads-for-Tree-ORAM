"""Explicit batches, bounded workers, immutable per-run outputs and logs."""
from common import *
import argparse,concurrent.futures,subprocess,time

def pilot_specs():
    out=[]
    for kind in ('path','deferred','sde','ring','gc_ring','r0'):
        out.append(dict(id=f'pilot_{kind}_N256_B4096',kind=kind,N=256,B=4096,profile=[4,3,3],
                        map_B=512,terminal_bytes=32768,compact=True,fusion=True,R=256,warmup=64,requests=128,
                        trace_seed=901,oram_seed=1901,workload='uniform',experiment_class='pilot'))
    for N in (4096,16384):
        out.append(dict(out[2],id=f'pilot_sde_N{N}_B4096',N=N))
    return out

def launch(spec):
    dest=PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json"
    if dest.exists():
        old=json.loads(dest.read_text(encoding='utf-8'))
        assert old['status']=='passed' and old['spec']==spec and old['source_hashes']==source_identity(),'stale completed receipt'
        return dict(id=spec['id'],status='reused')
    specfile=PACKAGE/'specs'/f"{spec['id']}.json";save(specfile,spec)
    logfile=PACKAGE/'results/logs'/f"{spec['id']}.log";logfile.parent.mkdir(parents=True,exist_ok=True)
    with logfile.open('w',encoding='utf-8') as log:
        p=subprocess.Popen([sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_core.py'),'--spec',str(specfile)],
                           stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        save(PACKAGE/'results/processes'/f"{spec['id']}.json",dict(pid=p.pid,started=time.time(),spec=spec,log=str(logfile)))
        code=p.wait()
    if code!=0:return dict(id=spec['id'],status='failed',returncode=code,log=str(logfile))
    row=json.loads(dest.read_text(encoding='utf-8'))
    return dict(id=spec['id'],status='passed',seconds=row['elapsed_seconds'],bytes_per_request=row['bytes_per_request'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',default='pilot');p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    specs=pilot_specs() if args.batch=='pilot' else json.loads(Path(args.batch).read_text(encoding='utf-8'))['specs']
    save(PACKAGE/'results/batch_plan.json',dict(specs=specs,workers=args.workers,created=time.time()))
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(launch,s) for s in specs]
        for f in concurrent.futures.as_completed(futures):
            row=f.result();results.append(row);print(json.dumps(row),flush=True)
    save(PACKAGE/'results/batch_completion.json',dict(results=results,completed=time.time(),all_passed=all(r['status'] in ('passed','reused') for r in results)))
    if any(r['status']=='failed' for r in results):raise SystemExit(1)
if __name__=='__main__':main()
