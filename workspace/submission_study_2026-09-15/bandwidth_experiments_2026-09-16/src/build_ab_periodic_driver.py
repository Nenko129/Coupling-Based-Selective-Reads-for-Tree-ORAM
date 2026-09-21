"""Derive an aligned CB driver without altering the completed pilot driver."""
from common import *
import difflib


def main():
    source=Path(__file__).parent/'run_ab_cb.py';text=source.read_text();original=text
    replacements=[
        ("    setup=b.io.snapshot();setup_peak=b.tree.max_boundary\n", """    setup=b.io.snapshot();setup_peak=b.tree.max_boundary
    period=s['period_slots'];assert period==b.c.A*(1<<b.c.L)
    assert s['warmup']*s['slots_per_request']==period
    assert s['requests']*s['slots_per_request']==4*period
    init_t=b.tree.t;pad=(-init_t)%period
    b.io.reset_meter();b.tree.logical_calls.reset();before=Counter(b.tree.cb_metrics);occupancy=Counter(c.occupancies)
    for _ in range(pad):c.tick()
    assert b.tree.t%period==0
    alignment=dict(public_slots=pad,start_t=init_t,end_t=b.tree.t,bill=b.io.snapshot(),schedule=b.tree.logical_calls.snapshot(),
        cb_metrics=dict(Counter(b.tree.cb_metrics)-before),boundary_stash_histogram=dict(Counter(c.occupancies)-occupancy))
"""),
        ("        offset+=len(part);progress(s,phase,completed=W,total=W)\n", """        assert (f.total+start)%period==0 and (f.total+c.clock)%period==0
        offset+=len(part);progress(s,phase,completed=W,total=W)
"""),
        ("        setup=setup,setup_peak_boundary_stash=setup_peak,phases=phases,bytes_per_request=m['total_bytes']/s['requests'],\n", """        setup=setup,setup_peak_boundary_stash=setup_peak,alignment=alignment,
        periodic_extension=dict(period_slots=period,warmup_complete_periods=1,measurement_complete_periods=4,no_steady_state_claim=True),
        phases=phases,bytes_per_request=m['total_bytes']/s['requests'],
"""),
        ("        measurement='same offered application requests and fixed public backend slot count; inclusive dirty LLC remains resident',\n",
         "        measurement='one aligned period warmup, four periods measurement; same offered application requests and fixed public slots; dirty LLC remains resident',\n")]
    for old,new in replacements:
        assert text.count(old)==1;text=text.replace(old,new)
    out=source.with_name('run_ab_periodic.py');out.write_text(text,encoding='utf-8')
    diff=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='run_ab_cb.py',tofile='run_ab_periodic.py'))
    source.with_name('ab_periodic_driver.diff').write_text(diff,encoding='utf-8')
    save(PACKAGE/'results/ab_periodic_driver_build.json',dict(status='generated',base_sha256=sha(source),output_sha256=sha(out),
        replacement_count=len(replacements),generator_sha256=sha(__file__)))


if __name__=='__main__':main()
