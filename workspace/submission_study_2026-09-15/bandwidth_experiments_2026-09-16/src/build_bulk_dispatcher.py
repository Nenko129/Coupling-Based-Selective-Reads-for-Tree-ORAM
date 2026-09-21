"""Preserve the running dispatcher, derive an auditable scale-only variant."""
from common import *
import difflib

def main():
    source=Path(__file__).parent/'dispatch_extended.py';old=source.read_text();new=old
    changes=[('from run_extended import identity as core_identity','from run_bulk_scale import identity as core_identity'),
             ("name=path.stem;results=[]","name=path.stem+'_bulk';results=[]"),
             ("script='run_extended.py' if item['entry']=='core' else 'run_extended_composition.py'","assert item['entry']=='core'\n        script='run_bulk_scale.py'"),
             ("f\"{s['id']}_extended.log\"","f\"{s['id']}_bulk.log\""),
             ("assert proof['status']=='passed'","assert proof['status']=='passed'\n    bulk=json.loads((PACKAGE/'results/bulk_runner_checks.json').read_text())\n    assert bulk['status']=='passed' and bulk['runner_sha256']==sha(Path(__file__).parent/'run_bulk_scale.py')\n    assert bulk['bulk_sha256']==sha(Path(__file__).parent/'bulk_prf.py')")]
    for a,b in changes:
        assert new.count(a)==1,a;new=new.replace(a,b)
    target=source.with_name('dispatch_bulk_scale.py');assert not target.exists();target.write_text(new,encoding='utf-8')
    diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=source.name,tofile=target.name))
    (PACKAGE/'results/bulk_dispatcher.diff').write_text(diff,encoding='utf-8')
    save(PACKAGE/'results/bulk_dispatcher_build.json',dict(source_sha256=sha(source),target_sha256=sha(target),generator_sha256=sha(__file__)))
if __name__=='__main__':main()
