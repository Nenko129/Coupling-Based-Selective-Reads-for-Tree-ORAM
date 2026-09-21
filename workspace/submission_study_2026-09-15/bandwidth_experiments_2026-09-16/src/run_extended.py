"""Separate entry point for public traces, size slices and period calibration."""
from common import *
import argparse,traceback
import run_core,run_fast
from public_trace import load_window

BASE_IDENTITY=run_fast.expected_identity

def identity():
    return dict(BASE_IDENTITY(),**{str((Path(__file__).parent/n).relative_to(ROOT)):sha(Path(__file__).parent/n)
                                  for n in ('run_extended.py','public_trace.py')})

def run(spec):
    if 'trace_file' in spec:run_core.stored_trace=load_window(spec)
    run_fast.expected_identity=identity
    row=run_fast.run(spec)
    row['extended_experiment']=dict(source_identity=identity(),type=spec.get('study','size_slice'),
        public_trace='trace_file' in spec,measurement_is_actual_serialized_frames=True)
    save(PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json",row)
    return row

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    spec=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    try:run(spec)
    except Exception:
        save(PACKAGE/'results/failures'/f"{spec['id']}_extended.json",dict(status='failed',spec=spec,error=traceback.format_exc()))
        raise
