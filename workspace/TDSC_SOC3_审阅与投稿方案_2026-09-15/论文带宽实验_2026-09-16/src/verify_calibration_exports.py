"""Reopen exported tables/PDF and independently check numerical agreement."""
from common import *
import csv,math,statistics
from pypdf import PdfReader


def same(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-10),(a,b)


def main():
    snap=PACKAGE/'results/calibration_completed_snapshot.json';s=json.loads(snap.read_text())
    receipt=json.loads((PACKAGE/'results/calibration_exports.json').read_text());assert receipt['source_snapshot_sha256']==sha(snap)
    for x in receipt['outputs']:assert sha(PACKAGE/x['path'])==x['sha256']
    def read(name):
        with (PACKAGE/'tables'/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    raw=read('Calibration_40_runs.csv');groups=read('Calibration_8_configurations.csv')
    assert len(raw)==40 and len(groups)==8 and len({x['id'] for x in raw})==40
    for x in raw:
        p=PACKAGE/x['source_path'];assert sha(p)==x['source_sha256'];r=json.loads(p.read_text())
        actual=r['phases']['measurement']['total_bytes']/r['spec']['requests']
        same(x['actual_bytes_per_request'],actual);same(x['model_relative_error_pct'],100*(actual/float(x['model_bytes_per_request'])-1))
        assert x['id']==r['spec']['id'] and int(x['seed'])==r['spec']['trace_seed']
    for g in groups:
        rs=[r for r in raw if all(r[k]==g[k] for k in ('kind','Z','A','S'))]
        assert len(rs)==5 and {int(r['seed']) for r in rs}==set(range(101,106)) and g['source_snapshot_sha256']==sha(snap)
        for key,mean_key,low,high in [('actual_bytes_per_request','actual_mean_bytes','actual_ci95_lower','actual_ci95_upper'),
            ('model_relative_error_pct','mean_error_pct','error_ci95_lower','error_ci95_upper')]:
            vals=[float(r[key]) for r in rs];mean=sum(vals)/5;half=2.7764451051977987*statistics.stdev(vals)/math.sqrt(5)
            same(g[mean_key],mean);same(g[low],mean-half);same(g[high],mean+half)
    p=PACKAGE/'figures/completed_model_calibration.pdf';pdf=PdfReader(p);assert len(pdf.pages)==1;page=pdf.pages[0]
    text=page.extract_text();assert all(x in text for x in ('N = 256','64 B','Path','Deferred','SDE','Ring','GC-Ring','R0','95%'))
    assert not list(page.images)
    for font in page['/Resources']['/Font'].values():
        font=font.get_object()
        for descendant in font.get('/DescendantFonts',[font]):
            d=descendant.get_object()['/FontDescriptor'].get_object();assert any(k in d for k in ('/FontFile','/FontFile2','/FontFile3'))
    save(PACKAGE/'results/calibration_exports_audit.json',dict(status='passed',raw_rows=40,groups=8,pdf_pages=1,fonts_embedded=True,vector_content=True,
        snapshot_sha256=sha(snap),pdf_sha256=sha(p),checker_sha256=sha(__file__),export_receipt_sha256=sha(PACKAGE/'results/calibration_exports.json')))
    print(json.dumps(dict(status='passed',raw_rows=40,groups=8,pdf_pages=1)))


if __name__=='__main__':main()
