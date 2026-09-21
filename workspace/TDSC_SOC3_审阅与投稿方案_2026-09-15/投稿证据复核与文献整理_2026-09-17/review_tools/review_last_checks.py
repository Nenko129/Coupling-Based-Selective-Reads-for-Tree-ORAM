from pathlib import Path
import json,zipfile,math,hashlib
from fractions import Fraction
R=Path('D:/projects/SDE-R0')
B=R/'TDSC_SOC3_审阅与投稿方案_2026-09-15'
P=B/'Selective_通用组合与投稿实验准备_2026-09-16/论文实验章节完整证据_2026-09-16'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
m=load(P/'evidence_manifest.json')
for row in m['files']:
 if row['type']=='portable_bundle':
  print('PORTABLE',row)
  with zipfile.ZipFile(P/row['copy']) as z:
   print('ZIP',len(z.namelist()),'MANIFESTS',[s for s in z.namelist() if 'manifest' in s.lower()])
   for s in z.namelist():
    if s.lower().endswith('manifest.json'):
     v=json.loads(z.read(s));print('MANIFEST',s,str(v)[:1000])
c=load(P/'source_evidence/audits/minimal__capacity_binding.json')
bound=Fraction(c['lifetime_bound_exact']);log=math.log2(bound.numerator)-math.log2(bound.denominator)
grid=[]
for g in c['grids']:
 for rel,h in g['files'].items():
  p=R/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==h
  if p.suffix=='.csv':
   lines=sum(1 for _ in p.open(encoding='utf-8-sig'))-1
   print('GRID',p.name,'data_rows',lines,'declared_rows',g['rows']);grid.append({'file':str(p),'rows':lines,'sha256':h})
print('BOUND',log,'target_pass',bound < Fraction(1,2**132),'bound_specs',c['new_specs_bound'])
out={'grid_checks':grid,'log2_lifetime_bound':log,'below_2_pow_minus_132':bound < Fraction(1,2**132),'scope':c['scope'],'new_specs_bound':c['new_specs_bound']}
(B/'投稿证据复核与文献整理_2026-09-17/capacity_binding_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ['eval__tuned_model_window_audit.json','minimal__minimal_contract_checks.json','minimal__frontend_reset_checks.json','minimal__public_selector_checks.json']:
 v=load(P/'source_evidence/audits'/name);print('AUDIT_KEYS',name,list(v))
 if 'window' in name:print('WINDOW_FIELDS',str({k:v for k,v in v.items() if k not in ['cells']})[-3500:])
