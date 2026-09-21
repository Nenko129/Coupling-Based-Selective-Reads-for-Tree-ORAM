"""Read-only verification of the exported XLSX and its source bindings."""
from common import *
import openpyxl

def main():
    out=PACKAGE/'outputs/01a09f23-0c2e-75e3-9ce5-d8ef0a277d5e'
    p=out/'Freecursive_rho_基础实验.xlsx'
    values=openpyxl.load_workbook(p,data_only=True,read_only=False)
    formulas=openpyxl.load_workbook(p,data_only=False,read_only=False)
    assert values.sheetnames==['结果','配对计算','原始运行']
    raw=values['原始运行'];assert raw.tables['RawRuns'].ref=='A1:V241'
    assert formulas['配对计算'].tables['PairedRuns'].ref=='A5:H125'
    assert raw.freeze_panes is not None
    for cells in raw.iter_rows(min_row=2,max_row=241,values_only=True):
        ident,family,workload,kind,seed,N,B,requests,total,down,up,rpc,*_=cells
        rel,digest=cells[20:22];source=PACKAGE/rel;assert sha(source)==digest
        r=json.loads(source.read_text());s=r['spec'];m=r['phases']['measurement']
        assert (ident,family,workload,kind,seed,N,B,requests)==(s['id'],s['family'],s['workload'],s['kind'],s['trace_seed'],s['N'],s['B'],s['requests'])
        assert total==m['total_bytes']==down+up and rpc==m['rpc']
    reference=json.loads((PACKAGE/'results/paired_statistics.json').read_text())['rows']
    for i in range(8,32):
        group=values['结果'].cell(i,1).value
        family,workload,comparison=group.split(' / ');new,base=comparison.split(' vs ')
        r=next(r for r in reference if r['family']==family and r['workload']==workload and r['baseline']==base and r['selective']==new and r['N']==4096 and r['B']==64)
        actual=[values['结果'].cell(i,j).value for j in (2,3,4,5,7,8)]
        expected=[5,r['baseline_mean_bytes'],r['selective_mean_bytes'],r['paired_mean_saving_pct']/100,r['ci95'][0]/100,r['ci95'][1]/100]
        assert all(isinstance(a,(int,float)) and abs(a-b)<1e-8 for a,b in zip(actual,expected)),(group,actual,expected)
        assert formulas['结果'].cell(i,5).value.startswith('=AVERAGEIFS(')
    errors=[]
    for ws in values:
        for row in ws:
            errors.extend((ws.title,c.coordinate,c.value) for c in row if c.data_type=='e')
    assert not errors
    save(out/'export_check.json',dict(status='passed',xlsx_sha256=sha(p),source_rows_checked=240,summary_rows_checked=24,formula_error_cells=errors,
         table_sources_sort_together=True,reader='openpyxl read only verification; no native Excel execution',checker_sha256=sha(__file__)))
    print(json.dumps(dict(status='passed',raw=240,summary=24)))

if __name__=='__main__':main()
