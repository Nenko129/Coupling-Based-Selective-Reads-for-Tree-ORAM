"""Read-only numerical and PDF audit of the completed finite-prefix exports."""
from common import *
import csv,math,statistics
from pypdf import PdfReader


def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-10),(a,b)


def main():
    source=PACKAGE/'results/ir_dwb_statistics.json';stats=json.loads(source.read_text())
    receipt=json.loads((PACKAGE/'figures/ir_integrated_finite_receipt.json').read_text())
    assert receipt['source_sha256']==sha(source)
    for item in receipt['outputs']:assert sha(PACKAGE/item['path'])==item['sha256']
    records={}
    for item in stats['receipts']:
        p=PACKAGE/item['path'];assert sha(p)==item['sha256'];records[item['id']]=json.loads(p.read_text())
    with (PACKAGE/'tables/IR_DWB_120_runs.csv').open(encoding='utf-8-sig',newline='') as f:raw=list(csv.DictReader(f))
    assert len(raw)==120 and {r['id'] for r in raw}==set(records)
    for row in raw:
        r=records[row['id']];s=r['spec'];m=r['phases']['measurement'];b=m['bills'][0]
        assert sha(PACKAGE/row['source_path'])==row['source_sha256']
        for key in ('total_bytes','public_slots','rpc'):close(row[key],m[key])
        close(row['bytes_per_request'],b['total_bytes']/s['requests'])
        for key,value in s.items():
            if key in row:assert row[key]==str(value)
        for key,value in b['components'].items():close(row['bytes_'+key],value)
        for key in ('foreground_slots','foreground_writebacks','foreground_posmap_slots','dwb_completed','dwb_posmap_slots','dummy_slots','dirty_resident'):
            close(row[key],m['frontend_metrics'].get(key,0))
    with (PACKAGE/'tables/IR_DWB_40_comparisons.csv').open(encoding='utf-8-sig',newline='') as f:effects=list(csv.DictReader(f))
    assert len(effects)==len(stats['effects'])==40
    for row,e in zip(effects,stats['effects']):
        assert (row['axis'],row['baseline'],row['variant'])==(e['axis'],str(e['before']),str(e['after']))
        assert [row['condition_1'],row['condition_2'],row['workload']]==list(map(str,e['condition']))
        assert row['source_sha256']==sha(source) and int(row['n'])==5
        values=[];left=[];right=[]
        for pair in e['per_seed']:
            a=records[pair['baseline_id']];b=records[pair['variant_id']]
            av=a['phases']['measurement']['total_bytes']/a['spec']['requests']
            bv=b['phases']['measurement']['total_bytes']/b['spec']['requests']
            values.append(100*(1-bv/av));left.append(av);right.append(bv)
        mean=statistics.mean(values);half=2.7764451051977987*statistics.stdev(values)/math.sqrt(5)
        for key,value in dict(saving_pct=mean,ci95_lower=mean-half,ci95_upper=mean+half,
            baseline_bytes_per_request=statistics.mean(left),variant_bytes_per_request=statistics.mean(right)).items():close(row[key],value)
    pdfs=[]
    for stem in ('ir_integrated_finite_gain','ir_integrated_finite_breakdown'):
        p=PACKAGE/'figures'/f'{stem}.pdf';reader=PdfReader(p);assert len(reader.pages)==1
        page=reader.pages[0];text=page.extract_text();assert all(x in text for x in ('FINITE PREFIX','64 B','Path','Deferred','SDE'))
        assert page['/Resources']['/Font'];assert not list(page.images)
        for font in page['/Resources']['/Font'].values():
            font=font.get_object();descendants=font.get('/DescendantFonts',[font])
            for descendant in descendants:
                descriptor=descendant.get_object()['/FontDescriptor'].get_object()
                assert any(key in descriptor for key in ('/FontFile','/FontFile2','/FontFile3'))
        pdfs.append(dict(path=str(p.relative_to(PACKAGE)),sha256=sha(p),pages=1,vector_content=True,embedded_font_resources=True))
    save(PACKAGE/'results/ir_finite_exports_audit.json',dict(status='passed',raw_rows=120,comparisons_recomputed=40,
        source_sha256=sha(source),generator_receipt_sha256=sha(PACKAGE/'figures/ir_integrated_finite_receipt.json'),
        checker_sha256=sha(__file__),pdfs=pdfs,visual_review='separate human/model inspection receipt; not inferred from numerical tests'))
    print(json.dumps(dict(status='passed',raw_rows=120,comparisons=40,pdfs=2)))


if __name__=='__main__':main()
