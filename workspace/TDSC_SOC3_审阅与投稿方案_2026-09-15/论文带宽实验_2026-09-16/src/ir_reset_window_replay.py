"""Logical scheduling diagnosis only; never supplies measured bandwidth.

The existing staged frontend/controller run on a plaintext ownership oracle.
It checks every old leaf and returned payload, and cross-checks the original
encrypted run's observable schedules/metrics before exploring a public tail.
The O(N) dictionary is a test oracle, not a proposed trusted ORAM structure.
"""
from common import *
from types import SimpleNamespace
from composition_runtime import Schedule
import frontends
from dwb_compressed_frontend import StagedCompressedFront
from ir_compressed_controller import CompressedController,identity as runtime_identity
from run_ir_compressed_periodic import delta
from workloads import stored_trace,payload
from frontends import initial_payload


class LogicalBackend:
    def __init__(self,kind,L,N,B=64,Z=4,A=3,S=4,R=128,tree=0,key=None):
        self.c=SimpleNamespace(kind=kind,L=L,N=N,B=B,Z=Z,A=A,S=S,R=R)
        self.tree=SimpleNamespace(t=0,dead=False,logical_calls=Schedule())
        self.records={}

    def tick(self,remove,oldleaf,admit=None,*,replace=None):
        assert 0<=oldleaf<1<<self.c.L and (admit is None or replace is None)
        prior=None
        if remove is not None:
            leaf,prior=self.records.pop(remove)
            assert leaf==oldleaf and 0<=remove<self.c.N
        if replace is not None:
            assert remove is not None
            leaf,fn=replace;admit=(remove,leaf,fn(prior))
        if admit is not None:
            a,l,p=admit
            assert a not in self.records and 0<=a<self.c.N and 0<=l<1<<self.c.L and len(p)==self.c.B
            self.records[a]=(l,p)
        self.tree.t+=1
        self.tree.logical_calls.append(dict(remove=remove,admit=None if admit is None else admit[0]))
        return prior


def create(s):
    frontends.Backend=LogicalBackend
    f=StagedCompressedFront(s['kind'],N=s['N'],B=s['B'],X=s['X'],beta=s['beta'],
        plb=s['plb'],seed=s['oram_seed'],profile=s['profile'])
    return CompressedController(f,sets=s['llc_sets'],ways=s['llc_ways'],dwb=s['dwb'])


def requests_for(s,seq,truth,offset):
    requests=[];expected=[]
    for i,(a,v) in enumerate(seq):
        value=None if v is None else payload(a,v,s['B'])
        requests.append(dict(id=offset+i,address=a,value=value));expected.append((offset+i,truth[a]))
        if value is not None:truth[a]=value
    return requests,expected


def metrics_delta(c,before):
    return {k:v for k,v in (c.metrics-before).items() if v}


def replay(s,tail_periods=0):
    c=create(s);f=c.front;b=f.backend;period=s['period_slots']
    assert b.tree.t==f.total and period==b.c.A*(1<<b.c.L)
    for _ in range((-f.total)%period):c.tick()
    seq,trace=stored_trace(s['N'],s['warmup']+s['requests'],s['trace_seed'],s['workload'])
    truth={a:initial_payload(a,s['B']) for a in range(s['N'])};phases=[];answer=hashlib.sha256();offset=0
    for phase,part in [('warmup',seq[:s['warmup']]),('measurement',seq[s['warmup']:])]:
        requests,expected=requests_for(s,part,truth,offset)
        W=len(part)*s['slots_per_request'];tail=tail_periods*period
        b.tree.logical_calls.reset();before=c.metrics.copy();map_before=f.metrics.copy()
        start=len(c.returned);clock=c.clock;start_t=b.tree.t;reset_start=f.reset_snapshot()
        boundary=None;clearance=None;cut_trace=[]
        for i in range(W+tail):
            j=i//s['arrival_gap']
            c.tick([requests[j]] if i%s['arrival_gap']==0 and j<len(requests) else [])
            count=len(c.returned)-start
            if count==len(requests) and clearance is None:clearance=i+1
            if W-64<=i<min(W+tail,W+128):
                cut_trace.append(dict(slot=i+1,completed=count,queued=len(c.queue),
                    foreground=bool(c.work),reset=f.reset_snapshot()))
            if i+1==W:
                boundary=dict(completed=count,queued=len(c.queue),foreground=bool(c.work),reset=f.reset_snapshot(),
                    controller_metrics=dict(c.metrics),map_metrics=dict(f.metrics),schedule=b.tree.logical_calls.snapshot())
        actual=c.returned[start:]
        assert [(i,v) for i,v,t in actual]==expected[:len(actual)]
        for i,v,t in actual:answer.update(v)
        m=metrics_delta(c,before)
        m.update(unfinished_foreground=int(c.work is not None)+len(c.queue),
            dirty_resident=sum(x.dirty for group in c.sets for x in group.values()),dwb_pending=c.candidate is not None,
            group_reset_pending=f.pending_reset is not None,
            group_reset_slots=sum(m.get(k,0) for k in ('foreground_group_reset_slots','dwb_group_reset_slots','maintenance_reset_slots')))
        phases.append(dict(phase=phase,requests=len(part),completed=len(actual),public_slots=W+tail,
            frontend_metrics=m,map_metrics=delta(f.metrics,map_before),reset_start=reset_start,reset_end=f.reset_snapshot(),
            schedule=b.tree.logical_calls.snapshot(),start_clock=clock,end_clock=c.clock,start_t=start_t,end_t=b.tree.t,
            original_cut=boundary,clearance_slot=clearance,tail_slots_to_clear=None if clearance is None else max(0,clearance-W),cut_trace=cut_trace))
        offset+=len(part)
        if len(actual)!=len(part):break
    return dict(spec=s,trace=trace,phases=phases,answer_sha256=answer.hexdigest(),logical_replay=True,
        actual_ciphertext_execution=False,bytes_measured=False,tail_periods=tail_periods)


def nonzero(mapping):return {k:v for k,v in mapping.items() if v!=0}


def check_original(model,r):
    assert model['spec']==r['spec'] and model['tail_periods']==0
    if r['status']=='passed':
        assert model['answer_sha256']==r['answer_sha256'] and model['trace']==r['trace']
        assert len(model['phases'])==2
        for x in model['phases']:
            y=r['phases'][x['phase']]
            assert x['schedule']==y['schedules'][0]
            for key in ('frontend_metrics','map_metrics'):assert nonzero(x[key])==nonzero(y[key]),(x['phase'],key)
            for key in ('start_clock','end_clock','start_t','end_t','reset_start','reset_end'):assert x[key]==y[key]
    else:
        x=model['phases'][-1]
        assert r['phase']==x['phase'] and r['completed_this_phase']==x['completed']
        assert x['schedule']==r['schedule'] and x['reset_end']==r['reset']
        assert nonzero(x['original_cut']['controller_metrics'])==nonzero(r['controller_metrics'])
        assert nonzero(x['original_cut']['map_metrics'])==nonzero(r['map_metrics'])
        assert x['end_t']==r['t'] and x['end_clock']==r['clock']
        # No partial correctness digest in these encrypted failures: a model
        # digest is deliberately not presented as an encrypted-run digest.
        assert r['error'].strip().splitlines()[-1]=='AssertionError: fixed horizon did not complete every request'


def main():
    snapshot=PACKAGE/'results/ir_compressed_completed_snapshot.json';frozen=json.loads(snapshot.read_text())
    refs=[];grouped={}
    for ref in frozen['receipts']:
        p=PACKAGE/ref['path'];assert sha(p)==ref['sha256'];r=json.loads(p.read_text())
        s=r['spec']
        if s.get('map_mode')!='compressed' or not s['dwb'] or s['workload']!='hot90':continue
        key=(s['beta'],s['trace_seed']);grouped.setdefault(key,[]).append((ref,r));refs.append(ref)
    assert len(refs)==30 and len(grouped)==10
    cases=[]
    for key,items in sorted(grouped.items()):
        assert {r['spec']['kind'] for ref,r in items}=={'path','deferred','sde'}
        s=dict(items[0][1]['spec']);model=replay(s)
        for ref,r in items:
            same=dict(model,spec=r['spec']);check_original(same,r)
        counterfactual=replay(s,tail_periods=1)
        assert len(counterfactual['phases'])==2
        assert all(x['completed']==x['requests'] for x in counterfactual['phases'])
        cases.append(dict(beta=key[0],seed=key[1],references=[ref for ref,r in items],original=model,counterfactual=counterfactual))
        print(json.dumps(dict(beta=key[0],seed=key[1],original_completed=[x['completed'] for x in model['phases']],
            guarded_clearance=[x['tail_slots_to_clear'] for x in counterfactual['phases']])),flush=True)
    save(PACKAGE/'results/ir_reset_window_replay.json',dict(status='passed',source_snapshot_sha256=sha(snapshot),
        source_hashes=runtime_identity(),checker_sha256=sha(__file__),cases=cases,encrypted_receipts_checked=30,
        actual_bandwidth=False,security_admission=False,scope='Logical frontend/controller replay and one public-period tail counterfactual; original raw runs unchanged'))


if __name__=='__main__':main()
