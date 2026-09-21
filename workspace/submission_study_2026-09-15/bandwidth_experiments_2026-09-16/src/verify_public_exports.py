"""Recompute public export data, preserving the preselected-window estimand."""
from common import *
import math,statistics
from pypdf import PdfReader


def close(x,y):assert math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-10),(x,y)


def main():
    source=PACKAGE/'results/public_completed_audit.json';s=json.loads(source.read_text())
    ep=PACKAGE/'results/public_exports.json';e=json.loads(ep.read_text());assert e['source_sha256']==sha(source)
    assert s['auditor_sha256']==sha(Path(__file__).parent/'audit_completed_public.py')
    assert e['generator_sha256']==sha(Path(__file__).parent/'render_completed_public.py')
    for item in e['outputs']:assert sha(PACKAGE/item['path'])==item['sha256']
    dp=PACKAGE/'figures/completed_public_workloads_data.json';data=json.loads(dp.read_text())
    assert data['source_sha256']==sha(source) and data['effects']==s['effects'] and data['cells']==s['cells'] and data['windows']==s['windows']
    records={}
    for row in data['runs']:
        item=row['source'];p=PACKAGE/item['path'];assert sha(p)==item['sha256'];r=json.loads(p.read_text())
        assert row['spec']==r['spec'] and row['measurement']==r['phases']['measurement']
        for k in ('trace','configs','server_storage','frontend_memory_representation','scope'):assert row[k]==r[k]
        close(row['bytes_per_request'],r['phases']['measurement']['total_bytes']/4096)
        close(row['rpc_per_request'],r['phases']['measurement']['rpc']/4096)
        assert r['spec']['id'] not in records;records[r['spec']['id']]=r
    assert len(records)==80 and len(data['cells'])==16 and len(data['effects'])==8
    for c in data['cells']:
        assert c['n']==5 and len(c['ids'])==5
        rs=[records[k] for k in c['ids']]
        assert all((r['spec']['family'],r['spec']['workload'],r['spec']['kind'])==(c['family'],c['workload'],c['kind']) for r in rs)
        assert {r['spec']['trace_seed'] for r in rs}==set(range(101,106))
        vals=[r['phases']['measurement']['total_bytes']/4096 for r in rs]
        close(c['mean'],statistics.mean(vals));assert c['range']==[min(vals),max(vals)]
    used=set()
    for effect in data['effects']:
        key=tuple(effect[k] for k in ('family','workload','baseline','variant'));assert key not in used;used.add(key)
        vals=[];left=[];right=[]
        assert effect['n']==5 and effect['ci95'] is None
        assert [p['seed'] for p in effect['per_window']]==list(range(101,106))
        for p in effect['per_window']:
            a=records[p['baseline_id']];b=records[p['variant_id']]
            assert a['trace']==b['trace'] and a['answer_sha256']==b['answer_sha256']
            assert (a['spec']['family'],a['spec']['workload'],a['spec']['kind'],b['spec']['kind'])==key
            av=a['phases']['measurement']['total_bytes']/4096;bv=b['phases']['measurement']['total_bytes']/4096
            v=100*(1-bv/av);close(v,p['saving_pct']);vals.append(v);left.append(av);right.append(bv)
            if effect['family']=='rho':
                aa=a['phases']['measurement']['bills'];bb=b['phases']['measurement']['bills'];front=aa[0]['total_bytes'];back=aa[1]['total_bytes']
                assert front==bb[0]['total_bytes']
                close(p['front_bytes'],front/4096);close(p['backend_share'],back/(front+back))
                close(p['backend_saving_pct'],100*(1-bb[1]['total_bytes']/back))
                close(p['saving_pct'],p['backend_share']*p['backend_saving_pct'])
        close(effect['mean'],statistics.mean(vals));assert effect['range']==[min(vals),max(vals)]
        close(effect['baseline_mean'],statistics.mean(left));close(effect['variant_mean'],statistics.mean(right))
    pdf=PACKAGE/'output/pdf/completed_public_workloads.pdf';reader=PdfReader(pdf);assert len(reader.pages)==1
    page=reader.pages[0];text=page.extract_text();assert all(x in text for x in ('Financial1','WebSearch1','16,384','min-max','not confidence intervals'))
    assert not list(page.images) and page['/Resources']['/Font']
    for font in page['/Resources']['/Font'].values():
        f=font.get_object()
        for desc in f.get('/DescendantFonts',[f]):
            descriptor=desc.get_object()['/FontDescriptor'].get_object()
            assert any(k in descriptor for k in ('/FontFile','/FontFile2','/FontFile3'))
    save(PACKAGE/'results/public_exports_audit.json',dict(status='passed',runs=80,comparisons=8,cells=16,paired_windows=40,
        source_sha256=sha(source),export_receipt_sha256=sha(ep),checker_sha256=sha(__file__),pdf_sha256=sha(pdf),
        pages=1,vector_content=True,embedded_fonts=True,window_range_not_confidence_interval=True,visual_review_separate=True))
    print(json.dumps(dict(status='passed',runs=80,comparisons=8,pdfs=1)))


if __name__=='__main__':main()
