"""Independent raw-number and vector-PDF verification for completed B2."""
from common import *
import math,statistics
from pypdf import PdfReader

def close(x,y):assert math.isclose(x,y,rel_tol=1e-11,abs_tol=1e-8),(x,y)
def main():
    src=PACKAGE/'results/ablation_complete_audit.json';a=json.loads(src.read_text())
    receipt_path=PACKAGE/'results/ablation_exports.json';receipt=json.loads(receipt_path.read_text())
    assert receipt['source_sha256']==sha(src)
    for x in receipt['outputs']:assert sha(PACKAGE/x['path'])==x['sha256']
    data=PACKAGE/'figures/completed_r0_ablation_data.json';assert sha(data)==receipt['data_sha256']
    chart=json.loads(data.read_text());assert chart['source_sha256']==sha(src) and len(chart['bars'])==16
    rows={}
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];rows[ref['id']]=json.loads(p.read_text())
    pairs={'compact_without_fusion_pct':('00','10'),'compact_with_fusion_pct':('01','11'),
           'fusion_without_compact_pct':('00','01'),'fusion_with_compact_pct':('10','11')}
    for b in chart['bars']:
        if b['panel']=='conditional':
            x,y=pairs[b['effect']];before=f"{b['family']}_cf{x}";after=f"{b['family']}_cf{y}"
        else:before,after=b['before'],b['after']
        key='total_bytes' if b['metric']=='bytes_saving' else 'rpc';values=[]
        for seed in range(101,106):
            left=rows[f'B2_R0_{before}_seed{seed}']['phases']['measurement'][key]
            right=rows[f'B2_R0_{after}_seed{seed}']['phases']['measurement'][key]
            values.append(100*(1-right/left))
        mean=statistics.mean(values);half=2.7764451051977987*statistics.stdev(values)/math.sqrt(5)
        close(mean,b['mean']);close(mean-half,b['ci95'][0]);close(mean+half,b['ci95'][1])
    p=PACKAGE/'output/pdf/completed_r0_ablation.pdf';reader=PdfReader(p);assert len(reader.pages)==1
    page=reader.pages[0];txt=page.extract_text()
    assert all(x in txt for x in ('16,384','4,096','95%','RPC','fusion','geometry'))
    assert '\\n' not in txt and '\\header' not in txt
    assert not list(page.images) and page['/Resources']['/Font']
    for f in page['/Resources']['/Font'].values():
        f=f.get_object()
        for d in f.get('/DescendantFonts',[f]):
            fd=d.get_object()['/FontDescriptor'].get_object()
            assert any(k in fd for k in ('/FontFile','/FontFile2','/FontFile3'))
    report=PACKAGE/'34_R0完整消融结果.md';text=report.read_text(encoding='utf-8')
    assert sum(line.startswith('| B2_R0_') for line in text.splitlines())==45
    save(PACKAGE/'results/ablation_exports_audit.json',dict(status='passed',raw_records=45,bars_recomputed=16,pdf_pages=1,
        pdf_sha256=sha(p),vector_content=True,embedded_fonts=True,source_sha256=sha(src),export_receipt_sha256=sha(receipt_path),
        checker_sha256=sha(__file__),visual_review='separate render inspection required'))
    print(json.dumps(dict(status='passed',bars=16,raw_records=45,vector_pdf=True)))

if __name__=='__main__':main()

