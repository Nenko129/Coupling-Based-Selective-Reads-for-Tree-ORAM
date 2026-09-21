from pathlib import Path
import json,zipfile,hashlib,tempfile,subprocess,sys,datetime
ROOT=Path('D:/projects/SDE-R0')
BASE=ROOT/'TDSC_SOC3_审阅与投稿方案_2026-09-15'
HOME=BASE/'Selective_通用组合与投稿实验准备_2026-09-16'
PACK=HOME/'论文实验章节完整证据_2026-09-16'
OUT=BASE/'投稿证据复核与文献整理_2026-09-17'
archive=PACK/'source_evidence/Selective_最小组合审阅包.zip'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=load(PACK/'source_evidence/audits/minimal__portable_bundle_check.json')
temp=Path(tempfile.mkdtemp(prefix='final_archive_review_20260917_',dir=ROOT/'tmp'))
with zipfile.ZipFile(archive) as z:
 for name in z.namelist():assert (temp/name).resolve().is_relative_to(temp.resolve())
 assert z.testzip() is None
 z.extractall(temp)
manifest=load(temp/'MANIFEST.json')
for row in manifest['files']:
 p=temp/'workspace'/row['path'];assert sha(p)==row['sha256'];assert p.stat().st_size==row['bytes']
replica=temp/'workspace'/HOME.relative_to(ROOT)
def run(name,args):
 p=subprocess.run([sys.executable,'-B','-X','utf8',*map(str,args)],cwd=replica,capture_output=True,text=True,encoding='utf-8')
 (OUT/(name+'.stdout.txt')).write_text(p.stdout,encoding='utf-8')
 (OUT/(name+'.stderr.txt')).write_text(p.stderr,encoding='utf-8')
 assert p.returncode==0,(name,p.stderr[-2000:])
run('portable_contract_replay',[replica/'src/check_minimal_contract.py'])
checks=load(replica/'results/minimal_contract_checks.json')
replays=[]
for rid,driver in [('MIN_pilot_AB_depth_selective_B64_seed101','run_minimal.py'),('MIN_pilot_free_compressed_sde_B64_seed101','run_frontend_minimal.py')]:
 target=replica/'results/pilot'/f'{rid}.json';before=load(target)
 run('replay_'+rid,[replica/'src'/driver,'--spec',replica/'specs/pilot'/f'{rid}.json'])
 after=load(target)
 keys=['spec','trace','source_hashes','answer_sha256','bytes_per_request','rpc_per_request']
 for k in keys:assert before[k]==after[k],(rid,k)
 # Check wire-ledger invariants again on the newly executed encrypted messages.
 m=after['phases']['measurement'];bills=m.get('bills',[m])
 for b in bills:
  assert b['total_bytes']==b['request_bytes']+b['response_bytes']==sum(b['components'].values())
  assert b['rpc']==b['independently_invoiced_rpcs']==b['next_sequence']-b['first_sequence']
 replays.append({'id':rid,'status':'passed','compared_fields':keys,'bytes_per_request':after['bytes_per_request'],'rpc_per_request':after['rpc_per_request'],'answer_sha256':after['answer_sha256'],'replayed_receipt_sha256':sha(target)})
out={'status':'passed','checked_on':datetime.datetime.now().isoformat(),'archive':str(archive),'archive_sha256':sha(archive),
 'old_receipt_archive_sha256':old['archive_sha256'],'old_receipt_matches_final_archive':old['archive_sha256']==sha(archive),
 'manifest_files':len(manifest['files']),'all_member_hashes_verified':True,'replica':str(replica),
 'contract_checks':checks,'replays':replays,
 'scope':'Fresh clean-directory replay of the final archived minimal artifact: all member hashes, contract checker and two pilot cases. Does not rerun the full formal matrix or certify native-system security. Frozen original bundle is unchanged; this receipt supersedes the stale replay binding.'}
(OUT/'final_archive_replay.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='contract_checks'},ensure_ascii=False))
