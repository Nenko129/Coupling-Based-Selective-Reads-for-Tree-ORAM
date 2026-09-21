"""Recompute the completed tuned figure and both CSV tables from raw bills."""
from common import *
import csv,math,statistics
from pypdf import PdfReader


def close(x,y):assert math.isclose(x,y,rel_tol=1e-11,abs_tol=1e-8),(x,y)


def main():
    sp=PACKAGE/'results/tuned_completed_snapshot.json';a=json.loads(sp.read_text())
    ep=PACKAGE/'results/tuned_exports.json';export=json.loads(ep.read_text())
    assert export['source_sha256']==sha(sp) and a['status']=='passed' and a['runs']==50
    assert export['generator_sha256']==sha(PACKAGE/'src/render_completed_tuned.py')
    for ref in export['outputs']:assert sha(PACKAGE/ref['path'])==ref['sha256']
    dp=PACKAGE/'figures/completed_tuned_data.json';d=json.loads(dp.read_text())
    assert d['source_sha256']==sha(sp) and export['data_sha256']==sha(dp)
    assert len(d['series'])==16 and d['absolute_plot_scale']==1024
    rows={}
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];r=json.loads(p.read_text());rows[ref['id']]=r
    assert len(rows)==50
    for point in d['series']:
        xs=[];seeds=[]
        for ids in point['ids']:
            if point['panel']=='absolute':
                r=rows[ids];s=r['spec'];seeds.append(s['trace_seed'])
                assert (s['kind'],s['workload'])==(point['kind'],point['workload'])
                xs.append(r['phases']['measurement']['total_bytes']/s['requests'])
            else:
                l,r=[rows[x] for x in ids]
                assert l['trace']==r['trace'] and l['answer_sha256']==r['answer_sha256']
                assert l['spec']['requests']==r['spec']['requests'] and l['spec']['trace_seed']==r['spec']['trace_seed']
                assert (l['spec']['kind'],r['spec']['kind'],l['spec']['workload'],r['spec']['workload'])==(
                    point['baseline'],point['variant'],point['workload'],point['workload'])
                seeds.append(l['spec']['trace_seed'])
                xs.append(100*(1-r['phases']['measurement']['total_bytes']/l['phases']['measurement']['total_bytes']))
        assert seeds==list(range(101,106))
        for x,y in zip(xs,point['values']):close(x,y)
        mean=sum(xs)/5
        variance=sum((x-mean)**2 for x in xs)/4
        half=2.7764451051977987*math.sqrt(variance/5)
        close(mean,point['mean']);close(mean-half,point['ci95'][0]);close(mean+half,point['ci95'][1])
    p=PACKAGE/'tables/tuned_50_runs.csv';raw=list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
    assert len(raw)==50 and {x['id'] for x in raw}==set(rows)
    sources={x['id']:x for x in a['receipts']}
    for x in raw:
        r=rows[x['id']];s=r['spec'];m=r['phases']['measurement'];z,ar,ss=s['profile']
        assert x['source_path']==sources[x['id']]['path'] and x['source_sha256']==sources[x['id']]['sha256']
        assert (x['kind'],x['workload'])==(s['kind'],s['workload'])
        for key,v in dict(seed=s['trace_seed'],N=s['N'],B=s['B'],Z=z,A=ar,S=ss,R=s['R'],map_B=s['map_B'],
                          requests=s['requests'],measurement_bytes=m['total_bytes']).items():assert int(x[key])==v
        close(float(x['bytes_per_request']),m['total_bytes']/s['requests'])
        close(float(x['rpc_per_request']),m['rpc']/s['requests'])
    cp=PACKAGE/'tables/tuned_6_comparisons.csv';effects=list(csv.DictReader(cp.open(encoding='utf-8-sig',newline='')))
    assert len(effects)==6
    for x in effects:
        y=next(s for s in d['series'] if s['panel']=='paired' and (s['baseline'],s['variant'],s['workload'])==
               (x['baseline'],x['variant'],x['workload']))
        assert int(x['n'])==5
        close(float(x['mean_saving_pct']),y['mean']);close(float(x['ci95_low']),y['ci95'][0]);close(float(x['ci95_high']),y['ci95'][1])
    pdf=PACKAGE/'output/pdf/completed_tuned_bandwidth.pdf';reader=PdfReader(pdf);assert len(reader.pages)==1
    page=reader.pages[0];text_=page.extract_text()
    for token in ('16,384','4,096','256','95%','Z4/A3','Z7/A6/S9','Z7/A6/S6','72 candidates',
                  'actual storage differs','empirical Path Z4','global-optimum','latency'):
        assert token in text_,token
    assert '\\n' not in text_ and not list(page.images)
    fonts=page['/Resources']['/Font'];assert fonts
    for font in fonts.values():
        f=font.get_object()
        for descendant in f.get('/DescendantFonts',[f]):
            fd=descendant.get_object()['/FontDescriptor'].get_object()
            assert any(k in fd for k in ('/FontFile','/FontFile2','/FontFile3'))
    save(PACKAGE/'results/tuned_exports_audit.json',dict(status='passed',source_sha256=sha(sp),
        export_sha256=sha(ep),checker_sha256=sha(__file__),raw_runs_checked=50,series_recomputed=16,
        csv_observations=50,csv_comparisons=6,pdf_sha256=sha(pdf),pages=1,
        vector=True,embedded_fonts=True,visual_review='separate final rendering inspection'))
    print(json.dumps(dict(status='passed',runs=50,series=16,csv_rows=56,pages=1)))


if __name__=='__main__':main()
