"""Public release entry point; frozen inputs are never overwritten."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys, time, io, zipfile, copy

ROOT = Path(__file__).resolve().parents[1]
BASE = 'submission_study_2026-09-15'
EVAL = Path(BASE)/'bandwidth_experiments_2026-09-16'
MIN = Path(BASE)/'selective_composition_2026-09-16'

def migration():
    return json.loads((ROOT/'provenance/path_migration.json').read_text(encoding='utf-8'))

def legacy(path):
    names={v:k for k,v in migration()['component_names'].items()}
    return Path(*(names.get(n,n) for n in Path(path).parts))

def original_archive_bytes(path):
    item=migration().get('archive_migrations',{}).get(path.relative_to(ROOT).as_posix())
    if item is None: return None
    output=io.BytesIO()
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(output,'w',compresslevel=item['compression_level']) as target:
        target.comment=source.comment
        reverse={v:k for k,v in item['member_names'].items()}
        for info in source.infolist():
            old=copy.copy(info);old.filename=reverse.get(info.filename,info.filename);old.orig_filename=old.filename
            target.writestr(old,source.read(info.filename),compresslevel=item['compression_level'])
    data=output.getvalue()
    assert hashlib.sha256(data).hexdigest()==item['original_sha256']
    return data

def materialize(work):
    """Restore immutable historical inputs outside the ASCII-only repository."""
    for row in migration()['files']:
        if not row['original'].startswith('workspace/'): continue
        src=ROOT/row['published'];dst=work/Path(row['original']).relative_to('workspace')
        restored=original_archive_bytes(src) if src.suffix=='.zip' else None
        assert (hashlib.sha256(restored).hexdigest() if restored is not None else sha(src))==row['sha256'],row['published']
        dst.parent.mkdir(parents=True,exist_ok=True)
        if restored is None: copy_file(src,dst)
        else: dst.write_bytes(restored)

def sha(p):
    if os.name=='nt': p=Path('\\\\?\\'+str(p.resolve()))
    return hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    m=json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
    for name,h in m['files'].items():
        p=(ROOT/name).resolve(); p.relative_to(ROOT)
        assert sha(p)==h, name
    # Verify the surviving files against the ORIGINAL audit identity as well.
    audit=ROOT/'workspace/SOC3_audit_2026-09-15'
    original=json.loads((audit/'BUNDLE_MANIFEST.json').read_text(encoding='utf-8'))['files']
    checked=0; omitted=[]
    excluded={x['path'] for x in json.loads((ROOT/'provenance/excluded_files.json').read_text(encoding='utf-8'))}
    remap={r['original']:r['published'] for r in migration()['files']}
    for name,h in original.items():
        old='workspace/SOC3_audit_2026-09-15/'+name
        p=ROOT/remap.get(old,old)
        if p.exists():
            restored=original_archive_bytes(p) if p.suffix=='.zip' else None
            assert (hashlib.sha256(restored).hexdigest() if restored is not None else sha(p))==h,name
            checked+=1
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
        work=out/'workspace';materialize(work)
        old_min=legacy(MIN);old_eval=legacy(EVAL)
        if a.mode in {'core-quick','core-full'}:
            run(a.mode,[ROOT/'tools/run_core_audit.py',a.mode,str(out/'core'),str(work)],ROOT)
        else:
            if a.mode=='smoke':
                run('host-contract',[work/old_min/'src/check_minimal_contract.py'],work)
                run('frontend-reset',[work/old_min/'tools/check_frontend_reset.py'],work)
                for name,driver in [('MIN_pilot_AB_depth_selective_B64_seed101','run_minimal.py'),('MIN_pilot_free_compressed_sde_B64_seed101','run_frontend_minimal.py')]:
                    run(name,[work/old_min/'src'/driver,'--spec',work/old_min/'specs/pilot'/(name+'.json')],work)
                    orig=json.loads((ROOT/'workspace'/MIN/'results/pilot'/(name+'.json')).read_text(encoding='utf-8'))
                    new=json.loads((work/old_min/'results/pilot'/(name+'.json')).read_text(encoding='utf-8'))
                    for k in ('spec','trace','source_hashes','answer_sha256','bytes_per_request','rpc_per_request'): assert orig[k]==new[k],(name,k)
                report['replay_matches']='spec, trace, code hashes, answers, bytes, RPC'
            elif a.mode=='audit-results':
                for name in ['audit_completed_core_components.py','audit_completed_ablation.py','audit_tuned_reference.py']:
                    run(name,[work/old_eval/'src'/name],work)
                run('minimal-statistics',[work/old_min/'tools/analyze_and_freeze.py'],work)
            else:
                assert a.driver and a.spec,'--driver and --spec required'
                driver=(work/legacy(a.driver)).resolve();spec=(work/legacy(a.spec)).resolve()
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
