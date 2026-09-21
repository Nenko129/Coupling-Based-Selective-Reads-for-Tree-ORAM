"""Serial inclusive set-LRU LLC and a public, fixed-horizon slot scheduler.

It measures bandwidth, not simulated CPU cycles. DWB chooses each set's LRU
entry in round-robin order, and only uses slots with no ready foreground work.
"""
from common import *
from collections import OrderedDict,Counter,deque
from dataclasses import dataclass
from dwb_staged_frontend import StagedRawMapFront


@dataclass
class Line:
    address:int
    payload:bytes
    version:int=0
    dirty:bool=False


class StepwiseFront(StagedRawMapFront):
    def _request_steps(self,a,value):
        old,new=yield from self._reserve_staged(0,a)
        prior=self.backend.tick(a,old,replace=(new,lambda p:p if value is None else value))
        yield dict(type='data',level=0,address=a,previous=prior)

    def step(self,a,value=None):
        if self.dead:raise RuntimeError('fail-stop stepwise frontend')
        steps=self._request_steps(a,value);before=self.backend.tree.t
        try:
            event=next(steps)
            assert self.backend.tree.t==before+1
            return event
        except Exception:
            self.dead=True;self.backend.tree.dead=True;raise
        finally:steps.close()

    def dummy(self):
        if self.dead:raise RuntimeError('fail-stop stepwise frontend')
        try:self.backend.tick(None,self.padding.fresh('public-scheduler-idle'))
        except Exception:
            self.dead=True;self.backend.tree.dead=True;raise


class Controller:
    def __init__(self,front,sets=8,ways=2,dwb=False):
        assert sets>=1 and ways>=1
        self.front=front;self.sets=[OrderedDict() for _ in range(sets)];self.ways=ways
        self.enabled=dwb;self.cursor=0;self.candidate=None;self.work=None;self.queue=deque()
        self.metrics=Counter();self.clock=0;self.dead=False;self.returned=[]

    def group(self,a):return self.sets[a%len(self.sets)]

    def valid_candidate(self):
        if self.candidate is None:return False
        line,version,data=self.candidate;group=self.group(line.address)
        return bool(group) and next(iter(group))==line.address and group.get(line.address) is line and line.dirty and line.version==version and line.payload==data

    def drop_candidate(self,reason):
        if self.candidate is not None:
            self.metrics['dwb_cancelled_'+reason]+=1;self.candidate=None

    def complete_request(self,req,prior):
        line=self.group(req['address'])[req['address']]
        if req['value'] is not None:
            line.payload=req['value'];line.version+=1;line.dirty=True
        self.group(req['address']).move_to_end(req['address'])
        self.returned.append((req['id'],prior,self.clock));self.metrics['application_completed']+=1

    def prepare_foreground(self):
        while self.work is None and self.queue:
            req=self.queue.popleft();a=req['address'];group=self.group(a)
            if a in group:
                self.metrics['llc_hits']+=1;self.complete_request(req,group[a].payload);continue
            self.metrics['llc_misses']+=1
            victim=next(iter(group.values())) if len(group)>=self.ways else None
            if victim is not None:
                self.metrics['llc_evictions']+=1
                if self.candidate is not None and self.candidate[0] is victim:self.drop_candidate('normal_eviction')
            if victim is not None and victim.dirty:
                self.work=dict(req=req,victim=victim,phase='writeback')
            else:
                if victim is not None:del group[victim.address]
                self.work=dict(req=req,victim=None,phase='fetch')

    def foreground_slot(self):
        w=self.work;req=w['req'];self.metrics['foreground_slots']+=1
        if w['phase']=='writeback':
            line=w['victim'];event=self.front.step(line.address,line.payload)
            if event['type']=='data':
                line.dirty=False;del self.group(line.address)[line.address]
                w.update(victim=None,phase='fetch');self.metrics['foreground_writebacks']+=1
        else:
            event=self.front.step(req['address'])
            if event['type']=='data':
                a=req['address'];group=self.group(a);assert len(group)<self.ways
                group[a]=Line(a,event['previous']);self.complete_request(req,event['previous']);self.work=None
        self.metrics['foreground_'+event['type']+'_slots']+=1

    def idle_slot(self):
        if not self.enabled:
            self.front.dummy();self.metrics['dummy_slots']+=1;return
        if self.candidate is not None and not self.valid_candidate():self.drop_candidate('candidate_changed')
        if self.candidate is None:
            for _ in self.sets:
                group=self.sets[self.cursor];self.cursor=(self.cursor+1)%len(self.sets)
                if group:
                    line=next(iter(group.values()))
                    if line.dirty:
                        self.candidate=(line,line.version,line.payload);self.metrics['dwb_started']+=1;break
        if self.candidate is None:
            self.front.dummy();self.metrics['dummy_slots']+=1;return
        line,version,value=self.candidate
        event=self.front.step(line.address,value);self.metrics['dwb_'+event['type']+'_slots']+=1
        if event['type']=='data':
            assert self.valid_candidate()
            line.dirty=False;self.candidate=None;self.metrics['dwb_completed']+=1

    def tick(self,arrivals=()):
        if self.dead:raise RuntimeError('fail-stop controller')
        try:
            self.queue.extend(arrivals);self.prepare_foreground()
            if self.candidate is not None and not self.valid_candidate():self.drop_candidate('candidate_changed')
            before=self.front.backend.tree.t
            if self.work is not None:self.foreground_slot()
            else:self.idle_slot()
            assert self.front.backend.tree.t==before+1
            self.metrics['public_slots']+=1;self.clock+=1
        except Exception:
            self.dead=True;self.front.dead=True;self.front.backend.tree.dead=True;raise

    def run_window(self,requests,gap,slots):
        assert gap>=1 and slots>=(len(requests)-1)*gap+1
        assert self.work is None and not self.queue
        before=self.metrics.copy();start=len(self.returned)
        for i in range(slots):
            j=i//gap
            self.tick([requests[j]] if i%gap==0 and j<len(requests) else [])
        result=dict(Counter(self.metrics)-before)
        result.update(unfinished_foreground=int(self.work is not None)+len(self.queue),
                      dirty_resident=sum(x.dirty for g in self.sets for x in g.values()),
                      dwb_pending=self.candidate is not None)
        answers=self.returned[start:]
        assert len(answers)==len(requests) and result['unfinished_foreground']==0,'fixed horizon did not complete every request'
        return answers,result
