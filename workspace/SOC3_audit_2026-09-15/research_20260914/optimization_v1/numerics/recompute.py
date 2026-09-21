"""Rebuild both enclosures and independent checks, with source/output receipts."""
from pathlib import Path
import subprocess,json,hashlib,platform
ROOT=Path(__file__).resolve().parent
flags=['-std=c++17','-O3','-fopenmp','-frounding-math','-ffp-contract=off','-fno-fast-math']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['g++',*flags,str(ROOT/'ghost_z7a6.cpp'),'-o',str(ROOT/'ghost_z7a6')],check=True)
old={}
for mode in ('up','next'):
    prefix=ROOT/f'z7a6_{mode}_c280_h24';csv=prefix.with_suffix('.csv')
    if csv.exists():old[mode]=sha(csv)
    result=subprocess.run([str(ROOT/'ghost_z7a6'),'280','24','128','4',mode,str(prefix)],check=True,capture_output=True,text=True)
    (ROOT/f'recompute_{mode}.log').write_text(result.stderr)
    if mode in old:assert sha(csv)==old[mode],'guard-only edit changed numeric endpoints'
    print(mode,'full grid PASS',flush=True)
subprocess.run(['python3',str(ROOT/'validate_new_scalar.py')],check=True)
names=['ghost_z7a6.cpp','poisson_seed.h','poisson_seed.json','ghost_z7a6','validate_new_scalar.py','validation_results.json']
names += [f'z7a6_{m}_c280_h24{s}' for m in ('up','next') for s in ('.csv','_meta.json','_levels.csv')]
receipt=dict(source_and_outputs_sha256={n:sha(ROOT/n) for n in names},compiler_flags=flags,
             python=platform.python_version(),platform=platform.platform(),fresh_full_recomputation=True,
             arithmetic_modes=['FE_UPWARD','nearest_plus_NextUp'],points_per_mode=24*281)
(ROOT/'recompute_receipt.json').write_text(json.dumps(receipt,indent=2))
