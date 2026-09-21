"""Recompute all plot values from raw receipts and read actual SVG bar widths."""
from common import *
import math
import re
import xml.etree.ElementTree as ET
from verify_free_sensitivity_tables import check_stat


def main():
    source=PACKAGE/'results/rho_sensitivity_completed_snapshot.json';a=json.loads(source.read_text())
    ep=PACKAGE/'results/rho_sensitivity_exports.json';e=json.loads(ep.read_text())
    dp=PACKAGE/'figures/completed_rho_sensitivity_data.json';d=json.loads(dp.read_text())
    assert a['status']=='complete_receipts_audited' and a['completed']==180
    assert e['source_sha256']==d['source_sha256']==sha(source) and e['data_sha256']==sha(dp)
    assert e['generator_sha256']==sha(Path(__file__).parent/'render_rho_sensitivity.py')
    assert e['checks_sha256']==sha(PACKAGE/'results/rho_sensitivity_checks.json')
    for out in e['outputs']:assert sha(PACKAGE/out['path'])==out['sha256']
    records={}
    for ref in a['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];records[ref['id']]=json.loads(p.read_text())
    assert len(records)==180 and len(d['series'])==54 and d['absolute_scale']==1024
    svg=PACKAGE/'figures/completed_rho_sensitivity.svg';tree=ET.parse(svg);ns={'s':'http://www.w3.org/2000/svg'}
    assert not tree.findall('.//s:image',ns)
    def path_points(gid):
        group=tree.find(f".//s:g[@id='{gid}']",ns);assert group is not None,gid
        path=group.find('s:path',ns);assert path is not None
        raw=path.attrib['d'];assert not re.search('[CcQqAa]',raw),raw
        numbers=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?',raw)]
        assert len(numbers)%2==0
        return list(zip(numbers[::2],numbers[1::2]))
    for series in d['series']:
        values=[];seeds=[]
        for ids in series['ids']:
            if series['panel']=='absolute':
                r=records[ids];sp=r['spec'];m=r['phases']['measurement'];values.append(m['total_bytes']/m['requests'])
                assert sp['kind']==series['kind']
            else:
                l,r=[records[i] for i in ids];sp=l['spec']
                assert l['trace']==r['trace'] and l['answer_sha256']==r['answer_sha256']
                assert (sp['kind'],r['spec']['kind'])==(series['baseline'],series['variant'])
                assert sp['trace_seed']==r['spec']['trace_seed']
                assert l['phases']['measurement']['requests']==r['phases']['measurement']['requests']==4096
                values.append(100*(1-r['phases']['measurement']['total_bytes']/l['phases']['measurement']['total_bytes']))
            seeds.append(sp['trace_seed'])
            assert sp['workload']+'/'+sp.get('condition','base')==series['configuration']
        assert seeds==list(range(101,106));check_stat(series,values)
        prefix=series['panel'];zero=path_points(prefix+'_reference_zero')[0][0];maximum=path_points(prefix+'_reference_max')[0][0]
        xs=[x for x,y in path_points(series['gid'])];assert abs(min(xs)-zero)<1e-5
        drawn=(max(xs)-zero)/(maximum-zero)*d['axes_max'][prefix]
        expected=series['mean']/(1024 if prefix=='absolute' else 1)
        assert math.isclose(drawn,expected,abs_tol=1e-5),(series['gid'],drawn,expected)
    out=dict(status='passed',source_sha256=sha(source),exports_sha256=sha(ep),data_sha256=sha(dp),
        checker_sha256=sha(__file__),raw_runs_checked=180,series_recomputed=54,svg_bar_widths_checked=54,
        svg_sha256=sha(svg),png_sha256=sha(PACKAGE/'figures/completed_rho_sensitivity.png'),vector=True,fonts_as_paths=True,visual_review='separate')
    save(PACKAGE/'results/rho_sensitivity_exports_audit.json',out)
    print(json.dumps(dict(status='passed',runs=180,series=54,actual_svg_bars=54)))


if __name__=='__main__':main()
