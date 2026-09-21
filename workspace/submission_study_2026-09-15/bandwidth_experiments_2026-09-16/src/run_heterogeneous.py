"""Reuse the measured runner with a separately bound static-profile engine."""
from common import *
import argparse,dataclasses
import heterogeneous_oram as engine
import run_core
from heterogeneous_meter import install
from heterogeneous_cost import expected_tree

def run(spec):
    runtime=[Path(__file__).parent/n for n in ('heterogeneous_oram.py','heterogeneous_fusion.py','heterogeneous_meter.py','heterogeneous_cost.py','run_heterogeneous.py')]
    identity={p.name:sha(p) for p in runtime}
    install(engine);run_core.ref=engine;run_core.Config=engine.Config;run_core.RecursiveORAM=engine.RecursiveORAM;run_core.expected_tree=expected_tree
    base=run_core.configs_for
    def configs(s):
        cs=base(s)
        return [dataclasses.replace(c,Z_by_depth=tuple(s.get('Z_by_depth',[])),S_by_depth=tuple(s.get('S_by_depth',[]))) if j==0 else c for j,c in enumerate(cs)]
    run_core.configs_for=configs
    row=run_core.run(spec)
    assert identity=={p.name:sha(p) for p in runtime}
    row['heterogeneous_source_hashes']=identity
    row['composition_scope']='static public per-depth bucket layout; no top cache, IR-Stash/DWB, CB or DeadQ'
    save(PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json",row)
    return row

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spec',required=True);args=parser.parse_args()
    run(json.loads(Path(args.spec).read_text(encoding='utf-8')))
if __name__=='__main__':main()
