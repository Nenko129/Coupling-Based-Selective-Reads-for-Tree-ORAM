"""Exact process-level trace transplant and frontend parameter checks."""
from common import *
from workloads import make_trace
from public_trace import load_window
import subprocess

def launch(spec,script,extra=()):
    p=PACKAGE/'specs'/f"{spec['id']}.json";save(p,spec)
    result=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).parent/script),'--spec',str(p),*extra],
                           capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,(spec['id'],result.stderr)
    return json.loads((PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json").read_text(encoding='utf-8'))

def equal_bill(a,b):
    for key in ('configs','bytes_per_request','rpc_per_request','server_storage','answer_sha256','final_stash_blocks'):
        assert a[key]==b[key],key
    for phase in ('warmup','measurement'):
        assert {k:v for k,v in a['phases'][phase].items() if k!='harness_seconds'}=={
                k:v for k,v in b['phases'][phase].items() if k!='harness_seconds'},phase

def main():
    rows=make_trace(32,48,654,'uniform');mapping=[dict(asu=0,lba=a*8,oram_address=a) for a in range(32)]
    raw=PACKAGE/'datasets/checks/fixture.csv';raw.parent.mkdir(exist_ok=True)
    raw.write_text(''.join(f'0,{a*8},4096,{"R" if v is None else "W"},{i}\n' for i,(a,v) in enumerate(rows)),encoding='ascii')
    fixture=PACKAGE/'datasets/checks/fixture.json'
    save(fixture,dict(N=32,trace_seed=654,warmup=16,requests=32,rows=rows,mapping=mapping,
         source=str(raw.relative_to(PACKAGE)),source_sha256=sha(raw),source_records=[0,48],
         semantics='test fixture: identity-mapped source command start keys',restrictions=['not a public evaluation trace']))
    trace_fields=dict(trace_file=str(fixture.relative_to(PACKAGE)),trace_file_sha256=sha(fixture))
    tests=[]
    s=dict(kind='r0',N=32,B=4096,profile=[4,3,3],R=128,map_B=64,terminal_bytes=32768,compact=True,fusion=True,
           warmup=16,requests=32,trace_seed=654,oram_seed=987,workload='uniform',experiment_class='extended_checks')
    a=launch(dict(s,id='extended_core_control'),'run_fast.py')
    b=launch(dict(s,id='extended_core_fixture',workload='fixture_startkey',**trace_fields),'run_extended.py')
    equal_bill(a,b);tests.append(dict(name='core_public_trace_transplant',same_frames_and_answers=True))
    cases=[('free_compressed','sde',64,dict(beta=2,X=32)),('free_raw','r0',4096,dict(X=1024)),
           ('free_compressed','r0',4096,dict(beta=14,X=2048)),('rho','r0',64,dict(frame_ratio=1)),
           ('rho','sde',64,dict(frame_ratio=5))]
    for i,(family,kind,B,parameters) in enumerate(cases):
        s=dict(family=family,kind=kind,N=32,B=B,profile=[4,3,4],R=128,plb=4,llc=2,rho=4,
               warmup=16,requests=32,trace_seed=654,oram_seed=987,workload='fixture_startkey',
               experiment_class='extended_checks',**trace_fields,**parameters)
        a=launch(dict(s,id=f'extended_front_{i}_legacy'),'run_extended_composition.py',('--legacy-prf',))
        b=launch(dict(s,id=f'extended_front_{i}_fast'),'run_extended_composition.py')
        equal_bill(a,b);tests.append(dict(name=f'{family}/{kind}/B{B}',parameters=parameters,same_frames_and_answers=True))
    invalid=[]
    original=dict(s)
    for change in (dict(trace_file_sha256='0'*64),dict(N=31),dict(trace_seed=655),dict(requests=31)):
        try:load_window(dict(original,**change))
        except AssertionError:invalid.append(change)
        else:raise AssertionError('invalid trace contract accepted')
    save(PACKAGE/'results/extended_runner_checks.json',dict(status='passed',tests=tests,rejected_contracts=invalid,
        source_hashes=source_identity(),adapters={n:sha(Path(__file__).parent/n) for n in ('run_extended.py','run_extended_composition.py','public_trace.py')},
        checker_sha256=sha(__file__)))
    print(json.dumps(dict(status='passed',paired_runs=len(tests),rejected_contracts=len(invalid))))
if __name__=='__main__':main()
