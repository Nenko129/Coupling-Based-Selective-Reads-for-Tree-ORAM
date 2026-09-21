"""Create a period-aligned driver and predeclare the longer IR validation batch."""
from common import *
import difflib,importlib


def main():
    base=Path(__file__).parent/'run_ir_dwb.py';old=base.read_text(encoding='utf-8')
    needle="    setup=b.io.snapshot();seq,trace=stored_trace(s['N'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])"
    assert old.count(needle)==1
    replacement="""    setup=b.io.snapshot()
    period=s['period_slots'];assert period==b.c.A*(1<<b.c.L)
    assert s['warmup']*s['slots_per_request']==period
    assert s['requests']*s['slots_per_request']==4*period
    init_t=b.tree.t;pad=(-init_t)%period
    b.io.reset_meter();b.tree.logical_calls.reset();progress(s,'period_alignment',completed=0,total=pad)
    for _ in range(pad):c.tick()
    assert b.tree.t%period==0
    alignment=dict(public_slots=pad,start_t=init_t,end_t=b.tree.t,bill=b.io.snapshot(),schedule=b.tree.logical_calls.snapshot())
    seq,trace=stored_trace(s['N'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])"""
    new=old.replace(needle,replacement)
    needle="    m=phases['measurement']"
    assert new.count(needle)==1
    new=new.replace(needle,"""    assert (b.tree.t-phases['measurement']['public_slots'])%period==0 and b.tree.t%period==0
    m=phases['measurement']""")
    needle="        measurement='actual encrypted below-cache application frames at a fixed public slot horizon; dirty LLC lines may remain resident',"
    assert new.count(needle)==1
    new=new.replace(needle,"""        alignment=alignment,periodic_extension=dict(period_slots=period,warmup_complete_periods=1,measurement_complete_periods=4,
            no_steady_state_claim=True,path_uses_reference_window=s['kind']=='path'),
        measurement='actual encrypted frames: one aligned reference period warmup and four measured periods; dirty LLC lines may remain resident',""")
    target=Path(__file__).parent/'run_ir_periodic.py';assert not target.exists();target.write_text(new,encoding='utf-8')
    (PACKAGE/'ir_periodic_driver.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=base.name,tofile=target.name)),encoding='utf-8')
    driver=importlib.import_module('run_ir_periodic');source=driver.identity()
    original=json.loads((PACKAGE/'formal_ir_dwb_plan.json').read_text());specs=[]
    for s in original['specs']:
        if s['layout']!='depth':continue
        specs.append(dict(s,id=s['id'].replace('IRDWB_','IRPER_',1),warmup=1536,requests=6144,
            period_slots=12288,experiment_class='formal_ir_periodic'))
    path=PACKAGE/'formal_ir_periodic_plan.json';assert not path.exists()
    save(path,dict(specs=specs,source_hashes=source,
        design='depth layout x DWB off/on x Path/Deferred/SDE x uniform/hot90 x five seeds; validate the full integrated stack over aligned periods',
        selection='Both synthetic workloads and all three backends are retained; uniform/depth layout factorial remains in the finite-prefix batch.',
        warmup='Align the backend clock after full initialization using counted dummy slots, then one complete reference period with application requests.',
        measurement='Four complete reference periods: 49152 public slots and 6144 application requests. Path uses the same reference window, not a bit-reversal eviction period.',
        source_finite_plan_sha256=sha(PACKAGE/'formal_ir_dwb_plan.json'),predeclared_before_periodic_outcomes=True,
        no_steady_state_claim=True,no_latency_claim=True,native_full_paper_reproduction=False,
        dependencies=[dict(pid=22552,completion='results/ir_dwb_queue_completion.json')]))
    pilot=dict(specs[0],id='pilot_ir_periodic_sde',kind='sde',N=64,X=8,cached_levels=2,Z_by_depth=[4,4,2,2,3,4,4],
        warmup=24,requests=96,period_slots=192,trace_seed=977,oram_seed=1977,dwb=True,plb=3,experiment_class='pilot_ir_periodic')
    save(PACKAGE/'specs'/f"{pilot['id']}.json",pilot)
    save(PACKAGE/'results/ir_periodic_build.json',dict(base_sha256=sha(base),driver_sha256=sha(target),generator_sha256=sha(__file__),plan_sha256=sha(path)))
    print(json.dumps(dict(formal_runs=len(specs),pilot=pilot['id'])))


if __name__=='__main__':main()
