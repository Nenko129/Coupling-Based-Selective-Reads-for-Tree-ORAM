from pathlib import Path
import sys,json,datetime,collections
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minimal_runtime import *

def main():
    lock=json.loads((HOME/'source_lock.json').read_text(encoding='utf-8'));assert lock['source_hashes']==identity()
    for name,digest in lock['plan_hashes'].items():assert sha(HOME/name)==digest
    total=0
    for suite in ('pilot','formal'):
        plan=json.loads((HOME/f'{suite}_plan.json').read_text(encoding='utf-8'))
        ids=[s['id'] for s in plan['specs']];assert len(ids)==len(set(ids))==plan['rows']
        for s in plan['specs']:
            assert json.loads((HOME/'specs'/suite/f"{s['id']}.json").read_text(encoding='utf-8'))==s
            assert s['compact'] is False and s['fusion'] is False and s['root_retained'] is True
            if s['family'] in ('IR','AB'):
                c=configuration(s);assert s['warmup']%(c.A*(1<<c.L))==s['requests']%(c.A*(1<<c.L))==0
                if suite=='formal' and s['family']=='IR' and s['layout']=='depth':
                    assert c.Z_by_depth==(4,4,4,4,4,4,2,2,2,3,3,4,4) and c.R==480 and c.L==12
            total+=1
    checks=json.loads((HOME/'results/minimal_contract_checks.json').read_text(encoding='utf-8'));assert checks['status']=='passed' and checks['source_hashes']==identity()
    for name in ('public_selector_checks.json','frontend_reset_checks.json','capacity_binding.json'):
        assert json.loads((HOME/'results'/name).read_text(encoding='utf-8'))['status']=='passed'
    pilots=json.loads((HOME/'pilot_plan.json').read_text(encoding='utf-8'))['specs']
    for s in pilots:
        r=json.loads((HOME/'results/pilot'/f"{s['id']}.json").read_text(encoding='utf-8'));assert r['status']=='passed' and r['spec']==s
    save(HOME/'results/preflight.json',dict(status='passed',generated=datetime.datetime.now().isoformat(),specs_checked=total,pilot_passed=len(pilots),
        coupling_boundaries=checks['complete_boundary_checks'],source_lock_sha256=sha(HOME/'source_lock.json'),
        ready_to_run_formal=True,formal_complete=len(list((HOME/'results/formal').glob('*.json')))==120,all_submission_requirements_complete=False,
        remaining='complete repetitions and final figure/data audit; do not claim latency, true trusted peak, native full-system reproduction, or global SOTA'))
    print(json.dumps(dict(status='passed',specs=total,pilot_passed=len(pilots),ready_to_run_formal=True)))
if __name__=='__main__':main()
