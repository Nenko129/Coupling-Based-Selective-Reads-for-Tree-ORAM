"""Check figure values against raw bills and vector/font properties."""
from common import *
from pypdf import PdfReader
from verify_free_sensitivity_tables import check_stat


def main():
    source=PACKAGE/'results/free_sensitivity_completed_audit.json';a=json.loads(source.read_text(encoding='utf-8'))
    ep=PACKAGE/'results/free_sensitivity_exports.json';e=json.loads(ep.read_text(encoding='utf-8'))
    dp=PACKAGE/'figures/completed_free_sensitivity_data.json';d=json.loads(dp.read_text(encoding='utf-8'))
    assert e['source_sha256']==d['source_sha256']==sha(source)
    assert e['generator_sha256']==sha(Path(__file__).parent/'render_free_sensitivity.py')
    assert e['data_sha256']==sha(dp) and e['tables_audit_sha256']==sha(PACKAGE/'results/free_sensitivity_tables_audit.json')
    for ref in e['outputs']:assert sha(PACKAGE/ref['path'])==ref['sha256']
    records={}
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];records[ref['id']]=json.loads(p.read_text(encoding='utf-8'))
    assert len(records)==160 and len(d['series'])==32 and d['absolute_scale']==1024
    for s in d['series']:
        values=[];seeds=[]
        for ids in s['ids']:
            if s['panel']=='absolute':
                r=records[ids];sp=r['spec'];m=r['phases']['measurement'];seeds.append(sp['trace_seed'])
                assert sp['kind']==s['kind'];values.append(m['total_bytes']/m['requests'])
                key='/'.join((sp['family'],sp['workload'],sp.get('condition','B64_base')))
            else:
                l,r=[records[i] for i in ids];sp=l['spec'];seeds.append(sp['trace_seed'])
                assert l['trace']==r['trace'] and l['answer_sha256']==r['answer_sha256']
                assert (sp['kind'],r['spec']['kind'])==(s['baseline'],s['variant'])
                assert sp['trace_seed']==r['spec']['trace_seed']
                key='/'.join((sp['family'],sp['workload'],sp.get('condition','B64_base')))
                values.append(100*(1-r['phases']['measurement']['total_bytes']/l['phases']['measurement']['total_bytes']))
            assert key==s['configuration']
        assert seeds==list(range(101,106));check_stat(s,values)
    pdf=PACKAGE/'output/pdf/completed_free_sensitivity.pdf';reader=PdfReader(pdf);assert len(reader.pages)==1
    page=reader.pages[0];t=page.extract_text()
    for token in ('4,096','Z4/A3/S4','256','95%','1,024','2,048','PLB32','beta4','different client resources','Finite windows','latency'):
        assert token in t,token
    assert not list(page.images) and '\\n' not in t
    fonts=page['/Resources']['/Font'];assert fonts
    for f in fonts.values():
        font=f.get_object()
        for descendant in font.get('/DescendantFonts',[font]):
            descriptor=descendant.get_object()['/FontDescriptor'].get_object()
            assert any(k in descriptor for k in ('/FontFile','/FontFile2','/FontFile3'))
    out=dict(status='passed',source_sha256=sha(source),export_sha256=sha(ep),data_sha256=sha(dp),
        checker_sha256=sha(__file__),statistics_checker_sha256=sha(Path(__file__).parent/'verify_free_sensitivity_tables.py'),
        raw_runs_checked=160,series_recomputed=32,pages=1,pdf_sha256=sha(pdf),vector=True,embedded_fonts=True,
        visual_review='separate final rendering inspection')
    save(PACKAGE/'results/free_sensitivity_exports_audit.json',out)
    print(json.dumps(dict(status='passed',runs=160,series=32,pages=1)))


if __name__=='__main__':main()
