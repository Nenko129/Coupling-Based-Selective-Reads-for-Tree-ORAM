"""Complete artifact notes and experimental coverage limits, bound to audits."""
from common import *


def main():
    tp=PACKAGE/'results/ab_ir_completed_tables_audit.json';t=json.loads(tp.read_text())
    ep=PACKAGE/'results/ab_ir_completed_exports_audit.json';e=json.loads(ep.read_text())
    vp=PACKAGE/'results/ab_ir_completed_visual_review.json';v=json.loads(vp.read_text())
    assert t['status']==e['status']=='passed' and v['status']=='visually_reviewed'
    assert not v['unresolved_layout_defects'] and v['numerical_audit_sha256']==sha(ep)
    assert e['tables_audit_sha256']==sha(tp)
    for numeric,visual in zip(e['figures'],v['figures']):
        assert numeric['stem']==visual['stem']
        for ext in ('svg','png'):assert numeric[ext+'_sha256']==visual[ext+'_sha256']==sha(PACKAGE/f"figures/{visual['stem']}.{ext}")
    abp=PACKAGE/'results/ab_dummy_first_completed_snapshot.json';ab=json.loads(abp.read_text())
    irp=PACKAGE/'results/ir_compressed_completed_snapshot.json';ir=json.loads(irp.read_text())
    assert [x['source_sha256'] for x in t['artifacts']]==[sha(abp),sha(irp)]
    assert all(c['frontend'].get('background_slots',{'mean':0})['mean']==0 for c in ab['cells'])
    abmd=['# AB-CB完整图表：强基线与机制覆盖','',
        '56号报告的60份原始记录、12格绝对成本和18组配对结果均已完整核对。现新增双面板矢量图`figures/completed_ab_cb_bandwidth.svg`与PNG预览：左图相对Ring+CB，右图放大展示相对GC-Ring+CB的增量。','',
        'R0相对Ring+CB的配对减少率为20.2372%–21.9777%。但GC-Ring→R0四组均值仅−0.002497%至+0.002485%，全部95%区间包含零；此数据不支持宣称R0进一步降低了已采用GC约束的CB对照的通信。树根已经在可信缓存中，省根没有可再次去掉的远程根读写。','',
        '## 必须披露的机制覆盖','',
        '本批测量阶段所有12格的background_slots均为零：H48/L32压力控制器已配置且功能检查覆盖触发，但本正式批次没有测到压力后台激活。因此不能从本表推出后台压力策略的性能收益。CB的green与neutral计数实际非零，列在下表。这些是全树内部计数，包含缓存桶，不能直接乘块长当成远程通信。','',
        '| 布局 / 负载 / 后端 | green搬出均值 | neutral重建均值 | maintenance cover槽均值 | background槽均值 |',
        '|---|---:|---:|---:|---:|']
    for c in ab['cells']:
        val=lambda key:c['cb'].get(key,{'mean':0})['mean']
        abmd.append(f"| {c['layout']} / {c['workload']} / {c['kind']} | {val('green_promotions'):.1f} | {val('neutral_rebuilds'):.1f} | {val('maintenance_cover_slots'):.1f} | 0 |")
    abmd+=['','## 审计与范围','',
        '60份原始收据支持图中的12组均值/区间；独立解析SVG实际柱宽，包含正负的微小增量。最终PNG已实际审阅，并修正了右图刻度过密问题。56号报告保留绝对字节、RPC、服务器对象、已列客户资源和通信分项。','',
        '本图是无DeadQ、dummy优先并允许green回退的条件协议结果；不能声称原生AB或strict-dummy后台、green容量证书、自适应安全证明、可信峰值或延迟改进。54号认证DeadQ原型与这60次实验分开，新增路由开销没有悄悄混入或省略。']
    abreport=PACKAGE/'57_AB_CB完整图表与覆盖范围.md';abreport.write_text('\n'.join(abmd)+'\n',encoding='utf-8')
    main=[c for c in ir['cells'] if c['cohort']=='main_beta14'];stress=[o for o in ir['outcomes'] if o['spec']['cohort']=='reset_stress_beta4']
    assert len(main)==12 and all(c['frontend'].get('group_reset_slots',{'mean':0})['mean']==0 for c in main)
    assert sum(o['status']=='passed' for o in stress)==3 and all(o['audit']['phase']=='warmup' for o in stress if o['status']!='passed')
    irmd=['# IR压缩map完整图表：性能与未完成窗口分开','',
        '58号报告已冻结75个正式观测和60份raw-map对照。主β14组60次全部完成；β4压力15次中，仅seed101的三后端完成，其余12次均在暖机窗口结束时停止。新增`figures/completed_ir_compressed.svg`和PNG，同时展示八组主性能比较与全部15个压力结果。','',
        '主组SDE相对Deferred减少19.1871%–19.2002%，相对Path减少9.7415%–9.7561%。完整五种子配对表还包括DWB与raw→compressed因素；26组有效比较通过，涉及β4的五组比较整体不报告成功子集均值。','',
        '## 重置覆盖与失败阶段','',
        'β14主组的group_reset_slots在全部60次测量中为零。因此主性能组没有测量计数器耗尽后的重置代价；不能将其外推为“reset没有开销”。β4将重置压力显式引入，但15次中12次在暖机阶段未完成，尚未进入正式measurement。','',
        '| seed | Path暖机完成 | Deferred暖机完成 | SDE暖机完成 | 是否进入并完成measurement |','|---|---:|---:|---:|---|']
    for seed in range(101,106):
        os=[next(o for o in stress if o['spec']['trace_seed']==seed and o['spec']['kind']==k) for k in ('path','deferred','sde')]
        warm=[1536 if o['status']=='passed' else o['audit']['completed_requests'] for o in os]
        assert len(set(warm))==1
        irmd.append(f"| {seed} | {warm[0]}/1536 | {warm[1]}/1536 | {warm[2]}/1536 | "+('三者均完成6144/6144' if all(o['status']=='passed' for o in os) else '三者均未进入')+' |')
    irmd+=['','固定时隙窗口结束的错误已由失败审计确认；这些收据没有报告stash overflow。三后端对同一seed具有相同完成数，符合前端/reset调度造成窗口不足的解释；不据此断言所有原生IR系统存在该问题。未完成记录没有独立partial-answer摘要，完成数仅作为控制器结果保留，不计算“每个正确完成请求”的性能或将其纳入优化均值。','',
        '单独的启动前β4 pilot是在measurement阶段完成6143/6144，与正式12次暖机停止不同，不能混淆阶段。公开观测规则是在正式运行前修订的；不延长失败者的窗口、不删失败、不事后重试覆盖原始样本。','',
        '同几何、同完整时隙窗口下，Path/Deferred每槽账单固定。58号关于DWB/β账单相等的陈述适用于这样的同窗口条件；本批β4缺少完整五对，不构成正式β14→β4性能结论。raw→compressed主组和DWB主组的完整对照则可直接核对。','',
        '## 数据与图形核验','',
        '共135份来源，其中123份完整运行逐层核对对象空间，12份失败独立审计窗口与全部通信。完整15格、31个预声明比较位置都保留；26组有性能统计，5组因未完成排除。表审计与AB合计拒绝11种破坏，包括改分母、改均值、漏格、以重复比较隐藏缺项、删除失败和把单种子压力格伪装成完整组。','',
        '八根收益柱从原始收据重算，并核对SVG实际宽度；15个压力色块的状态、颜色及完成数逐一对应原始成功/失败文件。最终PNG版面已实际审阅。','',
        '该结果仍为异质树、缓存、压缩map和固定时隙DWB适配，不含原生IR-Stash或PMMAC，未修复此前skip转录反例。不得用主组数据补写原生IR整体收益、完整安全证明、真实可信峰值、稳态或延迟结论。']
    irreport=PACKAGE/'59_IR压缩图表与压力边界.md';irreport.write_text('\n'.join(irmd)+'\n',encoding='utf-8')
    save(PACKAGE/'results/ab_ir_completed_evidence.json',dict(status='passed',tables_audit_sha256=sha(tp),exports_audit_sha256=sha(ep),
        visual_review_sha256=sha(vp),producer_sha256=sha(__file__),ab_source_sha256=sha(abp),ir_source_sha256=sha(irp),
        report_hashes={p.name:sha(p) for p in (abreport,irreport)},ab_runs=60,ir_outcomes=75,ir_reused_controls=60,
        ir_incomplete=12,main_ir_reset_slots=0,ab_measurement_background_slots=0,native_full_systems=False))
    print(json.dumps(dict(status='passed',reports=[abreport.name,irreport.name],ab_runs=60,ir_passed=63,ir_incomplete=12)))


if __name__=='__main__':main()
