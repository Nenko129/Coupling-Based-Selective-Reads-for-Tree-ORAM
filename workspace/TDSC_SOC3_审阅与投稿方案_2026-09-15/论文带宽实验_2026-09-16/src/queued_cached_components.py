from common import *
from queued_core_batch import free_memory
import subprocess,time

def main():
    plan=json.loads((PACKAGE/'formal_cached_component_plan.json').read_text(encoding='utf-8'));rows=[]
    for spec in plan['specs']:
        identity={n:sha(Path(__file__).parent/n) for n in plan['source_hashes']};assert identity==plan['source_hashes']
        dest=PACKAGE/'results/formal_cached_components'/f"{spec['id']}.json"
        if dest.exists():
            row=json.loads(dest.read_text(encoding='utf-8'));assert row['spec']==spec and 'cache_representation' in row
            rows.append(dict(id=spec['id'],reused=True));continue
        while free_memory()<1.5*(1<<30):
            save(PACKAGE/'results/cached_component_queue.json',dict(stage='waiting_for_available_memory',pid=os.getpid(),next=spec['id'],time=time.time()))
            time.sleep(10)
        specpath=PACKAGE/'specs'/f"{spec['id']}.json";save(specpath,spec);logpath=PACKAGE/'results/logs'/f"{spec['id']}.log"
        with logpath.open('w',encoding='utf-8') as log:
            p=subprocess.Popen([sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_cached_component.py'),'--spec',str(specpath)],
                 stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            save(PACKAGE/'results/cached_component_queue.json',dict(stage='running',pid=os.getpid(),child_pid=p.pid,next=spec['id'],time=time.time()))
            code=p.wait()
        if code:
            save(PACKAGE/'results/component_failures'/f"{spec['id']}.json",dict(spec=spec,exit_code=code,log=logpath.read_text(encoding='utf-8')))
            raise RuntimeError('cached component failed; preserved log')
        row=json.loads(dest.read_text(encoding='utf-8'));assert 'cache_representation' in row
        item=dict(id=spec['id'],bytes_per_request=row['bytes_per_request']);rows.append(item);print(json.dumps(item),flush=True)
    save(PACKAGE/'results/cached_component_completion.json',dict(passed=True,rows=rows))
if __name__=='__main__':main()
