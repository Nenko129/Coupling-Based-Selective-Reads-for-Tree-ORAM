"""Paths and reproducible, atomic evidence output. Frozen sources are read only."""
from pathlib import Path
import hashlib,json,os,sys

PACKAGE=Path(__file__).resolve().parents[1]
ROOT=PACKAGE.parents[1]
FROZEN=ROOT/'SOC3_audit_2026-09-15/research_20260914/optimization_v1/src'
COMPOSITION=PACKAGE.parent/'组合协议推进_2026-09-15/src'
sys.path.insert(0,str(FROZEN))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,path)

def source_identity():
    # Bind the runtime closure. Adding a separate plot/check tool while a long
    # run is live must not falsely mark the running executable as changed.
    paths=[Path(__file__).parent/n for n in ('common.py','meter.py','workloads.py','run_core.py')]+sorted(FROZEN.glob('*.py'))
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}
