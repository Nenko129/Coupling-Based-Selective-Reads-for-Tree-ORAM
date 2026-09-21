"""Scoped frontend parameter/trace adapter with unchanged Transfer/ORAM code."""
from common import *
import argparse,traceback
import composition_runtime as runtime
import run_composition
import transfer_backend_fixed as fixed
import optimized_oram as engine
from fast_prf import make_fast_prf
from public_trace import load_window

ORIGINAL_IDENTITY=runtime.identity

def identity():
    names=('run_extended_composition.py','public_trace.py','fast_prf.py','transfer_backend_fixed.py')
    return dict(ORIGINAL_IDENTITY(),extended_adapter={n:sha(Path(__file__).parent/n) for n in names})

def run(spec,accelerate=True):
    proofpath=PACKAGE/'results/fast_prf_regression.json';proof=json.loads(proofpath.read_text())
    assert proof['status']=='passed' and proof['source_hashes']==source_identity()
    assert proof['accelerator_sha256']==sha(Path(__file__).parent/'fast_prf.py')
    if accelerate:runtime.PRF=make_fast_prf(engine)
    if spec['family']=='rho':runtime.TransferTree=fixed.TransferTree
    runtime.identity=identity
    if 'trace_file' in spec:run_composition.stored_trace=load_window(spec)
    ff=runtime.frontends
    if spec['family']=='rho':
        original=ff.RhoFront
        def make(*args,**kwargs):
            kwargs['n']=spec.get('frame_ratio',3)
            return original(*args,**kwargs)
        ff.RhoFront=make
    else:
        original=ff.FreecursiveFront
        def make(*args,**kwargs):
            kwargs['beta']=spec.get('beta',14)
            if 'X' in spec:kwargs['X']=spec['X']
            return original(*args,**kwargs)
        ff.FreecursiveFront=make
    row=run_composition.run(spec)
    row['extended_experiment']=dict(accelerated=accelerate,accelerator_proof_sha256=sha(proofpath),
        type=spec.get('study','frontend_sensitivity'),parameters={k:spec[k] for k in ('beta','X','frame_ratio') if k in spec},
        public_trace='trace_file' in spec,source_identity=identity())
    save(PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json",row)
    return row

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--legacy-prf',action='store_true');args=p.parse_args()
    spec=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    try:run(spec,not args.legacy_prf)
    except Exception:
        save(PACKAGE/'results/failures'/f"{spec['id']}_extended.json",dict(status='failed',spec=spec,error=traceback.format_exc()))
        raise
