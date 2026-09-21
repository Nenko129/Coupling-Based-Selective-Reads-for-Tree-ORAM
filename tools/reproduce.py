"""Public release entry point; frozen inputs are never overwritten."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
BASE = 'TDSC_SOC3_审阅与投稿方案_2026-09-15'
EVAL = Path(BASE)/'论文带宽实验_2026-09-16'
MIN = Path(BASE)/'Selective_通用组合与投稿实验准备_2026-09-16'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    m=json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
    for name,h in m['files'].items():
        p=(ROOT/name).resolve(); p.relative_to(ROOT)
        assert p.is_file() and sha(p)==h, name
    # Verify the surviving files against the ORIGINAL audit identity as well.
    audit=ROOT/'workspace/SOC3_audit_2026-09-15'
    original=json.loads((audit/'BUNDLE_MANIFEST.json').read_text(encoding='utf-8'))['files']
    checked=0; omitted=[]
    excluded={x['path'] for x in json.loads((ROOT/'provenance/excluded_files.json').read_text(encoding='utf-8'))}
    for name,h in original.items():
        p=audit/name
        if p.exists(): assert sha(p)==h,name; checked+=1
        else:
            assert 'SOC3_audit_2026-09-15/'+name in excluded,name
            omitted.append(name)
    return dict(release_files=len(m['files']),original_audit_files_checked=checked,declared_original_omissions=omitted)

def copy_file(src,dst):
    # Avoid CopyFile2 MAX_PATH failures for preserved historical Unicode paths.
    if os.name=='nt':
        src='\\\\?\\'+str(Path(src).resolve())
        dst='\\\\?\\'+str(Path(dst).resolve())
    with open(src,'rb') as a, open(dst,'wb') as b: shutil.copyfileobj(a,b)
    return dst

def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['verify','smoke','audit-results','core-quick','core-full','replay-spec'])
    p.add_argument('--out',type=Path)
    p.add_argument('--driver',help='Driver path relative to workspace (replay-spec)')
    p.add_argument('--spec',help='Spec path relative to workspace (replay-spec)')
    a=p.parse_args(); report=dict(mode=a.mode,integrity=verify()); started=time.time()
    if a.mode=='verify': print(json.dumps(report,indent=2)); return
    assert a.out is not None,'--out must name a new directory outside this artifact'
    out=a.out.resolve();assert not out.is_relative_to(ROOT),'Keep the release immutable'
    assert not out.exists(),'Use a new output directory'
    out.mkdir(parents=True)
    env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    tasks=[]
    def run(label,args,cwd):
        log=out/(label+'.log')
        print('Running',label,flush=True)
        with log.open('w',encoding='utf-8') as f:
            r=subprocess.run([sys.executable,'-B','-X','utf8',*map(str,args)],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        tasks.append(dict(label=label,returncode=r.returncode,log=log.name))
        if r.returncode: raise RuntimeError('Failed '+label+'; inspect '+str(log))
    try:
        if a.mode in {'core-quick','core-full'}:
            run(a.mode,[ROOT/'tools/run_core_audit.py',a.mode,str(out/'core')],ROOT)
        else:
            work=out/'workspace';shutil.copytree(ROOT/'workspace',work,copy_function=copy_file)
            if a.mode=='smoke':
                run('host-contract',[work/MIN/'src/check_minimal_contract.py'],work)
                run('frontend-reset',[work/MIN/'tools/check_frontend_reset.py'],work)
                for name,driver in [('MIN_pilot_AB_depth_selective_B64_seed101','run_minimal.py'),('MIN_pilot_free_compressed_sde_B64_seed101','run_frontend_minimal.py')]:
                    run(name,[work/MIN/'src'/driver,'--spec',work/MIN/'specs/pilot'/(name+'.json')],work)
                    orig=json.loads((ROOT/'workspace'/MIN/'results/pilot'/(name+'.json')).read_text(encoding='utf-8'))
                    new=json.loads((work/MIN/'results/pilot'/(name+'.json')).read_text(encoding='utf-8'))
                    for k in ('spec','trace','source_hashes','answer_sha256','bytes_per_request','rpc_per_request'): assert orig[k]==new[k],(name,k)
                report['replay_matches']='spec, trace, code hashes, answers, bytes, RPC'
            elif a.mode=='audit-results':
                for name in ['audit_completed_core_components.py','audit_completed_ablation.py','audit_tuned_reference.py']:
                    run(name,[work/EVAL/'src'/name],work)
                run('minimal-statistics',[work/MIN/'tools/analyze_and_freeze.py'],work)
            else:
                assert a.driver and a.spec,'--driver and --spec required'
                driver=(work/a.driver).resolve();spec=(work/a.spec).resolve()
                driver.relative_to(work);spec.relative_to(work)
                run('replay-spec',[driver,'--spec',spec],work)
        report['status']='passed'
    except Exception as exc:
        report.update(status='failed',error=str(exc));raise
    finally:
        report.update(tasks=tasks,elapsed_seconds=time.time()-started)
        (out/'receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))

if __name__=='__main__': main()
