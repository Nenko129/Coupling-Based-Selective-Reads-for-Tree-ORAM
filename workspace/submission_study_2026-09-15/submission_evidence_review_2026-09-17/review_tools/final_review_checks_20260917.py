from pathlib import Path
import json,re,subprocess,hashlib,shutil
from pypdf import PdfReader
from PIL import Image,ImageDraw
B=Path('D:/projects/SDE-R0/TDSC_SOC3_审阅与投稿方案_2026-09-15')
O=B/'投稿证据复核与文献整理_2026-09-17';L=B/'细化准备_2026-09-15/literature';P=L.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def norm(s):return re.sub('[^a-z0-9]','',s.lower().replace('ﬁ','fi').replace('ﬂ','fl').replace('ρ','rho'))
rows=[]
for r in load(L/'library_index.json')['references']:
 f=P/r['file']
 if f.suffix!='.pdf':continue
 pdf=PdfReader(f);text=' '.join(pdf.pages[i].extract_text() or '' for i in range(min(2,len(pdf.pages))));words=re.findall('[a-z0-9]+',r['title'].lower())
 words=[w for w in words if len(w)>2 and w not in ['the','and','for','with','from','into','via']]
 overlap=sum(norm(w) in norm(text) for w in words)/len(words) if words else 1
 rows.append({'id':r['id'],'title':r['title'],'title_token_overlap_first_two_pages':overlap,'doi_in_first_two_pages':r.get('doi') in text if r.get('doi') else None,'pages':len(pdf.pages)})
suspects=[r for r in rows if r['title_token_overlap_first_two_pages']<.6]
(O/'bibliographic_identity_screen.json').write_text(json.dumps({'method':'title-token screen of first two PDF pages; absent DOI in an author version is not automatically an error','screened_pdf_count':len(rows),'needs_manual_identity_review':suspects,'rows':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
poppler='C:/Users/12038/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
ims=[]
for p in (O/'写作修订稿/figures').glob('*.pdf'):
 assert len(PdfReader(p).pages)==1
 prefix=O/'visual_review'/('rendered_'+p.stem)
 subprocess.run([poppler,'-singlefile','-scale-to','1200','-png',str(p),str(prefix)],check=True,capture_output=True)
 im=Image.open(prefix.with_suffix('.png')).convert('RGB');ims.append(im)
contact=Image.new('RGB',(max(i.width for i in ims),sum(i.height for i in ims)+30*len(ims)),'white');y=0
for im in ims:contact.paste(im,(0,y));y+=im.height+30
contact.save(O/'visual_review/final_pdf_figures.png')
shutil.copy2(Path('D:/projects/SDE-R0/tmp/prepare_review_figures_20260917.py'),O/'review_tools/prepare_review_figures_20260917.py')
shutil.copy2(Path(__file__),O/'review_tools'/Path(__file__).name)
# A manifest for the review addendum itself; exclude backups and visual contact sheets.
files=[]
for p in sorted(O.rglob('*')):
 if p.is_file() and not any(x in p.parts for x in ['文献整理前备份','visual_review']) and p.name!='review_addendum_manifest.json':
  files.append({'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'review_addendum_manifest.json').write_text(json.dumps({'checked_on':'2026-09-17','scope':'review addendum; frozen experiment bundle unchanged','files':files},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pdfs_screened':len(rows),'identity_flags':suspects,'review_manifest_files':len(files),'missing_original_references':load(L/'missing_references.json')},ensure_ascii=False))
