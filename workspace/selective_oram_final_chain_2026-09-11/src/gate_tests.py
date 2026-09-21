#!/usr/bin/env python3
from pathlib import Path
import tempfile,shutil,json,hashlib
from certified_driver import *
from unified_cost import invoice
ROOT=Path(__file__).resolve().parents[1]

def bad(fn):
    try:fn()
    except (GateError,ValueError):return
    raise AssertionError('bad evidence contract accepted')

def main():
    bank=CertificateBank();count=0
    for path,value in [(('ghost','bucket_levels'),'L'),(('ghost','rate'),'3'),(('protocol','priority'),'mutable stale flag'),
                       (('protocol','neutral_reshuffle_fills_from_stash'),True),(('offsets','r0'),2),
                       (('authentication','header_Z4_bytes'),376),(('authentication','server_computes_keyed_tags'),True)]:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ct=json.loads((ROOT/'theorem_contract.json').read_text());ct[path[0]][path[1]]=value
            (root/'theorem_contract.json').write_text(json.dumps(ct));bad(lambda:CertificateBank(root));count+=1
    # An altered artifact must fail identity checking before its data are used.
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);ct=json.loads((ROOT/'theorem_contract.json').read_text())
        name=next(iter(ct['artifact_sha256']));p=root/name;p.parent.mkdir(parents=True);p.write_bytes((ROOT/name).read_bytes()+b'\n# mutation\n')
        ct['artifact_sha256']={name:ct['artifact_sha256'][name]};(root/'theorem_contract.json').write_text(json.dumps(ct))
        bad(lambda:CertificateBank(root));count+=1
    bad(lambda:bank.plan([Config('r0',23,12582912,R=16)],1<<64));count+=1
    bad(lambda:bank.plan([Config('sde',23,12582912,R=192)],1<<128));count+=1
    executions=[]
    for kind in ('sde','r0'):
        configs=[Config(kind,6,96,B=64,R=32,tree=0),Config(kind,4,24,B=16,R=24,tree=1)]
        # This is a deliberately smaller regression horizon/budget, not the main
        # 48GiB/2^64 theorem instance.
        m=CertifiedRecursiveORAM(configs,hashlib.sha512(('gate:'+kind).encode()).digest(),max_online=40,bank=bank,stash_bits=12)
        m.initialize(lambda a:a.to_bytes(64,'big'));start=len(m.io.events)
        for a in range(40):assert m.access(a)==a.to_bytes(64,'big')
        assert [t.t for t in m.trees]==m.operation_limits
        before=len(m.io.events)
        try:m.access(0)
        except Reject:pass
        else:raise AssertionError('horizon was not enforced')
        assert before==len(m.io.events)
        executions.append({'kind':kind,'requests':40,'approval':m.approval,'invoice':invoice(configs,m.io.events[start:]),'horizon_rejected_before_IO':True})
    out={'rejected_contract_or_budget_mutations':count,'certified_entrypoint_executions':executions}
    (ROOT/'results/gate_tests.json').write_text(json.dumps(out,indent=2));print('Gate mutations:',count,'; two certified encrypted executions passed.')
if __name__=='__main__':main()
