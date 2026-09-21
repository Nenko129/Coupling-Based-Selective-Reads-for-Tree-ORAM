"""Read a bound, losslessly mapped command-start-key trace, without LBA guessing."""
from common import *

def load_window(spec):
    path=PACKAGE/spec['trace_file']
    assert sha(path)==spec['trace_file_sha256'],'prepared trace changed'
    window=json.loads(path.read_text(encoding='utf-8'))
    assert window['N']==spec['N'] and window['trace_seed']==spec['trace_seed']
    assert (window['warmup'],window['requests'])==(spec['warmup'],spec['requests'])
    source=PACKAGE/window['source'];assert sha(source)==window['source_sha256'],'raw trace changed'
    rows=window['rows'];assert len(rows)==spec['warmup']+spec['requests']
    mapping=window['mapping'];addresses=[x['oram_address'] for x in mapping]
    assert len(set(addresses))==len(addresses) and all(0<=x<spec['N'] for x in addresses)
    assert len({(x['asu'],x['lba']) for x in mapping})==len(mapping)
    allowed=set(addresses)
    for i,(a,v) in enumerate(rows):
        assert a in allowed and (v is None or v==i+1)
    info=dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path),source_sha256=window['source_sha256'],
              source_records=window['source_records'],semantics=window['semantics'],restrictions=window['restrictions'])
    def bound_loader(N,count,seed,workload):
        assert (N,count,seed,workload)==(spec['N'],len(rows),spec['trace_seed'],spec['workload'])
        return rows,info
    return bound_loader
