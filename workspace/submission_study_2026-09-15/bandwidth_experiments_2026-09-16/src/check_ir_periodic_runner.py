"""Check alignment, real ledgers and paired work for all three IR backends."""
from common import *
from run_ir_periodic import run,identity
from analyze_ir_dwb import bill,expected_answers
import copy


def check(r):
    s=r['spec'];c,=r['configs'];period=c['A']*2**c['L'];a=r['alignment']
    assert s['period_slots']==period==r['periodic_extension']['period_slots']
    assert a['start_t']==c['N'] and a['public_slots']==(-c['N'])%period
    assert a['end_t']==c['N']+a['public_slots'] and a['end_t']%period==0
    assert a['schedule']['slots']==a['public_slots']
    bill(r['setup']);bill(a['bill']);assert r['setup']['next_sequence']==a['bill']['first_sequence']
    seq=a['bill']['next_sequence'];clock=a['public_slots']
    for phase,multiple in [('warmup',1),('measurement',4)]:
        p=r['phases'][phase];b,=p['bills'];bill(b)
        assert b['first_sequence']==seq;seq=b['next_sequence']
        assert p['start_clock']==clock and p['end_clock']==clock+multiple*period;clock=p['end_clock']
        assert (c['N']+p['start_clock'])%period==0 and (c['N']+p['end_clock'])%period==0
        assert p['public_slots']==multiple*period==p['schedules'][0]['slots']
        assert p['requests']*s['slots_per_request']==p['public_slots']
    assert r['final_clock']['t']==c['N']+clock
    assert r['answer_sha256']==expected_answers(r['trace']['path'],r['trace']['sha256'],s['N'],s['B'],
        s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    return True


def main():
    base=json.loads((PACKAGE/'specs/pilot_ir_periodic_sde.json').read_text());rows=[]
    source=identity()
    for kind in ('path','deferred','sde'):
        for enabled in (False,True):
            s=dict(base,id=f'pilot_ir_periodic_{kind}_dwb{int(enabled)}',kind=kind,dwb=enabled)
            p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
            r=json.loads(p.read_text()) if p.exists() else run(s)
            assert r['spec']==s and r['source_hashes']==source and check(r);rows.append(r)
    for enabled in (False,True):
        group=[r for r in rows if r['spec']['dwb']==enabled]
        for r in group:
            assert r['answer_sha256']==group[0]['answer_sha256']
            for phase in ('warmup','measurement'):
                assert r['phases'][phase]['schedules']==group[0]['phases'][phase]['schedules']
                assert r['phases'][phase]['frontend_metrics']==group[0]['phases'][phase]['frontend_metrics']
    for kind in ('path','deferred'):
        group=[r for r in rows if r['spec']['kind']==kind]
        assert group[0]['bytes_per_request']==group[1]['bytes_per_request']
    negative=[]
    for label,edit in [('misaligned_start',lambda r:r['alignment'].__setitem__('end_t',1)),
        ('missing_alignment_charge',lambda r:r['alignment']['bill'].__setitem__('total_bytes',0)),
        ('short_measurement',lambda r:r['phases']['measurement'].__setitem__('end_clock',1))]:
        r=copy.deepcopy(rows[-1]);edit(r)
        try:check(r)
        except AssertionError:negative.append(label)
        else:raise AssertionError('corrupted periodic run accepted')
    assert source==identity()
    save(PACKAGE/'results/ir_periodic_runner_checks.json',dict(status='passed',source_hashes=source,
        cases=[dict(id=r['spec']['id'],bytes_per_request=r['bytes_per_request'],aligned=True) for r in rows],
        rejected=negative,checker_sha256=sha(__file__),pilot_only=True,no_steady_state_claim=True))
    print(json.dumps(dict(status='passed',cases=len(rows),negative=len(negative))))


if __name__=='__main__':main()
