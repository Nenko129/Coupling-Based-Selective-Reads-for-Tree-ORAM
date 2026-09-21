"""Reject corruption in the retained incomplete-window record."""
from common import *
import copy
from audit_ir_compressed_failure import audit_failure
def main():
    path=PACKAGE/'results/failures/IRCMpilot_beta4.json';base=json.loads(path.read_text());expected=audit_failure(base,base['spec'])
    edits=[
        ('false_completion',lambda r:r.__setitem__('completed_this_phase',6144)),
        ('extra_window',lambda r:r.__setitem__('clock',r['clock']+1)),
        ('missing_traffic',lambda r:r['partial_bill'].__setitem__('total_bytes',0)),
        ('wrong_outstanding',lambda r:r.__setitem__('queued_requests',1)),
        ('different_failure',lambda r:r.__setitem__('error','Overflow: transfer boundary stash')),
        ('hidden_reset',lambda r:r['map_metrics'].__setitem__('group_backend_slots',0)),
        ('invalid_cursor',lambda r:r['reset'].__setitem__('cursor',32)),
        ('claimed_success',lambda r:r.__setitem__('status','passed')),
    ];rejected=[]
    for name,edit in edits:
        r=copy.deepcopy(base);edit(r)
        try:audit_failure(r,base['spec'])
        except AssertionError:rejected.append(name)
        else:raise AssertionError(name)
    save(PACKAGE/'results/ir_compressed_failure_audit_checks.json',dict(status='passed',original=expected,rejected=rejected,
        input_sha256=sha(path),auditor_sha256=sha(Path(__file__).with_name('audit_ir_compressed_failure.py')),checker_sha256=sha(__file__)))
    print(json.dumps(dict(status='passed',rejections=len(rejected))))
if __name__=='__main__':main()

