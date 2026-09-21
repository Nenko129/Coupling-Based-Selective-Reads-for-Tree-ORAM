from common import *
import composition_runtime as runtime
from workloads import payload

def main():
    ff=runtime.frontends;Original=ff.Backend;rows=[]
    for family in ('free_raw','free_compressed','rho'):
        for kind in ('deferred','sde','ring','r0'):
            models=[]
            for measured in (False,True):
                if measured:runtime.install(None,R=128,capture=100000)
                else:ff.Backend=Original
                if family=='rho':
                    m=ff.RhoFront(kind,N=16,B=64,llc=2,rho=4,n=3,seed=19);bs=[m.front,m.back]
                    ans=m.run([(i%16,payload(i%16,i+1,64) if i%2 else None) for i in range(40)])
                else:
                    m=ff.FreecursiveFront(kind,N=16,B=64,compressed=family=='free_compressed',plb=4,seed=19);bs=[m.backend]
                    ans=[m.access(i%16,payload(i%16,i+1,64) if i%2 else None) for i in range(40)]
                models.append((m,bs,ans))
            a,ba,aa=models[0];b,bb,ab=models[1];assert aa==ab and a.metrics==b.metrics
            for x,y in zip(ba,bb):
                assert x.io.events==y.io.events
                assert (x.tree.root,x.tree.stash,x.tree.g,x.tree.t)==(y.tree.root,y.tree.stash,y.tree.g,y.tree.t)
                assert (x.p.calls,x.p.samples,x.p.nonces)==(y.p.calls,y.p.samples,y.p.nonces)
            rows.append(dict(family=family,kind=kind,exact_transcripts=True,exact_completed_state=True))
    save(PACKAGE/'results/composition_meter_regression.json',dict(status='passed',rows=rows,scope='metering transplant; reuses prior frontend contract and functional tests'))
    print(json.dumps(dict(status='passed',paired_configs=len(rows))))
if __name__=='__main__':main()
