"""Independently recompute exported period-window values from original bills."""
from common import *
import math,statistics
from pypdf import PdfReader


def close(a,b):assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10),(a,b)


def main():
    source=PACKAGE/'results/ir_periodic_statistics.json';stats=json.loads(source.read_text())
    receipt_path=PACKAGE/'results/ir_periodic_exports.json';receipt=json.loads(receipt_path.read_text())
    assert receipt['source_sha256']==sha(source)
    assert receipt['generator_sha256']==sha(Path(__file__).parent/'render_ir_periodic.py')
    for item in receipt['outputs']:assert sha(PACKAGE/item['path'])==item['sha256']
    data=json.loads((PACKAGE/'figures/completed_ir_periodic_data.json').read_text());assert data['source_sha256']==sha(source)
    records={}
    for item in stats['receipts']:
        p=PACKAGE/item['path'];assert sha(p)==item['sha256'];records[item['id']]=json.loads(p.read_text())
    assert len(data['runs'])==len(records)==60
    assert {r['spec']['id'] for r in data['runs']}==set(records)
    for row in data['runs']:
        r=records[row['spec']['id']];s=r['spec'];m=r['phases']['measurement']
        assert row['spec']==s and row['measurement']==m
        assert sha(PACKAGE/row['source']['path'])==row['source']['sha256']
        assert m['public_slots']==49152 and s['requests']==6144 and s['warmup']==1536
        assert m['total_bytes']==sum(sum(b['components'].values()) for b in m['bills'])
        assert m['rpc']==sum(b['rpc'] for b in m['bills'])
        close(row['bytes_per_request'],m['total_bytes']/s['requests'])
    assert data['effects']==stats['effects'] and len(data['plotted'])==len(data['effects'])==14
    keys=set()
    for item in data['plotted']:
        key=(item['axis'],tuple(item['condition']),item['before'],item['after']);assert key not in keys;keys.add(key)
        e=next(e for e in stats['effects'] if (e['axis'],tuple(e['condition']),e['before'],e['after'])==key)
        assert item['effect']==e['effect'] and item['pairs']==e['per_seed']
        values=[];left=[];right=[]
        assert len(e['per_seed'])==5
        for pair in e['per_seed']:
            a=records[pair['baseline_id']];b=records[pair['variant_id']];sa=a['spec'];sb=b['spec']
            assert sa['trace_seed']==sb['trace_seed']
            field='kind' if e['axis']=='backend' else 'dwb'
            assert sa[field]==e['before'] and sb[field]==e['after']
            assert sa['layout']==sb['layout']=='depth' and sa['workload']==sb['workload']==e['condition'][2]
            if e['axis']=='backend':assert sa['dwb']==sb['dwb']==e['condition'][1]
            else:assert sa['kind']==sb['kind']==e['condition'][1]
            av=a['phases']['measurement']['total_bytes']/sa['requests'];bv=b['phases']['measurement']['total_bytes']/sb['requests']
            values.append(100*(1-bv/av));left.append(av);right.append(bv)
        assert len({records[p['baseline_id']]['spec']['trace_seed'] for p in e['per_seed']})==5
        mean=statistics.mean(values);half=2.7764451051977987*statistics.stdev(values)/math.sqrt(5)
        close(mean,e['effect']['mean']);close(mean-half,e['effect']['ci95'][0]);close(mean+half,e['effect']['ci95'][1])
        close(statistics.mean(left),e['baseline_mean_bytes']);close(statistics.mean(right),e['variant_mean_bytes'])
    pdf=PACKAGE/'output/pdf/completed_ir_periodic.pdf';reader=PdfReader(pdf);assert len(reader.pages)==1
    page=reader.pages[0];txt=page.extract_text()
    assert all(s in txt for s in ('complete-period','6,144','49,152','Path','Deferred','IR-Stash','95%'))
    assert not list(page.images) and page['/Resources']['/Font']
    for font in page['/Resources']['/Font'].values():
        f=font.get_object()
        for desc in f.get('/DescendantFonts',[f]):
            descriptor=desc.get_object()['/FontDescriptor'].get_object()
            assert any(k in descriptor for k in ('/FontFile','/FontFile2','/FontFile3'))
    save(PACKAGE/'results/ir_periodic_exports_audit.json',dict(status='passed',runs=60,comparisons=14,
        source_sha256=sha(source),export_receipt_sha256=sha(receipt_path),checker_sha256=sha(__file__),
        pdf_sha256=sha(pdf),pages=1,vector_content=True,embedded_fonts=True,visual_review_separate=True))
    print(json.dumps(dict(status='passed',runs=60,comparisons=14,pdfs=1)))


if __name__=='__main__':main()
