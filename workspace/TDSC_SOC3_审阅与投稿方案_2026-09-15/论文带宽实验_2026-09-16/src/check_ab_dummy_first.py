"""Independent functional oracle, local exact law and active rejection checks."""
from common import *
import random
import check_cb_engine as old
import ab_dummy_first_runtime as rt
from ab_dummy_first_policy import eligible_slots


def main():
    source=rt.identity();old.TransferConfig=rt.TransferConfig;old.TransferTree=rt.TransferTree
    old.eligible_slots=eligible_slots
    exact=old.local_exact();cases=[];rng=random.Random(887)
    trace=[(rng.randrange(64),rng.randrange(64),rng.randrange(2)) for _ in range(160)]
    for kind in ('ring','gc_ring','r0'):
        for C,S,Y,heterogeneous in ((5,3,0,False),(5,7,4,False),(5,5,5,False),(5,7,4,True)):
            for cut in (0,2):
                t,io,server,leaves,truth=old.create(kind,C,S,Y,cut,heterogeneous);io.reset_meter()
                for i,(a,leaf,write) in enumerate(trace):
                    value=hashlib.sha256(str(i).encode()).digest()*2 if write else truth[a]
                    assert t.transfer(a,leaves[a],replace=(leaf,lambda p,v=value:v))==truth[a]
                    leaves[a]=leaf;truth[a]=value
                    if i%40==0:old.inventory(t,io,server,truth,leaves)
                for i in range(80):t.transfer(None,0)
                old.inventory(t,io,server,truth,leaves);invoice=io.snapshot();old.check_bill(invoice)
                if Y==0:assert t.cb_metrics['green_promotions']==0
                cases.append(dict(kind=kind,C=C,S=S,Y=Y,heterogeneous=heterogeneous,cut=cut,
                    checked_transfers=240,metrics=dict(t.cb_metrics),bytes=invoice['total_bytes'],max_boundary=t.max_boundary))
    failures=[]
    for op in (old.h.OPEN_HEAD,old.h.READ_SLOTS,old.h.WRITE):
        t,io,server,leaves,truth=old.create('r0',5,5,5,2);fired=[];green=t.cb_metrics['green_promotions']
        def mutate(c,opcode,seq,stage,meta,request,response):
            if not fired and opcode==op and stage=='logical':
                fired.append(t.P.decryptions);return response[:-1]+bytes([response[-1]^1])
            return response
        io.mutator=mutate
        try:t.transfer(0,leaves[0],replace=(17,lambda p:p))
        except (old.h.Reject,old.cache.h.Reject):pass
        else:raise AssertionError('dummy-first corruption accepted')
        assert fired and t.dead and t.P.decryptions==fired[0] and t.cb_metrics['green_promotions']==green
        seq=io.wire_seq
        try:t.transfer(None,0)
        except old.h.Reject:pass
        else:raise AssertionError('dummy-first continued after rejection')
        assert io.wire_seq==seq;failures.append(op)
    assert sum(r['metrics'].get('green_promotions',0) for r in cases)>0
    assert sum(r['metrics'].get('zero_cover_buckets',0) for r in cases)>0
    assert rt.identity()==source
    save(PACKAGE/'results/ab_dummy_first_checks.json',dict(status='passed',source_hashes=source,
        functional_cases=cases,active_rejections=failures,local_exact=exact,checker_sha256=sha(__file__),
        shared_oracle_sha256=sha(old.__file__),capacity_certificate=False,adaptive_security_proof=False))
    print(json.dumps(dict(status='passed',functional_cases=len(cases),active_rejections=len(failures),local_exact=exact)),flush=True)


if __name__=='__main__':main()
