"""Audit and report every completed selection diagnostic, including starvation."""
from common import *
from audit_ab_cb import bill
import ab_cb_runtime as old
import ab_dummy_first_runtime as new


def main():
    pp=PACKAGE/'ab_selection_diagnostic_plan.json';p=json.loads(pp.read_text());rows=[];receipts=[]
    assert p['source_hashes']['original']==old.identity() and p['source_hashes']['revised']==new.identity()
    assert p['source_hashes']['checker']==sha(Path(__file__).with_name('diagnose_ab_selection.py'))
    checks={name:json.loads((PACKAGE/'results'/name).read_text()) for name in (
        'ab_dummy_first_checks.json','ab_dummy_first_frontend_checks.json','ab_dummy_first_periodic_checks.json')}
    engine=checks['ab_dummy_first_checks.json'];front=checks['ab_dummy_first_frontend_checks.json'];period=checks['ab_dummy_first_periodic_checks.json']
    assert engine['status']=='passed' and engine['source_hashes']==new.identity() and len(engine['functional_cases'])==24
    assert engine['local_exact']['cases']==2658 and len(engine['active_rejections'])==3
    assert front['status']=='passed' and front['source_hashes']==new.identity() and len(front['cases'])==12 and front['pressure_exercised']
    assert period['status']=='passed' and period['source_hashes']['runtime']==new.identity() and period['positive_cases']==6 and len(period['negative_checks'])==7
    for s in p['specs']:
        path=PACKAGE/'results/ab_selection_diagnostic'/f"{s['policy']}.json"
        if not path.exists():continue
        r=json.loads(path.read_text());assert r['spec']==s and r['source_hashes']==p['source_hashes']
        assert r['performance_sample'] is False and r['capacity_certificate'] is False
        assert r['initialization']['t']==21845;bill(r['initialization']['bill']);bill(r['validation_bill'])
        assert r['validation_bill']['first_sequence']==r['initialization']['bill']['next_sequence']
        assert r['final_t']==21845+r['clock']
        m=r['metrics'];assert r['clock']==m['public_slots']==sum(m.get(k,0) for k in ('foreground_slots','dummy_slots','background_slots'))
        hist={int(k):v for k,v in r['boundary_stash_histogram'].items()};assert sum(hist.values())==r['clock']
        assert r['checked_answers']==m.get('application_completed',0) and 0<=r['checked_answers']<=s['Q']
        assert r['schedule']['slots']==r['clock'] and len(r['schedule']['remove_admit_sha256'])==64
        if r['status']=='completed':assert r['clock']==s['W'] and r['checked_answers']==s['Q'] and not r['queued'] and not r['work_pending'] and r['error'] is None
        elif r['status']=='incomplete_horizon':assert r['clock']==s['W'] and r['checked_answers']<s['Q'] and r['error'] is None
        else:assert r['status']=='execution_failed' and r['error']
        rows.append(r);receipts.append(dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path)))
    save(PACKAGE/'results/ab_selection_diagnostic_audit.json',dict(status='complete_diagnostic_audited' if len(rows)==2 else 'partial_diagnostic_audited',
        rows=len(rows),expected=2,plan_sha256=sha(pp),receipts=receipts,auditor_sha256=sha(__file__),
        check_sources={name:sha(PACKAGE/'results'/name) for name in checks},
        independent_answer_digest_check=False,performance_claim=False,capacity_certificate=False))
    md=['# AB-CB选择策略与完成率诊断','',
        '本轮不更换N/L/R、不增加时隙、不删除失败运行。比较两个明确命名的选择策略；该诊断不是正式五种子性能批次。',
        '固定条件：N4096/B64/L11、递归后4369记录、C5/A5/Y4/R500、底三层D0、缓存6层、PLB8、LLC8×2、H48/L32；相同叶标签种子5101。每A槽加载一条记录，初始化21845槽。随后按间隔8依次请求读取全部4096条数据，固定65536个公开时隙。','',
        '| 策略 | 状态 | 加载后stash | 加载/全程峰值 | 完成请求 | 后台时隙 | 后台green搬出 | 读取阶段总MiB |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        m=r['metrics'];i=r['initialization'];label='未读槽均匀选择' if r['spec']['policy']=='uniform_unused' else '优先dummy、必要时green'
        md.append(f"| {label} | {r['status']} | {i['stash']} | {i['peak']}/{r['max_boundary_stash']} | {r['checked_answers']}/4096 | {m.get('background_slots',0)} | {m.get('background_green_promotions',0)} | {r['validation_bill']['total_bytes']/2**20:.3f} |")
    md+=['',f'已落盘并审计{len(rows)}/2个诊断；未结束的结果不填预测值。',
        '旧受控检查失败于固定窗口完成条件。诊断直接逐时隙记录状态；若所有时隙均为后台、完成请求为零，说明该控制器/选择策略/阈值组合发生了请求饥饿。这不是容量溢出，也不能只延长窗口后抹去旧失败。','',
        '## 为什么增加这项修订','',
        '[AB-ORAM §III-C](https://mehrnoosh.net/research/AB-ORAM-HPCA%2723.pdf)描述在dummy预留耗尽后使用green。String ORAM §IV-A允许在green额度内选择dummy或真实块；原型此前采用全未读槽均匀选择。现在另建优先dummy的实现，避免仍有dummy时主动搬出非目标真实块。两个策略都保留，不能把本次修订隐藏在同一个协议名下。',
        '目标存在时始终优先目标；目标不在该桶时，从未读dummy均匀选取；只有没有未读dummy且G<Y时才从剩余真实槽选取green。所有在线、空闲与后台Transfer采用同一规则，不通过公开请求类型暴露私有后台模式。','',
        '## 局部分布及可执行性','',
        '设公开未读数为U，隐藏真实数为r，条件分布在所有r元真实集合上可交换。r<U时，任意槽j被选中的概率为((U-r)/U)/(U-r)=1/U；r=U时直接均匀取一个未读槽，概率也为1/U。桶内目标的槽位同样均匀。',
        '若无dummy且G=Y，则U=r<=C-Y，而U=C+D-t且t<D+Y，产生矛盾。因此合法消费阈值前，无dummy必有剩余green额度。认证、neutral融合、唯一nonce、gamma和ACK后提交逻辑沿用已检查代码，新协议另有加密上下文标识。',
        '24组功能检查、2658组局部有理数检查、80组零cover情形及三个主动认证失败点通过。12组raw递归map/LLC/压力检查也通过，低阈值组实际触发后台，所有组核对同一返回值和有用迁移序列。六组小域周期驱动与七种损坏收据拒绝检查通过，包含选择策略被篡改的拒绝。',
        '它们不证明多次自适应transcript的完整模拟，也不是green容量尾界。底部D0的满真实桶仍可能取出green，因此该修订不能称“严格只读dummy后台”。','',
        '## 正式实验门槛','',
        '诊断中的新策略已完成4096个正确读回，均匀/底部D0两布局×Ring/GC-Ring/R0六组目标规模检查正在执行。六组全部通过后，启动器才生成ABDF的60格正式条件计划，并启动逐行审计的队列；任何失败均停止，不会退回旧ABPER/ABPACED或覆盖失败。',
        '新的 `run_ab_dummy_first_periodic.py`、独立审计入口与来源绑定已完成小域验证。初始化、对齐与完整周期的时钟不变，所有对比臂都用同一选择修订；只有布局和selective后端按预定矩阵变化。`start_ab_dummy_first_batch.py`等候已确认存活的六组验证进程，当前进度见对应dependency/queue状态；状态文件不替代实际进程核验。',
        '当前账单、时钟、槽位守恒由独立分析器核对。数据逐项比对在诊断执行器内完成，该诊断未保存可供独立重算的返回值摘要，因此不把这份审计写成独立答案摘要核验。正式性能驱动已有该要求，修订时仍须保留。',
        '完整AB仍需DeadQ、后台策略的完整安全定义以及green感知容量归约。选择策略改进只解决其中一个具体实现选择，不代表完整目标完成。']
    (PACKAGE/'30_AB_CB选择策略与完成率诊断.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(rows=len(rows),expected=2,performance_claim=False)))


if __name__=='__main__':main()
