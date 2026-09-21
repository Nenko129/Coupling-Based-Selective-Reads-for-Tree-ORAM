"""New driver revision; preserve the failed unpaced plan and all old sources."""
from common import *
import difflib


def main():
    base=Path(__file__).parent/'run_ab_periodic.py';old=base.read_text();text=old
    edits=[('from ab_geometry_frontend import GeometryStepwiseFront',
            'import ab_paced_frontend as bootstrap\nfrom ab_paced_frontend import PacedGeometryStepwiseFront as GeometryStepwiseFront'),
        ('def identity():return dict(runtime=rt.identity(),driver=sha(__file__))',
            'def identity():return dict(runtime=rt.identity(),driver=sha(__file__),bootstrap_frontend=sha(bootstrap.__file__))'),
        ("    progress(s,'initializing')", "    bootstrap.Backend=rt.Backend\n    assert s['initialization_stride']==s['profile'][1]\n    progress(s,'initializing')"),
        ('    setup=b.io.snapshot();setup_peak=b.tree.max_boundary',
            "    setup=b.io.snapshot();setup_peak=b.tree.max_boundary\n    assert b.tree.t==f.total*s['initialization_stride'] and b.tree.births==f.total\n    initialization=dict(stride=s['initialization_stride'],initial_clock=b.tree.t,admitted_records=b.tree.births,\n        schedule=b.tree.logical_calls.snapshot(),useful_schedule=b.tree.logical_calls.useful.snapshot())"),
        ('        assert (f.total+start)%period==0 and (f.total+c.clock)%period==0',
            '        assert (init_t+start)%period==0 and (init_t+c.clock)%period==0'),
        ('        setup=setup,setup_peak_boundary_stash=setup_peak,alignment=alignment,',
            '        setup=setup,setup_peak_boundary_stash=setup_peak,alignment=alignment,initialization=initialization,')]
    for before,after in edits:
        assert text.count(before)==1;text=text.replace(before,after)
    out=base.with_name('run_ab_paced_periodic.py');out.write_text(text,encoding='utf-8')
    base.with_name('ab_paced_driver.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),
        fromfile=base.name,tofile=out.name)),encoding='utf-8')
    save(PACKAGE/'results/ab_paced_driver_build.json',dict(status='generated',base_sha256=sha(base),output_sha256=sha(out),
        generator_sha256=sha(__file__),controlled_edits=len(edits),old_evidence_preserved=True))


if __name__=='__main__':main()
