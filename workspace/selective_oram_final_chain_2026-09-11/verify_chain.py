#!/usr/bin/env python3
"""One-command or checkpointed reproduction of the same complete evidence chain.
A stage receipt binds its outputs to the CURRENT source/certificate contract.
Assembly refuses missing, stale, or altered receipts. This is reproducibility
bookkeeping, not a cryptographic attestation or a proof-assistant theorem.
"""
from pathlib import Path
import sys,subprocess,argparse,json,hashlib,time,platform
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from certified_driver import CertificateBank
FLAGS=['-std=c++17','-O3','-fopenmp','-frounding-math','-ffp-contract=off','-fno-fast-math']
STAGES={
 'scalar_validation':('legacy/validate_scalar.py',[],['legacy/scalar_validation_results.json']),
 'reduction':('src/reduction_checks.py',[],['results/reduction_checks.json']),
 'integrated':('src/chain_tests.py',['integrated'],['results/integrated.json','results/integrated_ledger_sample.jsonl']),
 'authentication_cost':('src/chain_tests.py',['active_attacks','slot_exchangeability','local_proofs','cost_intervals','unified_measured_ledgers'],
    ['results/'+n+'.json' for n in ('active_attacks','slot_exchangeability','local_proofs','cost_intervals','unified_measured_ledgers')]),
 'gate':('src/gate_tests.py',[],['results/gate_tests.json']),
 'cost_table':('src/unified_cost.py',[],['results/unified_cost_table.json']),
 'parameters':('src/certified_driver.py',[],['results/certificate_bindings.json'])}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def call(args,label):
    start=time.perf_counter();p=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (ROOT/'results'/('reproduce_'+label+'.log')).write_text(p.stdout)
    if p.returncode:print(p.stdout);raise SystemExit(f'{label} failed: {p.returncode}')
    print(label,'PASS',f'{time.perf_counter()-start:.2f}s',flush=True)
def receipt(name,outputs,executed):
    p=ROOT/'results/stage_receipts';p.mkdir(exist_ok=True)
    data={'stage':name,'input_contract_sha256':sha(ROOT/'theorem_contract.json'),'executed_in_this_stage':executed,
          'outputs_sha256':{v:sha(ROOT/v) for v in outputs}}
    (p/(name+'.json')).write_text(json.dumps(data,indent=2))

def certificates(recompute):
    ct=json.loads((ROOT/'theorem_contract.json').read_text())
    for name,digest in ct['artifact_sha256'].items():
        if recompute and name.startswith('certificates/'):continue
        assert sha(ROOT/name)==digest,('identity changed',name)
    exe=ROOT/'legacy/ghost_scalar'
    if recompute or not exe.exists():call(['g++',*FLAGS,'legacy/ghost_scalar.cpp','-o',str(exe)],'compile')
    if recompute:
        call([sys.executable,'legacy/poisson_seed.py'],'poisson_seed')
        for m in ('up','next'):call([str(exe),'280','31','128','4',m,f'certificates/ghost_{m}_c280_h31'],'ghost_'+m)
    CertificateBank()
    outputs=[f'certificates/ghost_{m}_c280_h31{s}' for m in ('up','next') for s in ('.csv','_meta.json')]
    receipt('certificates',outputs,recompute)

def assemble():
    bank=CertificateBank();ct=bank.contract;receipts={}
    for stage in ['certificates',*STAGES]:
        p=ROOT/f'results/stage_receipts/{stage}.json';assert p.exists(),('stage not completed',stage)
        r=json.loads(p.read_text());assert r['input_contract_sha256']==sha(ROOT/'theorem_contract.json'),('stale stage',stage)
        for name,digest in r['outputs_sha256'].items():assert sha(ROOT/name)==digest,('stage output changed',stage,name)
        receipts[stage]=r
    load=lambda n:json.loads((ROOT/n).read_text())
    integrated=load('results/integrated.json');attacks=load('results/active_attacks.json');gates=load('results/gate_tests.json')
    scalar=load('legacy/scalar_validation_results.json');plan=load('results/certificate_bindings.json')
    assert scalar['exact_rational_inequalities']==160 and scalar['thread_count_bitwise_match']
    assert attacks['count']==20 and gates['rejected_contract_or_budget_mutations']==10
    assert integrated['totals']['field_recurrence_comparisons']==integrated['totals']['canonical_comparisons']
    assert all(v['passes_2m128'] for v in plan.values())
    out={'chain_consistency_passed':True,
       'fresh_full_certificate_recomputation':receipts['certificates']['executed_in_this_stage'],
       'fresh_test_execution':all(r['executed_in_this_stage'] for k,r in receipts.items() if k!='certificates'),
       'contract_sha256':sha(ROOT/'theorem_contract.json'),'scope':ct['theorem_scope'],'proof_assistant_formalization':False,
       'edges':[
         {'edge':'actual -> finite shadow -> home field','evidence':'proofs/01_reduction_complete.md + per-current depth and field equality tests'},
         {'edge':'home field -> Poisson idcx -> scalar object','evidence':'fixed-history marking proof and explicit count recurrence'},
         {'edge':'scalar object -> numeric upper -> recursive configuration','evidence':'recomputed CSV + exact dyadic plan + runtime horizon guard'},
         {'edge':'recursive transitions -> authenticated bytes','evidence':'same encrypted Tree/RecursiveORAM execution and pre-use validation'},
         {'edge':'authenticated bytes -> unified cost table','evidence':'independent per-frame invoice identity + outward expected-cost intervals'}],
       'integrated_totals':integrated['totals'],'active_attacks':attacks['count'],'gate_mutations_rejected':gates['rejected_contract_or_budget_mutations'],
       'certificate_points_per_mode':len(bank.mode_values['up']),
       'python':sys.version,'platform':platform.platform(),'compiler_flags':FLAGS,
       'interpretation':'Complete research-level chain within the stated request/client model and PRF assumption; no deployment certification or 48GiB network benchmark.'}
    (ROOT/'results/final_chain_verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--recompute',action='store_true');ap.add_argument('--reuse-tests',action='store_true')
    ap.add_argument('--stage',choices=['certificates',*STAGES,'assemble']);a=ap.parse_args()
    if a.stage=='assemble':assemble();return
    if a.stage in (None,'certificates'):certificates(a.recompute)
    if a.stage=='certificates':return
    CertificateBank()
    chosen=[a.stage] if a.stage else list(STAGES)
    for k in chosen:
        script,extra,outputs=STAGES[k]
        if not a.reuse_tests:call([sys.executable,script,*extra],k)
        receipt(k,outputs,not a.reuse_tests)
    if not a.stage:assemble()
if __name__=='__main__':main()
