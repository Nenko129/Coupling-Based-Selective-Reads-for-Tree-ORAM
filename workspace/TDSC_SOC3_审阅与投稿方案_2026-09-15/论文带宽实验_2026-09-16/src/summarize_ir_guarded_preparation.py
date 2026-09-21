"""Bind the diagnosed original failure and the prospective public-tail plan."""
from common import *
from dispatch_ir_guarded import validate
from run_ir_guarded_periodic import identity
from ir_compressed_controller import identity as runtime_identity


def main():
    pp=PACKAGE/'formal_ir_guarded_plan.json';plan=json.loads(pp.read_text());validate(plan)
    rp=PACKAGE/'results/ir_reset_window_replay.json';r=json.loads(rp.read_text())
    gp=PACKAGE/'results/ir_guarded_runner_checks.json';g=json.loads(gp.read_text())
    assert r['status']=='passed' and r['encrypted_receipts_checked']==30 and not r['actual_bandwidth']
    assert r['source_hashes']==runtime_identity() and r['checker_sha256']==sha(Path(__file__).with_name('ir_reset_window_replay.py'))
    assert g['status']=='passed' and g['source_hashes']==identity() and len(g['cases'])==6 and len(g['rejected_receipts'])==7
    assert g['checker_sha256']==sha(Path(__file__).with_name('check_ir_guarded_periodic.py'))
    assert len(plan['specs'])==30 and len(plan['pilots'])==2
    for case in r['cases']:
        for ref in case['references']:assert sha(PACKAGE/ref['path'])==ref['sha256']
    for ref in g['cases']:assert sha(PACKAGE/ref['path'])==ref['sha256']
    md=['# IR重置压力：窗口末尾诊断与独立补充实验','',
        '原75个正式观测和58/59号报告不变。本报告解释β4压力组的窗口未完成，并固定新的公开尾部窗口实验；不将逻辑重放的结果冒充新的密文带宽测量。','',
        '## 1. 原始失败的具体位置','',
        '原计划每8个时隙到达一个应用请求，暖机1536请求/12288槽，测量6144请求/49152槽。最后一次到达后仅余8个槽。一次底层压缩计数器组重置最多要轮换32个子块；已有待处理reset优先占用后续Transfer，因此窗口可在最后几次请求完成前结束。固定窗口未完成并不等于stash溢出。','',
        '新增重放使用原有压缩前端和DWB控制器，后端换为只在诊断中使用的明文所有权字典；逐次检查旧叶标签、接纳/移除及返回payload。原β14/4、Hot90/DWB-on三后端各五种子的30份加密运行记录全部匹配：成功者的答案摘要、移除/接纳摘要和所有前端/map计数相同；失败者的阶段、完成数、队列、reset游标、时钟和完整调度摘要相同。后端字典是O(N)测试oracle，不能作为免费可信ORAM位置表或容量证明。','',
        '| β4种子 | 原暖机完成数 | 原截点reset游标 | 逻辑续行完成原暖机还需槽数 | 新统一尾部设计中measurement超出原截止线的槽数 |',
        '|---|---:|---:|---:|---:|']
    for case in r['cases']:
        if case['beta']!=4:continue
        w=case['original']['phases'][0];reset=w['reset_end'];cw,cm=case['counterfactual']['phases']
        cursor='无' if reset is None else str(reset['cursor'])+'/32'
        md.append(f"| {case['seed']} | {w['completed']}/1536 | {cursor} | {cw['tail_slots_to_clear']} | {cm['tail_slots_to_clear']} |")
    md+=['','12个原失败对应四个种子×三个后端；它们的逻辑续行余量为20–26槽。measurement一列是在新暖机尾部执行后的另一条运行历史，不能称为原始失败运行的实测延迟。原失败收据没有partial-answer摘要；本逻辑模型不能补造该摘要或追认其部分返回正确性。','',
        '## 2. 新的统一公开窗口','',
        '| 项目 | 原75观测中的对应压力设计 | 新补充设计 |','|---|---:|---:|',
        '| 维护参考周期P | 12288槽 | 12288槽 |',
        '| 到达间隔/应用请求数 | 间隔8；暖机1536/测量6144 | 保持相同 |',
        '| 暖机窗口 | 1P=12288 | 2P=24576 |',
        '| 测量窗口 | 4P=49152 | 5P=61440 |',
        '| 末尾无新请求的公开尾部 | 无额外尾部 | 两阶段均额外1P |',
        '| 计费 | 全部原窗口 | 全部新窗口，原截点与尾部另分账 |','',
        '选择一整维护周期是为了保持相位对齐与统一公开边界，属于保守的实验设计，不是最小padding方案，也不构成所有请求串均能完成的最坏情况证明。完成请求后仍执行至公开终点，不能按实际完成时刻提前结束。测量槽数增加25%，暖机槽数增加100%；所有方案支付相同窗口，不能省略额外流量，也不将新旧窗口之间的变化叫selective收益。','',
        'N4096/B64/X32、PLB8、LLC8组×2路、缓存6层、R480、Hot90、DWB-on保持不变。新矩阵为β14/4 × Path/Deferred/SDE × seeds101–105，共30次全量初始化的新加密运行；seed901/1901的两个SDE目标预试验通过后才进入正式批次。旧正式收据、失败、输入及窗口均不覆盖。设计是在看到原结果和逻辑诊断后制定、在新目标密文性能结果前固定；不声称最初盲预注册。','',
        '每个β内比较Path→SDE与Deferred→SDE；每个后端内比较β14→4，均以五个完整配对种子统计。绝对bytes/op、尾部bytes/RPC、reset/dummy槽及完成率一起报告。成本CV超过10%或减少率区间半宽超过5个百分点时，对整个相关比较组增至10次。任何未完成/异常均保留且停止检查，不以成功子集估计整组性能。','',
        '## 3. 已完成的真实检查与待完成项','',
        '新的窗口驱动已完成N64/B64的β2/14 × Path/Deferred/SDE六组真实密文执行。每个完成请求在运行时核对payload，另按独立版本历史复算完整和原截点答案摘要；全部帧账单、时钟、尾部费用、对象空间和逻辑调度通过审计。三组β2测量均实际触发8个reset槽。七种损坏记录被拒绝：不计尾部、虚构截点完成数、错部分答案摘要、错请求分母、隐藏reset、篡改调度、声称替换原结果。','',
        '目标规模预试验和30次正式补充结果尚未在本报告中宣称完成。逻辑重放预测新设计可完成这十条β/seed调度并触发β4 reset，但这些预测不提供任何带宽数值；最终须以真实密文收据、完整五次配对和图表为准。新实验仍不含IR-Stash、PMMAC或完整自适应安全归约，也不报告实测加速比。','',
        '来源：`formal_ir_guarded_plan.json`、`results/ir_reset_window_replay.json`、`results/ir_guarded_runner_checks.json`。启动/完成状态由`results/ir_guarded_queue_state.json`及具名目标收据单独保存，不将本准备报告当作完成标志。']
    report=PACKAGE/'60_IR重置压力诊断与补充实验.md';report.write_text('\n'.join(md)+'\n',encoding='utf-8')
    save(PACKAGE/'results/ir_guarded_preparation_evidence.json',dict(status='preparation_checked',plan_sha256=sha(pp),
        replay_sha256=sha(rp),small_runner_checks_sha256=sha(gp),report_sha256=sha(report),producer_sha256=sha(__file__),
        old_encrypted_receipts_crosschecked=30,new_small_encrypted_checks=6,planned_formal_runs=30,
        target_experiment_complete=False,model_bandwidth_claim=False,original_outcomes_replaced=False))
    print(json.dumps(dict(status='preparation_checked',report=report.name,new_formal_runs=30)))


if __name__=='__main__':main()
