"""Same unified map frontend with an explicit public tree-height parameter.

Generated from the frozen Freecursive constructor; no lookup or map algorithm
is replaced. One record is admitted every A public slots during initialization.
The remaining A-1 slots are ordinary CB dummy Transfers, billed to setup.
Backend is bound explicitly by the new driver; earlier drivers are unchanged.
"""
from frontends import *
from ir_dwb_controller import StepwiseFront


class PacedGeometryFront(FreecursiveFront):
    def __init__(self,kind='sde',N=256,B=64,X=None,beta=14,compressed=True,plb=4,seed=0,profile=(4,3,4),L=None):
        self.N=N;self.B=B;self.compressed=compressed;self.beta=beta
        self.X=X or (32 if compressed else B//4)
        need((64+self.X*beta<=8*B) if compressed else (4*self.X<=B),'map packing')
        self.counts=[N]
        while self.counts[-1]>1:self.counts.append(math.ceil(self.counts[-1]/self.X))
        self.offsets=[];total=0
        for n in self.counts:self.offsets.append(total);total+=n
        self.total=total;self.capacity=plb;self.cache=OrderedDict();self.pinned=set()
        self.L=max(1,math.ceil(math.log2(2*total/3))) if L is None else L
        self.leaves=Leaves(self.L,seed,b'FREE-MAP');self.padding=Leaves(self.L,seed,b'FREE-DUMMY')
        Z,A,S=profile
        self.backend=Backend(kind,self.L,total,B=B,Z=Z,A=A,S=S,R=128)
        self.top=[self.leaves.named('top-init',i) for i in range(self.counts[-1])]
        self.metrics=Counter();self.dead=False
        for level,n in enumerate(self.counts):
            for i in range(n):
                a=self.addr(level,i)
                payload=initial_payload(i,B) if level==0 else self.encode_map(level,i,0,[0]*self.X)
                self.backend.tick(None,self.padding.fresh('init'),admit=(a,self.initial_leaf(level,i),payload))
                for _ in range(A-1):self.backend.tick(None,self.padding.fresh('init-cadence'))
        self.metrics.clear()


class PacedGeometryStepwiseFront(StepwiseFront):
    def __init__(self,*args,**kwargs):
        kwargs['compressed']=False
        PacedGeometryFront.__init__(self,*args,**kwargs)
        self.pending_writeback=None
