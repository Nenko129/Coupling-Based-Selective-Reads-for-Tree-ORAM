"""Run complete practical-height depth profiles, with per-job process receipts."""
from common import *
import subprocess,time,csv
from check_profile_numerics import linux

NUM=PACKAGE/'numerics'
def main():
    gate=json.loads((NUM/'exact_checks.json').read_text(encoding='utf-8'))
    assert gate['status']=='passed' and gate['kernel_sha256']==sha(NUM/'ghost_profile.cpp') and gate['binary_sha256']==sha(NUM/'ghost_profile')
    names=['uniform43_h13','uniform76_h12','IR43_scaled_L12','IR43_native_leaf4'];jobs=[]
    for name in names:
        profile=NUM/'profiles'/f'{name}.txt';spec=json.loads(profile.with_suffix('.json').read_text(encoding='utf-8'))
        for mode in ('up','next'):
            prefix=NUM/'grids'/f'{name}_{mode}_c280';prefix.parent.mkdir(exist_ok=True)
            args=['wsl','--exec',linux(NUM/'ghost_profile'),'280',str(len(spec['Z_root_to_leaf'])),'128','1',mode,linux(prefix),linux(profile)]
            meta=prefix.with_name(prefix.name+'_meta.json')
            if meta.exists():raise RuntimeError('Audit existing job identity/liveness before resuming a numerical profile')
            logpath=prefix.with_suffix('.log')
            with logpath.open('w',encoding='utf-8') as log:
                p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                save(NUM/'live_job.json',dict(profile=name,mode=mode,windows_wsl_pid=p.pid,started=time.time(),command=args,
                     kernel_sha256=sha(NUM/'ghost_profile.cpp'),binary_sha256=sha(NUM/'ghost_profile'),profile_sha256=sha(profile)))
                code=p.wait()
            if code:raise RuntimeError(f'numeric job failed {name}/{mode}; retained log {logpath}')
            obj=json.loads(meta.read_text());assert obj['rounding_self_test'] and obj['height']==len(spec['Z_root_to_leaf'])
            rows=list(csv.DictReader(prefix.with_suffix('.csv').open()));assert len(rows)==obj['height']*281
            job=dict(profile=name,mode=mode,grid_sha256=sha(prefix.with_suffix('.csv')),metadata_sha256=sha(meta),log_sha256=sha(logpath),
                     prefix=str(prefix.relative_to(PACKAGE)),height=obj['height'],cap=280,poisson_cutoff=128)
            jobs.append(job);save(NUM/'completed_jobs.json',dict(jobs=jobs,all_jobs_complete=False));print(json.dumps(job),flush=True)
    save(NUM/'completed_jobs.json',dict(jobs=jobs,all_jobs_complete=True,practical_parameter_admission_not_yet_audited=True))
if __name__=='__main__':main()
