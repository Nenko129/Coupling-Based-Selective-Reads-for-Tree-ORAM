"""Recompute all plotted means and intervals directly from source receipts."""
from common import *
import math,statistics
from pypdf import PdfReader


def close(a,b):assert math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-8),(a,b)


def main():
    p=PACKAGE/'results/core_components_complete_audit.json';a=json.loads(p.read_text())
    export_path=PACKAGE/'results/core_components_exports.json';export=json.loads(export_path.read_text())
    assert export['source_sha256']==sha(p)
    assert export['generator_sha256']==sha(Path(__file__).parent/'render_completed_core.py')
    for x in export['outputs']:assert sha(PACKAGE/x['path'])==x['sha256']
    dp=PACKAGE/'figures/completed_core_components_data.json';assert sha(dp)==export['data_sha256']
    data=json.loads(dp.read_text());assert data['source_sha256']==sha(p) and len(data['series'])==30
    rows={}
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];rows[ref['id']]=json.loads(p.read_text())
    for point in data['series']:
        values=[]
        for ids in point['ids']:
            if point['metric']=='bytes_per_request':
                row=rows[ids];values.append(row['phases']['measurement']['total_bytes']/row['spec']['requests'])
            else:
                left,right=[rows[x] for x in ids]
                assert left['trace']==right['trace'] and left['spec']['requests']==right['spec']['requests']
                values.append(100*(1-right['phases']['measurement']['total_bytes']/left['phases']['measurement']['total_bytes']))
        assert len(values)==5
        for x,y in zip(values,point['values']):close(x,y)
        mean=statistics.mean(values);half=2.7764451051977987*statistics.stdev(values)/math.sqrt(5)
        close(mean,point['mean']);close(mean-half,point['ci95'][0]);close(mean+half,point['ci95'][1])
    pdfs=[]
    for name,tokens in [('completed_core_bandwidth',['16,384','4,096','95%','Z4/A3/S3','separately tuned']),
                        ('completed_static_components',['4,096','95%','IR-Stash/DWB','CB/DeadQ','R480','R256'])]:
        p=PACKAGE/'output/pdf'/f'{name}.pdf';reader=PdfReader(p);assert len(reader.pages)==1
        page=reader.pages[0];txt=page.extract_text();assert all(x in txt for x in tokens),(name,txt)
        assert '\\n' not in txt and not list(page.images) and page['/Resources']['/Font']
        for font in page['/Resources']['/Font'].values():
            f=font.get_object()
            for d in f.get('/DescendantFonts',[f]):
                fd=d.get_object()['/FontDescriptor'].get_object()
                assert any(k in fd for k in ('/FontFile','/FontFile2','/FontFile3'))
        pdfs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p),pages=1,vector=True,embedded_fonts=True))
    save(PACKAGE/'results/core_components_exports_audit.json',dict(status='passed',series_recomputed=30,raw_records=140,
        export_receipt_sha256=sha(export_path),checker_sha256=sha(__file__),pdfs=pdfs,visual_review='separate render inspection required'))
    print(json.dumps(dict(status='passed',series=30,raw_records=140,vector_pdfs=2)))


if __name__=='__main__':main()
