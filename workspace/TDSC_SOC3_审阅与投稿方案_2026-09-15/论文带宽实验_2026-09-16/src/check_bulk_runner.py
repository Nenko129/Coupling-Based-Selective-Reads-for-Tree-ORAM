from common import *
from check_extended_runners import launch,equal_bill
from bulk_prf import make_bulk_prf
from check_fast_prf import counters,execute,compare
import check_fast_prf as prior
import optimized_oram as ref

def main():
    cases=[]
    for kind in ('sde','r0'):
        spec=dict(kind=kind,N=32,B=4096,profile=[4,3,3],R=128,map_B=512,terminal_bytes=16,compact=True,fusion=True,
                  warmup=16,requests=32,trace_seed=654,oram_seed=987,workload='uniform',study='bulk_check',experiment_class='bulk_checks')
        a=launch(dict(spec,id=f'bulk_{kind}_control'),'run_extended.py')
        b=launch(dict(spec,id=f'bulk_{kind}_candidate'),'run_bulk_scale.py')
        equal_bill(a,b);assert len(b['configs'])==2;cases.append(dict(kind=kind,recursive=True,identical=True))
    budgets=[]
    for remaining in (0,1,63,64,65):
        values=[]
        for Type in (ref.PRF,make_bulk_prf(ref)):
            p=Type(b'K'*64);p.calls=(1<<96)-remaining
            try:out=p.seal(b'C',b'O',b'A',b'P'*4096)
            except ref.Reject as e:out=(type(e).__name__,str(e))
            values.append((out,counters(p)))
        assert values[0]==values[1];budgets.append(remaining)
    prior.make_fast_prf=make_bulk_prf;attacks=[]
    for kind in ('sde','r0'):
        for variant in ('header','sequence','ack'):
            pair=[]
            for fast in (False,True):
                m=execute(ref,[ref.Config(kind,3,8,4096,R=128)],fast);fired=[False]
                def mutate(c,op,seq,stage,meta,req,res):
                    if fired[0] or (variant=='ack' and op!=ref.WRITE):return res
                    fired[0]=True
                    if variant=='header':return res[:-1]+bytes([res[-1]^1])
                    o,t,s,f,body=ref.parse_frame(res)
                    return ref.frame(o,t,s-1 if variant=='sequence' else s,body if variant=='sequence' else b'bad',True)
                m.io.mutator=mutate
                try:m.access(0)
                except ref.Reject:pass
                else:raise AssertionError('tamper accepted')
                assert fired[0] and m.dead;seq=m.io.seq
                try:m.access(1)
                except ref.Reject:pass
                else:raise AssertionError('retry accepted')
                assert m.io.seq==seq;pair.append(m)
            compare(*pair);attacks.append(dict(kind=kind,variant=variant,identical_failed_prefix=True))
    save(PACKAGE/'results/bulk_runner_checks.json',dict(status='passed',process_checks=cases,budget_cases=budgets,attacks=attacks,
         runner_sha256=sha(Path(__file__).parent/'run_bulk_scale.py'),bulk_sha256=sha(Path(__file__).parent/'bulk_prf.py'),checker_sha256=sha(__file__)))
    print(json.dumps(dict(status='passed',process_checks=len(cases),budget_cases=len(budgets),attacks=len(attacks))))
if __name__=='__main__':main()
