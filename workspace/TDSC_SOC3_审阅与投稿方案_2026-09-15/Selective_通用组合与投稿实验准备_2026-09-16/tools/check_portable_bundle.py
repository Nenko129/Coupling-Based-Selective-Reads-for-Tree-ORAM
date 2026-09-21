from pathlib import Path
import sys,json,tempfile,zipfile,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minimal_runtime import *

def main():
    archive=HOME/'Selective_最小组合审阅包.zip'
    temp=Path(tempfile.mkdtemp(prefix='selective_minimal_replay_',dir=str(common.ROOT/'tmp')))
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            target=(temp/name).resolve()
            assert target.is_relative_to(temp.resolve()),'unsafe archive path'
        z.extractall(temp)
    manifest=json.loads((temp/'MANIFEST.json').read_text(encoding='utf-8'))
    for e in manifest['files']:assert sha(temp/'workspace'/e['path'])==e['sha256']
    replica=temp/'workspace'/HOME.relative_to(common.ROOT)
    checks=subprocess.run([sys.executable,'-B','-X','utf8',str(replica/'src/check_minimal_contract.py')],cwd=str(replica),capture_output=True,text=True,encoding='utf-8')
    assert checks.returncode==0,checks.stderr
    replay=[]
    for name,driver in [('MIN_pilot_AB_depth_selective_B64_seed101','run_minimal.py'),('MIN_pilot_free_compressed_sde_B64_seed101','run_frontend_minimal.py')]:
        run=subprocess.run([sys.executable,'-B','-X','utf8',str(replica/'src'/driver),'--spec',str(replica/'specs/pilot'/f'{name}.json')],cwd=str(replica),capture_output=True,text=True,encoding='utf-8')
        assert run.returncode==0,run.stderr
        original=json.loads((HOME/'results/pilot'/f'{name}.json').read_text(encoding='utf-8'))
        cloned=json.loads((replica/'results/pilot'/f'{name}.json').read_text(encoding='utf-8'))
        for key in ('spec','trace','source_hashes','answer_sha256','bytes_per_request','rpc_per_request'):assert original[key]==cloned[key],key
        replay.append(dict(id=name,bytes_per_request=cloned['bytes_per_request'],answers_sources_and_invoices_match=True))
    save(HOME/'results/portable_bundle_check.json',dict(status='passed',archive_sha256=sha(archive),manifest_files=len(manifest['files']),replica=str(replica),coupling_check_passed=True,replayed=replay,
        scope='clean-path unpack, all-file hashes, semantic check and two deterministic encrypted replay cases; no claim of a separate human audit'))
    print(json.dumps(dict(status='passed',files=len(manifest['files']),replays=len(replay))))
if __name__=='__main__':main()
