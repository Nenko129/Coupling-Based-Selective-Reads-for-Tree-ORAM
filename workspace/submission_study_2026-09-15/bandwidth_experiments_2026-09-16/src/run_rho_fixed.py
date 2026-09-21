from common import *
import argparse
import composition_runtime as runtime
import transfer_backend_fixed as fixed
import run_composition

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();spec=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    assert spec['family']=='rho'
    original_identity=runtime.identity
    def identity():
        return dict(original_identity(),path_stash_replacement_fix={name:sha(Path(__file__).parent/name) for name in ('transfer_backend_fixed.py','run_rho_fixed.py')})
    runtime.TransferTree=fixed.TransferTree;runtime.identity=identity
    row=run_composition.run(spec)
    row['fix']='Path uses post-removal pool for duplicate admission; corrects false fail-stop when the old target was in stash'
    save(PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json",row)
if __name__=='__main__':main()
