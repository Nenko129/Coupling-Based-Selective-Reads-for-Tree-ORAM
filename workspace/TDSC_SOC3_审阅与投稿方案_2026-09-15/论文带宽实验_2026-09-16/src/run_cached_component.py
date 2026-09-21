from common import *
import argparse,dataclasses
import heterogeneous_oram as engine
import run_core
import cached_transport as cache
from cached_cost import expected_tree

def run(spec):
    files=[Path(__file__).parent/n for n in ('heterogeneous_oram.py','heterogeneous_fusion.py','cached_transport.py','cached_cost.py','run_cached_component.py')]
    identity={p.name:sha(p) for p in files};cuts={0:spec['cached_levels']};captured=[]
    cache.install(cuts)
    class Measured(cache.CachedTransport):
        def __init__(self,server):super().__init__(server);captured.append(self)
    run_core.StreamingTransport=Measured;run_core.ref=engine;run_core.Config=engine.Config;run_core.RecursiveORAM=engine.RecursiveORAM
    run_core.expected_tree=lambda c:expected_tree(c,cuts.get(c.tree,0))
    base=run_core.configs_for
    def configs(s):
        return [dataclasses.replace(c,Z_by_depth=tuple(s.get('Z_by_depth',[])),S_by_depth=tuple(s.get('S_by_depth',[]))) if j==0 else c for j,c in enumerate(base(s))]
    run_core.configs_for=configs
    row=run_core.run(spec);assert len(captured)==1;io=captured[0]
    assert identity=={p.name:sha(p) for p in files}
    row.update(cache_representation=io.cache_storage(),cache_and_heterogeneous_sources=identity,
               scope='actual static prefix cache + public depth layout; not IR-Stash hit skip/DWB or native AB CB/DeadQ')
    save(PACKAGE/'results'/spec['experiment_class']/f"{spec['id']}.json",row)
    return row
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();run(json.loads(Path(args.spec).read_text(encoding='utf-8')))
