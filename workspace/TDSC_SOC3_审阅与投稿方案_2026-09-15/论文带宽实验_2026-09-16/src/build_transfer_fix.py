from common import *
import difflib

def main():
    source=COMPOSITION/'transfer_backend.py';old=source.read_text(encoding='utf-8')
    bad="                need(a not in self.stash,'duplicate admission in stash')"
    good="                if c.kind!='path':need(a not in self.stash,'duplicate admission in stash')"
    assert old.count(bad)==1
    new=old.replace(bad,good)
    target=Path(__file__).parent/'transfer_backend_fixed.py';target.write_text(new,encoding='utf-8')
    diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen/transfer_backend.py',tofile='evaluation/transfer_backend_fixed.py'))
    (PACKAGE/'transfer_stash_replacement_fix.diff').write_text(diff,encoding='utf-8')
    save(PACKAGE/'results/transfer_fix_identity.json',dict(source_sha256=sha(source),fixed_sha256=sha(target),
         change='Path duplicate admission must use the pool after removal, not stale self.stash; existing Path pool duplicate guard retained'))
if __name__=='__main__':main()
