"""Isolated full-scale validation; previous failed checks remain unchanged."""
from common import *
import difflib


def main():
    source=Path(__file__).parent/'check_ab_paced_controlled.py';old=source.read_text(encoding='utf-8');text=old
    replacements=[
        ('import ab_cb_runtime as rt','import ab_dummy_first_runtime as rt'),
        ("    source=identity();rows=[]", "    source=identity();rows=[]\n    proof=json.loads((PACKAGE/'results/ab_dummy_first_checks.json').read_text())\n    assert proof['status']=='passed' and proof['source_hashes']==rt.identity()"),
        ("        phase='initializing';initial=None", "        phase='initializing';initial=None;c=None;b=None"),
        ("                error=traceback.format_exc(),source_hashes=source));raise", "                error=traceback.format_exc(),source_hashes=source,\n                final_clock=None if c is None else c.clock,completed=None if c is None else len(c.returned),\n                metrics=None if c is None else dict(c.metrics),queued=None if c is None else len(c.queue),\n                final_stash=None if b is None else len(b.tree.stash),\n                max_stash=None if b is None else b.tree.max_boundary));raise")]
    for before,after in replacements:
        assert text.count(before)==1;text=text.replace(before,after)
    text=text.replace('ab_paced_controlled','ab_dummy_first_controlled')
    out=source.with_name('check_ab_dummy_first_controlled.py');out.write_text(text,encoding='utf-8')
    out.with_suffix('.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),
        fromfile=source.name,tofile=out.name)),encoding='utf-8')
    save(PACKAGE/'results/ab_dummy_first_validation_build.json',dict(status='generated',source_sha256=sha(source),
        output_sha256=sha(out),generator_sha256=sha(__file__),old_sources_preserved=True))


if __name__=='__main__':main()
