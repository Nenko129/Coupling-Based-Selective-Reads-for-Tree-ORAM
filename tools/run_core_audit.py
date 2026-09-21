"""Run original audit functions after the public release subset check.

Not a re-seal or a claim to verify omitted external-paper snapshots.
Use reproduce.py as the public entry point.
"""
from pathlib import Path
import sys,json
from reproduce import ROOT,verify
report={'integrity':verify()}
sys.path.insert(0,str(Path(sys.argv[3])/'SOC3_audit_2026-09-15/audit'))
import fusion,integrated,numerical
out=Path(sys.argv[2]);out.mkdir(parents=True)
report['original_identities']=integrated.identities()
numerical.seed_check()
f=fusion.audit(out/'fusion.json')
integrated.audit(out/'integrated')
if sys.argv[1]=='core-full': numerical.audit(out/'numerical',full=True)
report.update(status='passed',full_numerical_recomputed=sys.argv[1]=='core-full')
(out/'receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
