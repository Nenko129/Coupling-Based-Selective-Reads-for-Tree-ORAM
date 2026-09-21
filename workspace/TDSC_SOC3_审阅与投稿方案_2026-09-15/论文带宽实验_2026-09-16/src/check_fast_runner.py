"""Check the actual process entry point, including identity binding and ledger."""
from common import *
import subprocess

def main():
    pairs=[]
    for mode,kind in (('core','sde'),('cached','r0')):
        rows=[]
        for fast in (False,True):
            s=dict(id=f'driver_{mode}_{kind}_{int(fast)}',kind=kind,N=32,B=4096,profile=[4,3,3],R=128,
                   map_B=64,terminal_bytes=32768,compact=True,fusion=True,warmup=16,requests=32,
                   trace_seed=654,oram_seed=987,workload='uniform',experiment_class='driver_checks')
            if mode=='cached':s.update(cached_levels=2,S_by_depth=[3,2,2,3,3,3])
            path=PACKAGE/'specs'/f"{s['id']}.json";save(path,s)
            script='run_fast.py' if fast else 'run_cached_component.py' if mode=='cached' else 'run_core.py'
            cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).parent/script),'--spec',str(path)]
            if fast:cmd+=['--mode',mode]
            done=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8');assert done.returncode==0,done.stderr
            rows.append(json.loads((PACKAGE/'results/driver_checks'/f"{s['id']}.json").read_text(encoding='utf-8')))
        a,b=rows
        for k in ('configs','trace','measurement_windows','bytes_per_request','rpc_per_request','server_storage',
                  'terminal_position_map_bytes','final_stash_blocks','max_online_boundary_stash','final_clock','answer_sha256'):
            assert a[k]==b[k],(mode,k)
        for phase in ('warmup','measurement'):
            x={k:v for k,v in a['phases'][phase].items() if k!='harness_seconds'}
            y={k:v for k,v in b['phases'][phase].items() if k!='harness_seconds'}
            assert x==y,(mode,phase)
        if mode=='cached':assert a['cache_representation']==b['cache_representation']
        assert all(b['source_hashes'][k]==v for k,v in a['source_hashes'].items())
        assert b['execution_revision']['name']=='hmac_prefix_reuse_v1'
        pairs.append(dict(mode=mode,passed=True,records=[r['spec']['id'] for r in rows]))
    save(PACKAGE/'results/fast_runner_checks.json',dict(status='passed',pairs=pairs,
         runner_sha256=sha(Path(__file__).parent/'run_fast.py'),accelerator_sha256=sha(Path(__file__).parent/'fast_prf.py')))
    print(json.dumps(dict(status='passed',pairs=len(pairs))))
if __name__=='__main__':main()
