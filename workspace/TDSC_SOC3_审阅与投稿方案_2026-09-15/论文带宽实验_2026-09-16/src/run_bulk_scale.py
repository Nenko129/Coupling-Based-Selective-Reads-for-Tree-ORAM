"""A separate, byte-identical implementation for the expensive size-slice queue."""
from common import *
import argparse,traceback
import run_extended,run_fast
from bulk_prf import make_bulk_prf

BASE_IDENTITY=run_extended.identity

def identity():
    return dict(BASE_IDENTITY(),**{str((Path(__file__).parent/n).relative_to(ROOT)):sha(Path(__file__).parent/n)
                                  for n in ('bulk_prf.py','run_bulk_scale.py')})

def run(spec):
    proofpath=PACKAGE/'results/bulk_prf_checks.json';proof=json.loads(proofpath.read_text())
    assert proof['status']=='passed' and proof['source_hashes']==source_identity()
    assert proof['bulk_sha256']==sha(Path(__file__).parent/'bulk_prf.py')
    assert proof['prefix_sha256']==sha(Path(__file__).parent/'fast_prf.py')
    run_fast.make_fast_prf=make_bulk_prf
    run_extended.identity=identity
    row=run_extended.run(spec)
    row['execution_revision']=dict(name='hmac_bulk_exact_v2',proof_sha256=sha(proofpath),
                                   scope='exact same HMAC inputs and outputs; not password derivation or a new ORAM algorithm')
    save(PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json",row)
    return row

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();s=json.loads(Path(args.spec).read_text())
    try:run(s)
    except Exception:
        save(PACKAGE/'results/failures'/f"{s['id']}_bulk.json",dict(spec=s,error=traceback.format_exc()));raise
