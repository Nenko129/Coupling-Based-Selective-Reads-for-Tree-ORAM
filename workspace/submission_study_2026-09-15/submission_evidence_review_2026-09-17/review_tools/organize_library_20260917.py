"""Number user-supplied papers without altering PDF contents or old R01-R45 IDs."""
from pathlib import Path
import json,re,hashlib,shutil,subprocess
from pypdf import PdfReader
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path('D:/projects/SDE-R0')
BASE=ROOT/'TDSC_SOC3_审阅与投稿方案_2026-09-15'
PREP=BASE/'细化准备_2026-09-15'
LIB=PREP/'literature'
OUT=BASE/'投稿证据复核与文献整理_2026-09-17'
BACK=OUT/'文献整理前备份';BACK.mkdir(parents=True,exist_ok=True)
QA=OUT/'visual_review';QA.mkdir(exist_ok=True)
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in [LIB/'library_index.json',LIB/'download_manifest.json',LIB/'missing_references.json',LIB/'extra_references.json',PREP/'06_文献下载台账.md']:
 if not (BACK/p.name).exists():shutil.copy2(p,BACK/p.name)
idx=load(LIB/'library_index.json');refs=idx['references'];by={r['id']:r for r in refs}
incoming={
 'R16':'PageORAM_An_Efficient_DRAM_Page_Aware_ORAM_Strategy.pdf',
 'R17':'Hitchhiker_Accelerating_ORAM_With_Dynamic_Scheduling.pdf',
 'R24':'TianjiORAM.pdf','R25':'MP-ORAM.pdf',
 'R26':'PEO-Store_Delegation-Proof_Based_Oblivious_Storage_With_Secure_Redundancy_Elimination.pdf',
 'R27':'BOMAP_A_Round-Efficient_Construction_of_Oblivious_Maps.pdf','R43':'754-2019.pdf'}
pages={'R16':17,'R17':15,'R24':13,'R25':15,'R26':12,'R27':15,'R43':84}
rename_receipts=[]
for rid,oldname in incoming.items():
 r=by[rid];slug='_'.join(re.findall('[a-z0-9]+',r['title'].lower())[:8])
 old=LIB/'pdf'/oldname;new=LIB/'pdf'/f'{rid}_{slug}.pdf'
 p=old if old.exists() else new
 assert p.is_file(),p
 reader=PdfReader(p);first=reader.pages[0].extract_text() or '';last=reader.pages[-1].extract_text() or ''
 assert len(reader.pages)==pages[rid]
 if rid!='R43':assert r['doi'] in first,(rid,'DOI mismatch')
 else:assert '754' in first and '2019' in first
 before=sha(p)
 assert new.resolve().parent==(LIB/'pdf').resolve()
 if old.exists():
  assert not new.exists(),f'Will not overwrite {new}'
  old.rename(new)
 assert sha(new)==before
 r.update({'download_status':'downloaded','file':new.relative_to(PREP).as_posix(),'sha256':before,'pages':len(reader.pages),
  'acquisition_method':'user_supplied','original_supplied_filename':oldname,'download_url':None,
  'public_access_confirmed':False,'checked_on':'2026-09-17','local_full_text_available':True,
  'access_evidence':'用户补充本地全文；首页题名、DOI（IEEE标准为版号）、总页数及末页已核验。此记录不代表公开开放获取。',
  'version_note':'IEEE Std 754-2019 正式标准全文，84个PDF页。' if rid=='R43' else '用户提供的正式出版排版PDF；题名、DOI、卷期及首末页核验一致。',
  'download_version':'user-supplied publisher PDF',
  'reading_this_round':'2026-09-17核验书目身份、版本与首末页；不将取得全文计作整篇精读。',
  'first_page_excerpt':first[:1600], 'original_list_member':True})
 if rid=='R17':r['authors_display']='J. Zhu, M. Li, X. Zhang, K. Bu, M. Zhang, and T. Song'
 if rid=='R27':
  r['authors_display']='R. Wang, S. Lv, X. Li, H. Gong, Z. Liu, T. Li, and L. Guo'
  r['metadata_correction_note']='PDF列7位作者，补上原authors_display遗漏的Liang Guo。正式卷期2026，DOI内2025为早期在线年份线索，不替换卷期年。'
 if rid=='R26':r['name_order_note']='PDF首页印作Guo Jian；原出版注册/索引写法Jian Guo。此处保留现有规范化J. Guo，并记录拼写顺序差异；最终BibTeX以投稿书目规则与出版元数据核对。'
 rename_receipts.append({'id':rid,'old':str(old),'new':str(new),'sha256_before':before,'sha256_after':sha(new),'pages':len(reader.pages),'content_unchanged':True})

# rho is a central composition host but absent from the original 45-item bibliography.
rho_src=Path('C:/Users/12038/Desktop/for gpt/ro.pdf')
rho_dst=LIB/'pdf/X02_rho_relaxed_hierarchical_oram.pdf'
rho_hash='0f3d7fbda22f79a65096bf29146910fa3e56d2af4bd0dcbf5f589e55ac514b35'
assert sha(rho_src)==rho_hash
if not rho_dst.exists():shutil.copy2(rho_src,rho_dst)
assert sha(rho_dst)==rho_hash
rho={'id':'X02','title':'ρ: Relaxed Hierarchical ORAM','authors_display':'C. Nagarajan, A. Shafiee, R. Balasubramonian, and M. Tiwari',
 'authors_full':['Chandrasekhar Nagarajan','Ali Shafiee','Rajeev Balasubramonian','Mohit Tiwari'],
 'venue':'ASPLOS','year':2019,'volume_pages':'13 pages (author PDF; proceedings page range not inferred)',
 'doi':'10.1145/3297858.3304045','metadata_url':'https://doi.org/10.1145/3297858.3304045',
 'public_full_text_entry':'https://users.cs.utah.edu/~rajeev/pubs/asplos19.pdf',
 'access_class':'author-hosted public PDF','public_access_confirmed':True,
 'access_evidence':'2026-09-17在线打开作者主页PDF，13页，题名/作者/DOI与本地ro.pdf一致；本次文件从本地候选库复制。',
 'download_status':'downloaded','download_url':None,'acquisition_method':'copied_from_existing_local_candidate',
 'original_supplied_filename':str(rho_src),'file':rho_dst.relative_to(PREP).as_posix(),'sha256':rho_hash,'pages':13,
 'original_list_member':False,'checked_on':'2026-09-17','local_full_text_available':True,
 'version_note':'作者主页公开的ASPLOS 2019排版稿；另编号X02，保留原R01–R45。',
 'reading_this_round':'补入组合宿主正式书目；核对首页书目信息与§3.3确定性调度相关内容。',
 'paper_role':'ρ-style组合宿主、双层ORAM与时间泄漏边界','proposed_outline_sections':['Related Work','Composability','Evaluation']}
if 'X02' not in by:refs.append(rho)
else:by['X02'].update(rho)
extra=load(LIB/'extra_references.json')
if not any(r['id']=='X02' for r in extra):extra.append(rho)
checks=[]
for r in refs:
 p=PREP/r['file'];assert p.is_file(),(r['id'],p)
 h=sha(p);assert h==r['sha256'],(r['id'],'hash mismatch')
 n=len(PdfReader(p).pages) if p.suffix.lower()=='.pdf' else None
 if n is not None:assert n==r['pages'],(r['id'],'page count mismatch')
 checks.append({'id':r['id'],'file':str(p),'sha256':h,'pages':n,'status':'verified'})
original=[r for r in refs if re.fullmatch(r'R\d{2}',r['id'])]
assert len(original)==45
summary=dict(idx.get('summary',{}))
summary.update({'original_items':45,'original_pdf':43,'original_text':2,'original_full_text':45,'original_full_text_items':45,'original_missing':[],
 'extra_pdf':3,'all_verified_files':48,'user_supplied_added':7,'publicly_acquired_original_full_text':38,
 'local_completeness_is_not_public_access':True})
idx.update({'date':'2026-09-17','summary':summary,'references':refs})
write(LIB/'library_index.json',idx)
dm=load(LIB/'download_manifest.json');dm['checked_on']='2026-09-17'
for i,r in enumerate(dm['references']):
 if r['id'] in incoming:dm['references'][i]={**r,**by[r['id']]}
if not any(r['id']=='X02' for r in dm['references']):dm['references'].append(rho)
write(LIB/'download_manifest.json',dm);write(LIB/'extra_references.json',extra);write(LIB/'missing_references.json',[])

lines=['# 文献下载与阅读台账','', '更新：2026-09-17。原45项已取得 **45/45项全文：43份PDF、2份官方RFC文本**。另有R26-preprint、X01 SONIC和X02 ρ三份补充PDF，合计48个全文文件。', '',
 '本次新增的7份全文由用户提供，不计为新找到的公开开放获取论文。所有文件重新校验SHA-256和可解析性；取得全文不代表完成整篇精读。原R01–R45编号保持不变。','',
 '## 原45项','', '| ID | 题名 | 年份／出处 | 本地全文 | 版本与阅读状态 |','|---|---|---|---|---|']
for r in original:
 p=(PREP/r['file']).as_posix();label=f"PDF {r.get('pages')}页" if p.lower().endswith('.pdf') else 'RFC全文TXT'
 title=r['title'].replace('|','/')
 note=(r.get('version_note','')+' '+r.get('reading_this_round','')).replace('\n',' ').replace('|','/')
 lines.append(f"| {r['id']} | {title} | {r.get('year','')} · {r.get('venue','')} | [{label}](<{p}>) | {note} |")
lines+=['','## 补充全文（不占原45项编号）','']
for r in refs:
 if r in original:continue
 lines += [f"- **{r['id']}** · {r['title']}： [本地全文](<{(PREP/r['file']).as_posix()}>)。{r.get('version_note','')}"]
lines += ['','## 本次书目核对','',
 '- 已补齐R16 PageORAM、R17 Hitchhiker、R24 Tianji、R25 MP-ORAM、R26 PEO-Store正式版、R27 BOMAP、R43 IEEE 754-2019。七份PDF仅重命名，文件字节和哈希完全不变。',
 '- R27 BOMAP首页列7位作者，补上旧显示列表遗漏的Liang Guo。正式卷期是TDSC 23(1), 221–235, 2026；不要把DOI中的2025误作卷期年份。',
 '- R26正式版（12页）与R26-preprint早期稿（25页）分开保存，不混淆题名或版本。正式PDF印作Guo Jian，注册/索引规范化为Jian Guo；保留现有J. Guo并记录差异。',
 '- X02 ρ原本不在45项列表中，但已是主要组合宿主，因此补入。作者公开全文：[ASPLOS 2019 PDF](https://users.cs.utah.edu/~rajeev/pubs/asplos19.pdf)。',
 '- R43是2019正式标准（84个PDF页），不是2008版；R44/R45仍保留官方RFC文本格式。',
 '- R29原始入口误指Ascend的问题已在现有library_index修正；本次保持修正。R22作者稿、R36 ePrint长稿与出版版页数不同，继续保留版本说明。',
 '- 库内编号是稳定资料编号；论文中的参考文献序号应由LaTeX/Word按实际引用顺序生成，不能把R编号直接当作投稿最终编号。',
 '', '当前需要你继续下载的原45项文献：**无**。', '',
 '元数据及文件哈希见 `literature/library_index.json`；原始获取尝试保留在 `download_manifest.json`。整理前台账及索引备份保存在上级的 `投稿证据复核与文献整理_2026-09-17/文献整理前备份`。']
(PREP/'06_文献下载台账.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
write(OUT/'literature_organization_receipts.json',{'checked_on':'2026-09-17','renames':rename_receipts,'added_rho':rho,'summary':summary,'all_file_checks':checks})

# Render first/last pages of the seven supplied PDFs and rho for identity review.
poppler=Path('C:/Users/12038/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
contact=Image.new('RGB',(1280,8*330),'#e5e7eb');draw=ImageDraw.Draw(contact)
for i,rid in enumerate([*incoming,'X02']):
 r=by.get(rid,rho);p=PREP/r['file']
 for j,page in enumerate([1,r['pages']]):
  prefix=QA/f'{rid}_{"first" if j==0 else "last"}'
  subprocess.run([str(poppler),'-f',str(page),'-l',str(page),'-singlefile','-scale-to','850','-png',str(p),str(prefix)],check=True,capture_output=True)
  im=Image.open(prefix.with_suffix('.png')).convert('RGB');im.thumbnail((600,286))
  x=j*640+(640-im.width)//2;y=i*330+30
  contact.paste(im,(x,y));draw.text((j*640+12,i*330+5),f'{rid} | {"first" if j==0 else "last"} page',font=font,fill='#111827')
contact.save(QA/'literature_contact.png')
print(json.dumps({'summary':summary,'renamed':[(r['id'],Path(r['new']).name) for r in rename_receipts],'added':'X02','all_files_verified':len(checks)},ensure_ascii=False))
