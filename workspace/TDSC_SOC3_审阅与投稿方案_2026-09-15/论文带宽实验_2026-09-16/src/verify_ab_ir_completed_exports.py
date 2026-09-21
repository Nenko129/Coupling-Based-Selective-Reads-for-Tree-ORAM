"""Verify plotted intervals/actual signed SVG widths and all IR stress cells."""
from common import *
import math
import re
import xml.etree.ElementTree as ET
from verify_free_sensitivity_tables import check_stat


def main():
    ep=PACKAGE/'results/ab_ir_completed_exports.json';exports=json.loads(ep.read_text())
    assert exports['status']=='generated' and exports['generator_sha256']==sha(Path(__file__).parent/'render_ab_ir_completed.py')
    table=PACKAGE/'results/ab_ir_completed_tables_audit.json';checks=json.loads(table.read_text());assert checks['status']=='passed'
    figures=[]
    for export in exports['figures']:
        stem=export['stem'];source=PACKAGE/export['source_path'];a=json.loads(source.read_text())
        dp=PACKAGE/f'figures/{stem}_data.json';d=json.loads(dp.read_text())
        assert export['source_sha256']==d['source_sha256']==sha(source) and export['data_sha256']==sha(dp)
        assert export['table_audit_sha256']==sha(table)
        for ref in export['outputs']:assert sha(PACKAGE/ref['path'])==ref['sha256']
        records={}
        for ref in a['receipts']:
            p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];records[ref['id']]=json.loads(p.read_text())
        svg=PACKAGE/f'figures/{stem}.svg';tree=ET.parse(svg);ns={'s':'http://www.w3.org/2000/svg'}
        assert not tree.findall('.//s:image',ns)
        def path(gid):
            group=tree.find(f".//s:g[@id='{gid}']",ns);assert group is not None,gid
            p=group.find('s:path',ns);assert p is not None
            return p
        def points(gid):
            value=path(gid).attrib['d'];assert not re.search('[CcQqAa]',value)
            xs=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?',value)]
            assert len(xs)%2==0;return list(zip(xs[::2],xs[1::2]))
        assert len(d['series'])==(12 if stem=='completed_ab_cb_bandwidth' else 8)
        for s in d['series']:
            values=[];seeds=[]
            for left,right in s['ids']:
                l,r=records[left],records[right];sl,sr=l['spec'],r['spec']
                assert l['status']==r['status']=='passed' and l['trace']==r['trace'] and l['answer_sha256']==r['answer_sha256']
                assert (sl['kind'],sr['kind'])==(s['baseline'],s['variant'])
                assert sl['trace_seed']==sr['trace_seed'];seeds.append(sl['trace_seed'])
                assert sl['workload']==sr['workload']==s['workload']
                if stem=='completed_ab_cb_bandwidth':
                    assert ('D3' if sl['bottom_dummy'] is None else 'bottom_D0')==('D3' if sr['bottom_dummy'] is None else 'bottom_D0')==s['condition']
                else:assert sl['cohort']==sr['cohort']==s['cohort']=='main_beta14' and sl['dwb']==sr['dwb']==s['dwb']
                ml,mr=[z['phases']['measurement'] for z in (l,r)];assert ml['requests']==mr['requests']
                values.append(100*(1-mr['total_bytes']/ml['total_bytes']))
            assert seeds==list(range(101,106));check_stat(s,values)
            prefix=s['panel'];zero=points(prefix+'_reference_zero')[0][0];maximum=points(prefix+'_reference_max')[0][0]
            bar=points(s['gid']);assert abs(bar[0][0]-zero)<1e-5
            actual=(bar[1][0]-bar[0][0])/(maximum-zero)*d['axes_max'][prefix]
            assert math.isclose(actual,s['mean'],abs_tol=1e-6),(s['gid'],actual,s['mean'])
        stress=d['extra'].get('stress_outcomes',[])
        if stem=='completed_ir_compressed':
            assert len(stress)==15 and {(x['kind'],x['seed']) for x in stress}=={(k,s) for k in ('path','deferred','sde') for s in range(101,106)}
            for cell in stress:
                r=records[cell['id']];spec=r['spec'];assert (spec['kind'],spec['trace_seed'],spec['beta'])==(cell['kind'],cell['seed'],4)
                success=r['status']=='passed';assert (cell['status']=='passed')==success
                expected_color='#C2DCCB' if success else '#EFCEAD';assert cell['color']==expected_color
                assert f'fill: {expected_color.lower()}' in path(cell['gid']).attrib['style']
                if success:assert cell['phase']=='measurement' and cell['completed']==cell['offered']==6144
                else:
                    assert cell['phase']==r['phase']=='warmup' and cell['completed']==r['completed_this_phase']
                    assert cell['offered']==r['context']['phase_requests']==1536 and cell['completed']<1536
            assert sum(c['status']!='passed' for c in stress)==12
        else:assert not stress
        figures.append(dict(stem=stem,source_sha256=sha(source),data_sha256=sha(dp),svg_sha256=sha(svg),
            png_sha256=sha(PACKAGE/f'figures/{stem}.png'),raw_sources=len(records),numeric_bars=len(d['series']),
            actual_signed_svg_widths_checked=len(d['series']),stress_cells=len(stress),vector=True,fonts_as_paths=True))
    out=dict(status='passed',exports_sha256=sha(ep),tables_audit_sha256=sha(table),figures=figures,
        checker_sha256=sha(__file__),statistical_checker_sha256=sha(Path(__file__).parent/'verify_free_sensitivity_tables.py'),visual_review='separate')
    save(PACKAGE/'results/ab_ir_completed_exports_audit.json',out)
    print(json.dumps(dict(status='passed',figures=2,numeric_bars=20,stress_cells=15,raw_sources=195)))


if __name__=='__main__':main()
