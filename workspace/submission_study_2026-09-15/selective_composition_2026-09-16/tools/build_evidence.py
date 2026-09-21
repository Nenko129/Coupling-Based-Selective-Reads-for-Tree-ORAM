from pathlib import Path
import sys,json,shutil,datetime,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_frontend_minimal import *

def main():
    base=HOME.parent;root=base.parent
    old=json.loads((base/'树状ORAM组合候选筛选_2026-09-15/candidates.json').read_text(encoding='utf-8'))
    papers=[]
    for c in old['candidates']:
        p=Path(c['source']);assert sha(p)==c['source_sha256']
        row={k:c[k] for k in ('title','year','source','source_sha256','public_primary_url','read_scope_pdf_pages') if k in c}
        text_path=base/'树状ORAM组合候选筛选_2026-09-15'/c['text']
        row.update(text=str(text_path),text_sha256=sha(text_path),review_basis='existing primary-text extraction; selection re-assessed in 01; not every page freshly re-read')
        papers.append(row)
    extra=json.loads((base/'IR_AB_深入分析_2026-09-16/sources.json').read_text(encoding='utf-8'))['papers']
    for p in extra:
        assert sha(p['path'])==p['sha256'];papers.append(p)
    save(HOME/'sources.json',dict(papers=papers,note='historical combination_proved/measured flags deliberately not reused; current status is in this package'))
    selected={root/p for p in identity()}
    legacy=ORIGINAL_IDENTITY()
    selected.update(root/p for p in legacy['core']);selected.update(root/p for p in legacy['composition'])
    selected.add(EVAL/'src/transfer_backend_fixed.py')
    selected.update(HOME.glob('*.md'));selected.update(HOME.glob('*plan.json'));selected.update(HOME.glob('*lock.json'));selected.add(HOME/'sources.json')
    selected.update((HOME/'tools').glob('*.py'));selected.update((HOME/'specs').rglob('*.json'))
    selected.update((HOME/'results/pilot').glob('*.json'));selected.update((HOME/'results/formal').glob('*.json'))
    selected.update((HOME/'results').glob('*.json'));selected.update((HOME/'figures').glob('*'))
    dependencies=[root/'SOC3_audit_2026-09-15/proofs/02_parameterized_reduction.md',
        root/'SOC3_audit_2026-09-15/selective_oram_final_chain_2026-09-11/proofs/01_reduction_complete.md',
        base/'组合协议推进_2026-09-15/01_迁移接口与参数化证明.md',base/'组合协议推进_2026-09-15/validation_receipt.json',
        base/'IR_AB_深入分析_2026-09-16/01_协议与证明边界.md',EVAL/'07_IR容量准入与实验修订.md',
        EVAL/'45_经典基线执行归约与容量账本.md',EVAL/'61_IR公开尾部补充实验进度.md',
        EVAL/'results/ir_guarded_statistics.json',EVAL/'results/ir_guarded_observations.json',
        EVAL/'numerics/IR43_scaled_L12_c480_m128_audit.json',EVAL/'numerics/exact_checks.json',EVAL/'numerics/ghost_profile.cpp',
        EVAL/'numerics/profiles/IR43_scaled_L12.json',EVAL/'numerics/profiles/IR43_scaled_L12.txt']
    for p in dependencies:assert p.exists(),p;selected.add(p)
    selected.update((EVAL/'numerics/grids').glob('IR43_scaled_L12_*c480_m128*'))
    for suite in ('pilot','formal'):
        for p in (HOME/'results'/suite).glob('*.json'):
            r=json.loads(p.read_text(encoding='utf-8'));tp=EVAL/r['trace']['path'];assert sha(tp)==r['trace']['sha256'];selected.add(tp)
    entries=[];stage=HOME/'review_bundle/workspace'
    for p in sorted(selected):
        assert p.is_file();relative=p.relative_to(root);dest=stage/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        entries.append(dict(path=relative.as_posix(),sha256=sha(p),bytes=p.stat().st_size))
    manifest=dict(created=datetime.datetime.now().isoformat(),files=entries,scope='new minimal runtime, plans, receipts and selected proof dependencies; PDFs referenced by hash, not copied; not a full native-system artifact')
    save(HOME/'review_bundle/MANIFEST.json',manifest)
    readme='This snapshot preserves workspace-relative paths. Python 3.12+ is sufficient for runtime/checks; figures additionally use matplotlib.\nSee the Chinese 00/03 reports under TDSC_SOC3_审阅与投稿方案_2026-09-15/Selective_通用组合与投稿实验准备_2026-09-16.\nVerify SHA256 against MANIFEST.json before running. Existing original-paper PDFs are referenced by hash and are not redistributed.\n'
    (HOME/'review_bundle/README.txt').write_text(readme,encoding='utf-8')
    archive=HOME/'Selective_最小组合审阅包.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(HOME/'review_bundle/MANIFEST.json','MANIFEST.json');z.write(HOME/'review_bundle/README.txt','README.txt')
        for e in entries:z.write(stage/e['path'],'workspace/'+e['path'])
    assert all(sha(stage/e['path'])==e['sha256'] for e in entries)
    save(HOME/'bundle_receipt.json',dict(status='passed',files=len(entries),archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
        snapshot_manifest_sha256=sha(HOME/'review_bundle/MANIFEST.json'),time=datetime.datetime.now().isoformat()))
    print(json.dumps(dict(status='passed',files=len(entries),archive_bytes=archive.stat().st_size)))
if __name__=='__main__':main()
