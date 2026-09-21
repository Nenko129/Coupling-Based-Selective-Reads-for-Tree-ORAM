"""Dedicated-process runner using the byte-equivalent PRF implementation."""
from common import *
import argparse
import run_core
from fast_prf import make_fast_prf

def fast_sources():
    return {str((Path(__file__).parent/n).relative_to(ROOT)):sha(Path(__file__).parent/n)
            for n in ('fast_prf.py','run_fast.py')}

def expected_identity():
    return dict(source_identity(),**fast_sources())

def run(spec, mode='core'):
    proofpath=PACKAGE/'results/fast_prf_regression.json'
    proof=json.loads(proofpath.read_text(encoding='utf-8'))
    assert proof['status']=='passed' and proof['source_hashes']==source_identity()
    assert proof['accelerator_sha256']==sha(Path(__file__).parent/'fast_prf.py')
    before=fast_sources()
    run_core.source_identity=expected_identity
    if mode=='cached':
        import heterogeneous_oram as engine
        import run_cached_component
        assert proof['heterogeneous_sha256']==sha(Path(__file__).parent/'heterogeneous_oram.py')
        engine.PRF=make_fast_prf(engine)
        row=run_cached_component.run(spec)
    else:
        run_core.ref.PRF=make_fast_prf(run_core.ref)
        row=run_core.run(spec)
    assert before==fast_sources()
    row['execution_revision']=dict(name='hmac_prefix_reuse_v1',proof_sha256=sha(proofpath),
                                   scope='byte-equivalent frames and primitive accounting; timing not comparable with legacy harness')
    save(PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json",row)
    return row

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--mode',choices=('core','cached'),default='core')
    args=p.parse_args();run(json.loads(Path(args.spec).read_text(encoding='utf-8')),args.mode)
