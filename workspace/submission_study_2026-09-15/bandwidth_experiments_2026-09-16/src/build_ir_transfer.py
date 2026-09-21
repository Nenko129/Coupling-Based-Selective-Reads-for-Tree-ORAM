"""Bind the existing Transfer algorithm to the audited depth-layout engine."""
from common import *
import difflib

def main():
    source=Path(__file__).parent/'transfer_backend_fixed.py'
    old=source.read_text(encoding='utf-8')
    needle='from optimized_oram import (Config,Tree,PRF,Server,Transport,Record,Reject,Overflow,'
    assert old.count(needle)==1
    new=old.replace(needle,'from heterogeneous_oram import (Config,Tree,PRF,Server,Transport,Record,Reject,Overflow,')
    target=Path(__file__).parent/'ir_transfer.py'
    target.write_text(new,encoding='utf-8')
    diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=source.name,tofile=target.name))
    (PACKAGE/'ir_transfer_engine_binding.diff').write_text(diff,encoding='utf-8')
    save(PACKAGE/'results/ir_transfer_build.json',dict(source_sha256=sha(source),target_sha256=sha(target),generator_sha256=sha(__file__),change='one import binding; the complete Transfer body is unchanged'))
    print(json.dumps(dict(import_bindings_changed=1,target=str(target))))

if __name__=='__main__':main()
