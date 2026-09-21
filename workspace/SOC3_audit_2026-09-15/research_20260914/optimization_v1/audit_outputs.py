from pathlib import Path
from fractions import Fraction as F
import sys,json,hashlib,re
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from optimized_gate import OptimizedBank,BASE
from optimized_oram import Config
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((BASE/'MANIFEST.sha256.json').read_text())['files']
for name,value in manifest.items():assert sha(BASE/name)==(value if isinstance(value,str) else value['sha256'])
bank=OptimizedBank();d=json.loads((ROOT/'results/profile_comparison.json').read_text())
N0=12582912;online=(1<<64)-N0-12288
for row in d['variants']:
    cs=[Config(**c) for c in row['configs']];kind='sde' if row['label'].startswith('SDE-') else 'r0';offset=2 if kind=='sde' else 6
    limit=(online+N0)*bank.grids[4,3][24,192-offset]+(online+N0+12288)*bank.grids[4,3][14,144-offset]
    fresh=bank.plan(cs,online,limit);assert fresh==row['capacity_plan']
    assert row['payload_plus_terminal']<=1425408
    if 'with-path-budget' in row['label']:assert row['persistent_plus_report_path_payload']<=1806336
    for name,old in d['original_bytes'].items():assert abs(row['reduction_vs_original_percent'][name]-100*(1-row['bytes']/old))<1e-10
    assert F(row['total']['lower'])<=F(row['total']['upper'])
receipt=json.loads((ROOT/'numerics/recompute_receipt.json').read_text())
for name,value in receipt['source_and_outputs_sha256'].items():assert sha(ROOT/'numerics'/name)==value
text=(ROOT/'优化实施与基线对比.md').read_text(encoding='utf-8');links=re.findall(r'\]\((D:/[^)]+)\)',text)
assert all(Path(p).exists() for p in links)
report=dict(original_manifest_files_unchanged=len(manifest),variant_contract_artifacts_checked=len(json.loads((ROOT/'variant_contract.json').read_text())['artifact_sha256']),
            exact_plans_rechecked=len(d['variants']),original_stash_numeric_bounds_preserved=True,
            report_local_links_valid=len(links),fresh_numeric_receipt_verified=True,
            all_checks_passed=True,scope='Research model and serialized application-frame costs; not deployed throughput or full-memory RSS.')
(ROOT/'results/final_audit.json').write_text(json.dumps(report,indent=2))
files=[p for p in ROOT.rglob('*') if p.is_file() and p.name!='OUTPUT_MANIFEST.sha256.json' and '__pycache__' not in p.parts]
(ROOT/'OUTPUT_MANIFEST.sha256.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(files)},indent=2))
print(json.dumps(report,indent=2))
