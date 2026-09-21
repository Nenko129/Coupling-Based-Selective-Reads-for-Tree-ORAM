"""Generate isolated driver/check/queue tools with inspectable diffs."""
from common import *
import difflib


def write_revision(base_name,out_name,edits):
    base=Path(__file__).parent/base_name;out=base.with_name(out_name);old=base.read_text(encoding='utf-8');text=old
    for before,after,count in edits:
        assert text.count(before)==count,(base_name,before,text.count(before),count);text=text.replace(before,after)
    out.write_text(text,encoding='utf-8');out.with_suffix('.diff').write_text(''.join(difflib.unified_diff(
        old.splitlines(True),text.splitlines(True),fromfile=base_name,tofile=out_name)),encoding='utf-8')
    return dict(base=base_name,base_sha256=sha(base),output=out_name,output_sha256=sha(out))


def main():
    rows=[]
    rows.append(write_revision('run_ab_paced_periodic.py','run_ab_dummy_first_periodic.py',[
        ('import ab_cb_runtime as rt','import ab_dummy_first_runtime as rt',1),
        ('ab_cb_frontend_checks.json','ab_dummy_first_frontend_checks.json',1),
        ("    m=phases['measurement'];row=dict(status='passed',", "    m=phases['measurement'];row=dict(status='passed',cb_selection_policy='dummy_first_v1',",1),
        ('pressure slots use ordinary CB dummy reads','all Transfer slots prefer unused dummies before green',1),
        ('ordinary CB dummy Transfer, which can promote green records; not the native strict-dummy wording',
         'dummy-first CB Transfer; green fallback remains possible when no unused dummy exists; not strict-dummy-only',1)]))
    rows.append(write_revision('check_ab_paced_periodic.py','check_ab_dummy_first_periodic.py',[
        ('ab_paced_periodic','ab_dummy_first_periodic',3),
        ('from audit_ab_cb import audit_record,matched','from audit_ab_dummy_first import audit_record,matched',1),
        ('ab_cb_frontend_checks.json','ab_dummy_first_frontend_checks.json',1),
        ('check_ABPACED_','check_ABDF_',1),
        ("auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py')", "auditor_sha256=sha(Path(__file__).parent/'audit_ab_dummy_first.py'),base_auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py')",1),
        ("edits=[('old_initial_clock'", "edits=[('wrong_selection_policy',lambda x:x.__setitem__('cb_selection_policy','uniform_unused')),('old_initial_clock'",1)]))
    rows.append(write_revision('dispatch_ab_paced_periodic.py','dispatch_ab_dummy_first_periodic.py',[
        ('ab_paced_periodic','ab_dummy_first_periodic',6),
        ('ab_paced_controlled_checks.json','ab_dummy_first_controlled_checks.json',1),
        ('from audit_ab_cb import inputs,audit_record','from audit_ab_dummy_first import inputs,audit_record',1)]))
    rows.append(write_revision('analyze_ab_periodic.py','analyze_ab_dummy_first_periodic.py',[
        ('from audit_ab_cb import inputs,audit_record,matched','from audit_ab_dummy_first import inputs,audit_record,matched',1),
        ("    parser=argparse.ArgumentParser();parser.add_argument('--paced',action='store_true');args=parser.parse_args()\n    prefix='ab_paced_periodic' if args.paced else 'ab_periodic';plan_name=prefix+'_plan.json'",
         "    args=argparse.Namespace(paced=True)\n    prefix='ab_dummy_first_periodic';plan_name=prefix+'_plan.json'",1),
        ('AB_CB_paced_periodic_runs.csv','AB_CB_dummy_first_periodic_runs.csv',1),
        ('28_AB_CB公开加载周期结果.md','31_AB_CB优先dummy周期结果.md',1),
        ("auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py')", "auditor_sha256=sha(Path(__file__).parent/'audit_ab_dummy_first.py'),base_auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py')",1),
        ('# AB-CB完整周期通信复核：公开加载节拍修订（条件实验）','# AB-CB完整周期通信复核：优先dummy选择修订（条件实验）',1),
        ('后台使用普通CB dummy Transfer。','全部在线、空闲与后台Transfer均优先未读dummy，必要时green；尚非严格dummy后台。',1)]))
    save(PACKAGE/'results/ab_dummy_first_batch_build.json',dict(status='generated',files=rows,generator_sha256=sha(__file__),old_sources_preserved=True))
    print(json.dumps(dict(generated=len(rows))))


if __name__=='__main__':main()
