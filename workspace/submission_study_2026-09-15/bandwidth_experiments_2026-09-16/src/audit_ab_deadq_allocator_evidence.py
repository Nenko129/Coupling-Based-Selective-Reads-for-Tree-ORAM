"""Bind the allocator argument to its executable evidence without overclaiming."""
from common import *


def main():
    p=PACKAGE/'results/ab_deadq_allocator_model_checks.json';a=json.loads(p.read_text(encoding='utf-8'))
    report=PACKAGE/'52_AB_DeadQ所有权与联合重建.md';text=report.read_text(encoding='utf-8')
    assert a['status']=='passed'
    assert a['model_sha256']==sha(Path(__file__).parent/'ab_deadq_allocator_model.py')
    assert a['checker_sha256']==sha(Path(__file__).parent/'check_ab_deadq_allocator_model.py')
    source=PACKAGE.parent/'细化准备_2026-09-15/literature/pdf/R13_ab_oram_constructing_adjustable_buckets_for_space_reduction.pdf'
    assert a['source_pdf_sha256']==sha(source)
    assert not any(a[k] for k in ('native_AB_reproduction','encrypted_ORAM_execution','security_proof','bandwidth_measurement'))
    reach=a['reachability'];assert len(reach)==2
    assert all(x['full_normalized_graph_closed'] and x['depth_boundary_states']==0 for x in reach)
    assert [(x['states'],x['transitions']) for x in reach]==[(300,1932),(1676,10860)]
    assert reach[0]['expansion_transitions']==0 and reach[1]['expansion_transitions']==2376
    assert reach[1]['collateral_rebuild_transitions']==1368
    assert len(a['transaction_checks'])==9
    assert len(a['symbolic_payload_trials'])==5 and all(x['transitions']==500 for x in a['symbolic_payload_trials'])
    w=a['zero_extra_space_witness'];assert w['initial_physical_slots']==w['final_physical_slots']==4
    assert w['extra_persistent_slots']==0 and w['encrypted_execution'] is False
    assert w['steps'][4]['result']=='expanded' and w['steps'][4]['borrowed']==[0]
    assert w['steps'][5]['rebuilt']==[0,1] and [1,2,0] in w['steps'][5]['staged_logical_slots']
    for token in ('1,932','1,676','10,860','2,376','1,368','2,500','字符串比较不是密码认证实现','尚无正带宽结论'):
        assert token in text
    out=dict(status='evidence_consistent',model_receipt_sha256=sha(p),report_sha256=sha(report),auditor_sha256=sha(__file__),
        abstract_states=sum(x['states'] for x in reach),abstract_transitions=sum(x['transitions'] for x in reach),
        symbolic_payload_transitions=2500,transaction_checks=9,allocator_argument_only=True,
        full_security_admission=False,native_AB_complete=False,encrypted_ORAM_execution=False,bandwidth_claim=False)
    save(PACKAGE/'results/ab_deadq_allocator_evidence_audit.json',out)
    print(json.dumps(out))


if __name__=='__main__':main()
