"""Validate every named frontend receipt, input, ledger and matched schedule."""
from common import *
import composition_runtime as runtime
from collections import defaultdict

def check_bill(b):
    assert b['total_bytes']==b['request_bytes']+b['response_bytes']==sum(b['components'].values())
    assert sum(sum(x.values()) for x in b['by_stage'].values())==b['total_bytes']
    assert sum(sum(x.values()) for x in b['by_tree'].values())==b['total_bytes']
    assert sum(b['opcode_counts'].values())==b['rpc']==b['independently_invoiced_rpcs']
    assert b['next_sequence']-b['first_sequence']==b['rpc']

def main():
    plan=json.loads((PACKAGE/'formal_composition_plan.json').read_text());reports=[]
    for family_group in ('free','rho'):
        specs=[s for s in plan['specs'] if (s['family']=='rho')==(family_group=='rho')]
        if family_group=='rho':
            specs=[dict(s,id=s['id'].replace('C_rho','C2_rho',1),experiment_class='formal_rho_fixed') for s in specs]
            expected=dict(runtime.identity(),path_stash_replacement_fix={n:sha(Path(__file__).parent/n) for n in ('transfer_backend_fixed.py','run_rho_fixed.py')})
        else:expected=runtime.identity()
        rows=[];missing=[];groups=defaultdict(list)
        for s in specs:
            p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
            if not p.exists():missing.append(s['id']);continue
            r=json.loads(p.read_text(encoding='utf-8'))
            if family_group=='rho' and 'fix' not in r:missing.append(s['id']);continue
            assert r['status']=='passed' and r['spec']==s and r['source_hashes']==expected
            assert sha(PACKAGE/r['trace']['path'])==r['trace']['sha256']
            assert r['correctness_checked_requests']==s['warmup']+s['requests']
            for b in r['setup']:check_bill(b)
            for phase,count in [('warmup',s['warmup']),('measurement',s['requests'])]:
                x=r['phases'][phase];assert x['requests']==count
                for b in x['bills']:check_bill(b)
                assert x['total_bytes']==sum(b['total_bytes'] for b in x['bills'])
                assert x['rpc']==sum(b['rpc'] for b in x['bills'])
            assert r['bytes_per_request']*s['requests']==r['phases']['measurement']['total_bytes']
            rows.append(dict(id=s['id'],sha256=sha(p),independently_invoiced_rpcs=r['phases']['measurement']['rpc']))
            groups[s['family'],s['workload'],s['trace_seed']].append(r)
        schedule_groups=[]
        for key,rs in groups.items():
            for phase in ('warmup','measurement'):
                assert all(r['trace']==rs[0]['trace'] and r['phases'][phase]['schedules']==rs[0]['phases'][phase]['schedules'] for r in rs)
                assert all(r['phases'][phase]['frontend_metrics']==rs[0]['phases'][phase]['frontend_metrics'] for r in rs)
            schedule_groups.append(dict(family=key[0],workload=key[1],seed=key[2],backends=len(rs)))
        report=dict(family_group=family_group,status='complete_receipts_audited' if not missing else 'partial_receipts_audited',
            expected=len(specs),completed=len(rows),missing=missing,rows=rows,schedule_groups=schedule_groups,
            security_scope='receipt/functional/ledger audit; not new native-system security proof')
        reports.append(report)
    save(PACKAGE/'results/frontend_batch_audit.json',dict(reports=reports,checker_sha256=sha(__file__),runtime_identity=runtime.identity()))
    print(json.dumps([{k:r[k] for k in ('family_group','status','expected','completed')} for r in reports]))
if __name__=='__main__':main()
