"""Public, transactional DeadQ ownership model with bounded joint rebuilds.

This is an executable allocator contract, NOT an encrypted ORAM implementation.
No security/capacity theorem for CB, native-AB reproduction, or bandwidth result
is implied. A real engine must authenticate every public input and final ACK.
"""
from dataclasses import dataclass
import copy, hashlib, json


class Rejected(Exception):pass


def require(ok, why):
    if not ok:raise Rejected(why)


def reverse(x, bits):
    return int(f'{x:0{bits}b}'[::-1],2)


@dataclass(frozen=True)
class Geometry:
    buckets:int=4
    base:int=3
    extra:int=1
    component_cap:int=3
    queue_cap:int=8

    def __post_init__(self):
        require(self.buckets>=2 and self.buckets&(self.buckets-1)==0,'power-of-two level')
        require(self.base>=1 and 1<=self.extra<=self.base,'slot counts')
        require(1<=self.component_cap<=self.buckets and self.queue_cap>=self.extra,'public limits')


class Allocator:
    def __init__(self,g=Geometry()):
        self.g=g;self.maps=[[i*g.base+j for j in range(g.base)] for i in range(g.buckets)]
        self.valid=[[True]*g.base for _ in range(g.buckets)]
        self.owner=[(i,j) for i in range(g.buckets) for j in range(g.base)]
        self.version=[0]*len(self.owner);self.epoch=[0]*g.buckets;self.queue=[]
        self.scheduled=0;self.dead=False;self.pending=None;self.events=[]
        self.invariant()

    def component(self,b):
        members={b}
        while True:
            old=len(members)
            for p,owner in enumerate(self.owner):
                if owner is None:continue
                home=p//self.g.base;logical=owner[0]
                if home in members or logical in members:members.update((home,logical))
            if len(members)==old:return members

    def invariant(self):
        g=self.g
        assert len(self.owner)==g.buckets*g.base==len(self.version)
        active={}
        for b in range(g.buckets):
            assert len(self.maps[b]) in (g.base,g.base+g.extra)
            assert len(self.valid[b])==len(self.maps[b])
            assert len(self.component(b))<=g.component_cap
            for j,(p,valid) in enumerate(zip(self.maps[b],self.valid[b])):
                assert 0<=p<len(self.owner)
                if valid:
                    assert p not in active
                    active[p]=(b,j)
        assert all(o==active.get(p) for p,o in enumerate(self.owner))
        assert len(self.queue)<=g.queue_cap
        assert len({p for p,v in self.queue})==len(self.queue)
        for p,v in self.queue:assert self.owner[p] is None and self.version[p]==v
        assert len(active)+sum(o is None for o in self.owner)==g.buckets*g.base

    def digest(self):
        value=dict(maps=self.maps,valid=self.valid,owner=self.owner,version=self.version,
            epoch=self.epoch,queue=self.queue,scheduled=self.scheduled)
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def _check_ready(self):
        require(not self.dead,'fail-stop allocator')
        require(self.pending is None,'single serial transaction')

    def _queue_dead(self,p):
        assert self.owner[p] is None
        if len(self.queue)<self.g.queue_cap:
            assert all(q!=p for q,_ in self.queue)
            self.queue.append((p,self.version[p]))

    def _consume(self,b,j):
        require(0<=b<self.g.buckets and 0<=j<len(self.maps[b]),'logical address')
        require(self.valid[b][j],'slot already consumed')
        p=self.maps[b][j];assert self.owner[p]==(b,j)
        self.valid[b][j]=False;self.owner[p]=None;self.version[p]+=1
        self._queue_dead(p)
        return dict(operation='consume',bucket=b,slot=j,physical=p)

    def _gather(self,b):
        require(0<=b<self.g.buckets,'gather bucket bounds')
        queued={p for p,v in self.queue};added=[]
        for p in range(b*self.g.base,(b+1)*self.g.base):
            if len(self.queue)==self.g.queue_cap:break
            if self.owner[p] is None and p not in queued:
                self._queue_dead(p);queued.add(p);added.append(p)
        return dict(operation='gather',physical_home=b,added=added)

    def _rebuild(self,b,scheduled):
        g=self.g;require(0<=b<g.buckets,'bucket bounds')
        bits=g.buckets.bit_length()-1
        if scheduled:require(b==reverse(self.scheduled%g.buckets,bits),'scheduled order')
        warmed=self.scheduled>=g.buckets
        group=self.component(b);homes={p for p in range(len(self.owner)) if p//g.base in group}
        live=[(logical,j,p) for logical in sorted(group) for j,p in enumerate(self.maps[logical]) if self.valid[logical][j]]
        # Full connected-component closure: no live foreign owner of its homes,
        # and none of its live objects occupies a home outside this component.
        assert all(o is None or o[0] in group for p,o in enumerate(self.owner) if p in homes)
        assert all(p in homes for _,_,p in live)
        before=self.digest()
        self.queue=[q for q in self.queue if q[0] not in homes]
        for p in homes:self.owner[p]=None
        # Caller stages/validates its real records first, then each bucket keeps
        # <= C real records in base >= C slots. This model records only public
        # slot ownership; it cannot certify that the caller preserves payloads.
        for logical in sorted(group):
            self.epoch[logical]+=1
            self.maps[logical]=list(range(logical*g.base,(logical+1)*g.base))
            self.valid[logical]=[True]*g.base
            for j,p in enumerate(self.maps[logical]):
                self.version[p]+=1;self.owner[p]=(logical,j)
        reason='warmup';borrowed=[]
        if warmed:
            reason='empty_or_short_queue'
            if len(self.queue)>=g.extra:
                prefix=self.queue[:g.extra];combined={b}
                # Rebuilt members now have only home slots, so their old edges
                # no longer couple them. Test every proposed donor component.
                for p,v in prefix:
                    require(self.owner[p] is None and self.version[p]==v,'stale queue lease')
                    combined.update(self.component(p//g.base))
                if len(combined)>g.component_cap:reason='component_cap'
                else:
                    reason='expanded';del self.queue[:g.extra]
                    for p,v in prefix:
                        j=len(self.maps[b]);self.maps[b].append(p);self.valid[b].append(True)
                        self.version[p]+=1;self.owner[p]=(b,j);borrowed.append(p)
        if scheduled:self.scheduled+=1
        return dict(operation='rebuild',bucket=b,scheduled=scheduled,warmed=warmed,
            rebuilt=sorted(group),staged_logical_slots=live,physical_writes=sorted(homes)+borrowed,
            borrowed=borrowed,result=reason,before_digest=before,
            collateral_buckets=len(group)-1,staged_public_slot_count=len(live),
            new_logical_slots=len(self.maps[b]))

    def prepare(self,operation,*args):
        self._check_ready();work=copy.deepcopy(self)
        try:
            if operation=='consume':event=work._consume(*args)
            elif operation=='gather':event=work._gather(*args)
            elif operation=='rebuild':event=work._rebuild(*args)
            elif operation=='rebuild_consume':
                b,j,scheduled=args
                rebuilt=work._rebuild(b,scheduled)
                consumed=work._consume(b,j)
                event=dict(operation='rebuild_consume',rebuild=rebuilt,consume=consumed)
            else:event=None
            require(event is not None,'unknown public operation');work.invariant()
            token=work.digest()
            self.pending=(token,work,event)
            return dict(event=copy.deepcopy(event),expected_state_digest=token)
        except Exception:
            self.dead=True;raise

    def commit(self,authenticated_ack):
        require(not self.dead,'fail-stop allocator')
        require(self.pending is not None,'no prepared transaction')
        token,work,event=self.pending
        if authenticated_ack!=token:
            self.pending=None;self.dead=True;raise Rejected('failed final ACK')
        # A string comparison is only the model boundary. The production caller
        # must verify an authenticated reply binding this complete state digest.
        history=self.events+[event]
        self.__dict__.update(work.__dict__);self.pending=None;self.events=history
        self.invariant();return event

    def apply(self,operation,*args):
        transaction=self.prepare(operation,*args)
        return self.commit(transaction['expected_state_digest'])

    def normalized(self):
        """State key for abstract reachability; absolute generations renamed.

        Queue leases always equal current versions by the checked invariant;
        stale-message/fail-stop behavior is tested separately, not erased here.
        """
        return (tuple(tuple(x) for x in self.maps),tuple(tuple(x) for x in self.valid),
            tuple(self.owner),tuple(p for p,v in self.queue),
            min(self.scheduled,self.g.buckets)+(self.scheduled%self.g.buckets if self.scheduled>=self.g.buckets else 0))
