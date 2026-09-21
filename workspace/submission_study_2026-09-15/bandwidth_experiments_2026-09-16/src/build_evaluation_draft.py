"""Draft text cites only completed frontend evidence; missing scope stays visible."""
from common import *

def main():
    p=PACKAGE/'results/paired_statistics.json';rows=json.loads(p.read_text())['rows']
    complete=[r for r in rows if r['family'] in ('free_compressed','rho') and r['N']==4096 and r['B']==64]
    assert len(complete)==16 and all(r['n']==5 for r in complete)
    ir=json.loads((PACKAGE/'results/ir_dwb_statistics.json').read_text())
    assert ir['completed']==ir['expected']==120 and all(e['effect']['n']==5 for e in ir['effects'])
    cb=json.loads((PACKAGE/'results/pilot_ab_cb_audit.json').read_text())
    assert cb['completed']==cb['expected']==6
    skip_audit=json.loads((PACKAGE/'results/ir_stash_transcript_counterexample.json').read_text())
    assert skip_audit['status']=='counterexample_confirmed' and not skip_audit['security_admission']
    assert skip_audit['checker_sha256']==sha(Path(__file__).parent/'check_ir_stash_transcript_projection.py')
    periodic=json.loads((PACKAGE/'results/ir_periodic_statistics.json').read_text())
    assert periodic['completed']==periodic['expected']==60 and periodic['status']=='complete_receipts_audited'
    assert all(e['effect']['n']==5 and e['needs_more_repeats'] is False for e in periodic['effects'])
    periodic_export=json.loads((PACKAGE/'results/ir_periodic_exports_audit.json').read_text())
    periodic_visual=json.loads((PACKAGE/'results/ir_periodic_visual_review.json').read_text())
    assert periodic_export['status']=='passed' and periodic_export['source_sha256']==sha(PACKAGE/'results/ir_periodic_statistics.json')
    assert periodic_visual['status']=='visually_reviewed'
    assert periodic_export['pdf_sha256']==periodic_visual['pdf_sha256']==sha(PACKAGE/'output/pdf/completed_ir_periodic.pdf')
    assert periodic_visual['numerical_audit_sha256']==sha(PACKAGE/'results/ir_periodic_exports_audit.json')
    repairs=json.loads((PACKAGE/'results/ir_skip_repair_evidence_audit.json').read_text())
    assert repairs['status']=='evidence_consistent' and not repairs['security_admission'] and repairs['executions']==5376
    assert repairs['crosscheck_sha256']==sha(PACKAGE/'results/ir_skip_repair_model_crosscheck.json')
    assert repairs['model_sha256']==sha(PACKAGE/'results/ir_skip_repair_exact_model.json')
    assert repairs['checker_sha256']==sha(Path(__file__).parent/'summarize_ir_skip_repairs.py')
    public=json.loads((PACKAGE/'results/public_completed_audit.json').read_text())
    pub_export=json.loads((PACKAGE/'results/public_exports_audit.json').read_text())
    pub_visual=json.loads((PACKAGE/'results/public_visual_review.json').read_text())
    assert public['status']=='passed' and public['runs']==80 and public['comparisons']==8
    assert pub_export['status']=='passed' and pub_export['source_sha256']==sha(PACKAGE/'results/public_completed_audit.json')
    assert pub_visual['status']=='visually_reviewed'
    assert pub_export['pdf_sha256']==pub_visual['pdf_sha256']==sha(PACKAGE/'output/pdf/completed_public_workloads.pdf')
    assert pub_visual['numerical_audit_sha256']==sha(PACKAGE/'results/public_exports_audit.json')
    alignment=json.loads((PACKAGE/'results/ir_source_alignment_evidence_audit.json').read_text())
    assert alignment['status']=='evidence_consistent' and alignment['executions']==4224 and not alignment['security_admission']
    assert alignment['checker_sha256']==sha(Path(__file__).parent/'summarize_ir_source_alignment.py')
    for name,value in alignment['input_hashes'].items():assert sha(PACKAGE/'results'/name)==value
    space=json.loads((PACKAGE/'results/storage_components_audit.json').read_text())
    bad_space=json.loads((PACKAGE/'results/storage_audit_rejections.json').read_text())
    assert space['status']=='passed' and space['completed_run_count']==220 and space['completed_cells']==30
    assert space['auditor_sha256']==sha(Path(__file__).parent/'audit_storage_components.py')
    assert bad_space['status']=='passed' and len(bad_space['rejected'])==8 and bad_space['resource_receipt_sha256']==sha(PACKAGE/'results/storage_components_audit.json')
    classical=json.loads((PACKAGE/'results/classical_reference_evidence_audit.json').read_text())
    assert classical['status']=='evidence_consistent' and not classical['full_security_admission']
    assert classical['builder_sha256']==sha(Path(__file__).parent/'build_classical_report.py')
    assert classical['report_sha256']==sha(PACKAGE/'45_经典基线执行归约与容量账本.md')
    assert classical['plan_sha256']==sha(PACKAGE/'formal_classical_reference_plan.json')
    for name,value in classical['source_receipts'].items():assert sha(PACKAGE/'results'/name)==value
    tuned=json.loads((PACKAGE/'results/tuned_completed_snapshot.json').read_text())
    tuned_export=json.loads((PACKAGE/'results/tuned_exports_audit.json').read_text())
    tuned_visual=json.loads((PACKAGE/'results/tuned_visual_review.json').read_text())
    tuned_window=json.loads((PACKAGE/'results/tuned_model_window_audit.json').read_text())
    assert tuned['status']=='passed' and tuned['runs']==50 and len(tuned['effects'])==6
    assert tuned_export['status']=='passed' and tuned_export['source_sha256']==sha(PACKAGE/'results/tuned_completed_snapshot.json')
    assert tuned_visual['status']=='visually_reviewed' and not tuned_visual['unresolved_layout_defects']
    assert tuned_visual['pdf_sha256']==tuned_export['pdf_sha256']==sha(PACKAGE/'output/pdf/completed_tuned_bandwidth.pdf')
    assert tuned_visual['numerical_audit_sha256']==sha(PACKAGE/'results/tuned_exports_audit.json')
    assert tuned_window['status']=='passed' and tuned_window['source_sha256']==sha(PACKAGE/'results/tuned_completed_snapshot.json')
    assert tuned_window['auditor_sha256']==sha(Path(__file__).parent/'audit_tuned_model_window.py')
    free_sensitivity=json.loads((PACKAGE/'results/free_sensitivity_completed_audit.json').read_text())
    free_tables=json.loads((PACKAGE/'results/free_sensitivity_tables_audit.json').read_text())
    assert free_sensitivity['status']=='passed' and free_sensitivity['runs']==160
    assert free_sensitivity['all_free_slices_complete'] and not free_sensitivity['additional_repeat_groups']
    assert free_sensitivity['auditor_sha256']==sha(Path(__file__).parent/'audit_free_sensitivity_completed.py')
    assert free_tables['status']=='passed' and free_tables['source_sha256']==sha(PACKAGE/'results/free_sensitivity_completed_audit.json')
    assert free_tables['report_sha256']==sha(PACKAGE/'49_Freecursive敏感性完整结果.md')
    assert free_tables['checker_sha256']==sha(Path(__file__).parent/'verify_free_sensitivity_tables.py')
    free_export=json.loads((PACKAGE/'results/free_sensitivity_exports_audit.json').read_text())
    free_visual=json.loads((PACKAGE/'results/free_sensitivity_visual_review.json').read_text())
    assert free_export['status']=='passed' and free_export['source_sha256']==sha(PACKAGE/'results/free_sensitivity_completed_audit.json')
    assert free_visual['status']=='visually_reviewed' and not free_visual['unresolved_layout_defects']
    assert free_visual['pdf_sha256']==free_export['pdf_sha256']==sha(PACKAGE/'output/pdf/completed_free_sensitivity.pdf')
    assert free_visual['numerical_audit_sha256']==sha(PACKAGE/'results/free_sensitivity_exports_audit.json')
    rho_sensitivity=json.loads((PACKAGE/'results/rho_sensitivity_audit.json').read_text())
    rho_checks=json.loads((PACKAGE/'results/rho_sensitivity_checks.json').read_text())
    assert rho_checks['status']=='passed' and rho_checks['source_sha256']==sha(PACKAGE/'results/rho_sensitivity_audit.json')
    assert rho_checks['report_sha256']==sha(PACKAGE/'50_rho敏感性独立统计.md')
    assert rho_sensitivity['auditor_sha256']==sha(Path(__file__).parent/'audit_rho_sensitivity.py')
    assert rho_checks['checker_sha256']==sha(Path(__file__).parent/'check_rho_sensitivity_audit.py')
    rho_done=json.loads((PACKAGE/'results/rho_sensitivity_completed_evidence.json').read_text())
    assert rho_done['status']=='passed' and rho_done['runs']==180
    assert rho_done['source_sha256']==sha(PACKAGE/'results/rho_sensitivity_completed_snapshot.json')
    assert rho_done['checks_sha256']==sha(PACKAGE/'results/rho_sensitivity_checks.json')
    assert rho_done['exports_audit_sha256']==sha(PACKAGE/'results/rho_sensitivity_exports_audit.json')
    assert rho_done['visual_review_sha256']==sha(PACKAGE/'results/rho_sensitivity_visual_review.json')
    assert rho_done['report_sha256']==sha(PACKAGE/'55_rho敏感性完整图表.md')
    assert rho_done['producer_sha256']==sha(Path(__file__).parent/'summarize_rho_completed.py')
    ab_ir=json.loads((PACKAGE/'results/ab_ir_completed_evidence.json').read_text())
    assert ab_ir['status']=='passed' and not ab_ir['native_full_systems']
    assert (ab_ir['ab_runs'],ab_ir['ir_outcomes'],ab_ir['ir_reused_controls'],ab_ir['ir_incomplete'])==(60,75,60,12)
    assert ab_ir['main_ir_reset_slots']==ab_ir['ab_measurement_background_slots']==0
    assert ab_ir['producer_sha256']==sha(Path(__file__).parent/'summarize_ab_ir_completed.py')
    for field,name in [('tables_audit','ab_ir_completed_tables_audit'),('exports_audit','ab_ir_completed_exports_audit'),
                       ('visual_review','ab_ir_completed_visual_review')]:
        assert ab_ir[field+'_sha256']==sha(PACKAGE/'results'/f'{name}.json')
    for name,value in ab_ir['report_hashes'].items():assert sha(PACKAGE/name)==value
    ab_ir_tables=json.loads((PACKAGE/'results/ab_ir_completed_tables_audit.json').read_text())
    assert ab_ir_tables['status']=='passed'
    assert ab_ir_tables['checker_sha256']==sha(Path(__file__).parent/'verify_ab_ir_completed_tables.py')
    assert ab_ir_tables['statistical_checker_sha256']==sha(Path(__file__).parent/'verify_free_sensitivity_tables.py')
    for i,(prefix,stem,report,producer) in enumerate([
        ('ab','ab_dummy_first_completed_snapshot','56_AB_CB完整结果与强基线.md','freeze_ab_dummy_first_completed.py'),
        ('ir','ir_compressed_completed_snapshot','58_IR压缩位置表完整结果.md','freeze_ir_compressed_completed.py')]):
        source=PACKAGE/'results'/f'{stem}.json';snapshot=json.loads(source.read_text())
        assert ab_ir[prefix+'_source_sha256']==ab_ir_tables['artifacts'][i]['source_sha256']==sha(source)
        assert ab_ir_tables['artifacts'][i]['report_sha256']==sha(PACKAGE/report)
        assert snapshot['producer_sha256']==sha(Path(__file__).parent/producer)
        for name,value in snapshot['helper_hashes'].items():assert sha(Path(__file__).parent/name)==value
        for receipt in snapshot['receipts']:assert sha(PACKAGE/receipt['path'])==receipt['sha256']
    ab_ir_exports=json.loads((PACKAGE/'results/ab_ir_completed_exports_audit.json').read_text())
    ab_ir_visual=json.loads((PACKAGE/'results/ab_ir_completed_visual_review.json').read_text())
    assert ab_ir_exports['status']=='passed' and ab_ir_visual['status']=='visually_reviewed'
    assert not ab_ir_visual['unresolved_layout_defects']
    assert ab_ir_exports['tables_audit_sha256']==sha(PACKAGE/'results/ab_ir_completed_tables_audit.json')
    assert ab_ir_exports['checker_sha256']==sha(Path(__file__).parent/'verify_ab_ir_completed_exports.py')
    assert ab_ir_visual['numerical_audit_sha256']==sha(PACKAGE/'results/ab_ir_completed_exports_audit.json')
    assert len(ab_ir_exports['figures'])==len(ab_ir_visual['figures'])==2
    for numeric,visual in zip(ab_ir_exports['figures'],ab_ir_visual['figures']):
        assert numeric['stem']==visual['stem']
        for ext in ('svg','png'):
            assert numeric[ext+'_sha256']==visual[ext+'_sha256']==sha(PACKAGE/f"figures/{visual['stem']}.{ext}")
        assert numeric['data_sha256']==sha(PACKAGE/f"figures/{visual['stem']}_data.json")
    ir_guarded=json.loads((PACKAGE/'results/ir_guarded_preparation_evidence.json').read_text())
    assert ir_guarded['status']=='preparation_checked' and not ir_guarded['target_experiment_complete']
    assert not ir_guarded['model_bandwidth_claim'] and not ir_guarded['original_outcomes_replaced']
    assert ir_guarded['plan_sha256']==sha(PACKAGE/'formal_ir_guarded_plan.json')
    assert ir_guarded['replay_sha256']==sha(PACKAGE/'results/ir_reset_window_replay.json')
    assert ir_guarded['small_runner_checks_sha256']==sha(PACKAGE/'results/ir_guarded_runner_checks.json')
    assert ir_guarded['report_sha256']==sha(PACKAGE/'60_IR重置压力诊断与补充实验.md')
    assert ir_guarded['producer_sha256']==sha(Path(__file__).parent/'summarize_ir_guarded_preparation.py')
    deadq=json.loads((PACKAGE/'results/ab_deadq_allocator_evidence_audit.json').read_text())
    assert deadq['status']=='evidence_consistent' and not deadq['full_security_admission'] and not deadq['bandwidth_claim']
    assert deadq['model_receipt_sha256']==sha(PACKAGE/'results/ab_deadq_allocator_model_checks.json')
    assert deadq['report_sha256']==sha(PACKAGE/'52_AB_DeadQ所有权与联合重建.md')
    assert deadq['auditor_sha256']==sha(Path(__file__).parent/'audit_ab_deadq_allocator_evidence.py')
    routed=json.loads((PACKAGE/'results/ab_deadq_routed_evidence_audit.json').read_text())
    assert routed['status']=='passed' and not routed['native_AB'] and not routed['CB_integration']
    assert routed['source_sha256']==sha(PACKAGE/'results/ab_deadq_routed_checks.json')
    assert routed['report_sha256']==sha(PACKAGE/'54_AB_DeadQ认证路由与加密检查.md')
    assert routed['auditor_sha256']==sha(Path(__file__).parent/'audit_ab_deadq_routed_evidence.py')
    classical_done=json.loads((PACKAGE/'results/classical_completed_snapshot.json').read_text())
    assert classical_done['status']=='passed' and classical_done['new_runs']==10 and classical_done['reused_controls']==20
    assert classical_done['producer_sha256']==sha(Path(__file__).parent/'freeze_classical_completed.py')
    assert not classical_done['replaces_main_Path_Z4'] and not classical_done['full_security_admission']
    for name,value in classical_done['proof_hashes'].items():assert sha(PACKAGE/'results'/name)==value
    public_table=['| 前端 | 公开记录 | 比较 | 基线bytes/op | selective bytes/op | 平均节省 | 五窗口范围 |',
        '|---|---|---|---:|---:|---:|---|']
    for e in public['effects']:
        assert e['n']==5 and e['ci95'] is None
        public_table.append(f"| {e['family']} | {e['workload'].replace('_startkey','')} | {e['baseline']} → {e['variant']} | {e['baseline_mean']:.2f} | {e['variant_mean']:.2f} | {e['mean']:.3f}% | [{e['range'][0]:.3f}%, {e['range'][1]:.3f}%] |")
    md=['# 实验章节草稿（持续更新，未达到投稿完成态）','',
        '本稿中Freecursive/ρ基础与敏感性、IR有限前缀及完整周期集成、B1核心、静态IR/AB组件、B2消融和调优主比较已有完整重复及统计。公开trace的80次运行亦完成，五个相邻窗口的统计另列。AB-CB的60次运行全部完成；IR压缩map的75个正式观测全部收齐，其中主组60次完成，压力组3次完成、12次暖机窗口未完成，失败完整保留。规模实验仍在执行，IR/AB原生机制及证明缺口仍在后文列出，不能将未完成部分删去后视为全目标完成。','',
        '## 实验方法','',
        '我们比较实际执行产生的双向应用协议字节数，以每个完成的应用请求为单位。指标包括数据密文、nonce、桶头、认证证明、控制帧、递归位置表访问，以及定期维护和提前重建。数据槽包含真实块与dummy块，不等同于有效应用payload。初始化、预热和测量分别记账。通信通过进程内未可信服务器执行，不计TCP/TLS封装，不报告网络延迟或原型运行器加速比。','',
        '所有后端比较使用相同请求序列和公开配置，对每个请求核对返回值。请求密文实际生成和传输；独立账本根据操作码、mask、槽位与序列化规则核对每个RPC。跨后端前端迁移序列及缓存指标保持一致。五个独立合成输入种子分别配对，先计算每对的相对节省，再报告均值和95% Student-t区间。区间半宽超过5个百分点或任一方成本变异系数超过10%时，整个比较组增加到10次，不按收益方向追加。','',
        '合成负载包括均匀访问、固定1%热区承载90%请求、Zipf(0.9)和循环扫描，各50%读与50%更新。它们是块级trace，不是完整YCSB引擎。公开Financial1/WebSearch1回放保留命令起始键的局部性，预选相邻窗口只报告配对均值与范围。','',
        '## Freecursive与ρ组合结果','',
        '本组N=4096、B=64字节，预热2048请求、测量4096请求，每个配置5次重复。Freecursive使用统一递归map树、压缩计数器与地址LRU的PLB；ρ使用地址LRU的两树缓存前端。二者保留本研究认证格式，其实现范围不等同于论文原生硬件系统。','',
        '| 前端 | 负载 | 比较 | 基线字节/请求 | selective字节/请求 | 平均节省 | 95%区间 |','|---|---|---|---:|---:|---:|---|']
    for r in complete:
        lo,hi=r['ci95'];md.append(f"| {r['family']} | {r['workload']} | {r['baseline']} → {r['selective']} | {r['baseline_mean_bytes']:,.2f} | {r['selective_mean_bytes']:,.2f} | {r['paired_mean_saving_pct']:.2f}% | [{lo:.2f}%, {hi:.2f}%] |")
    md+=['',
        '保留Freecursive前端压缩后，SDE相对Deferred减少21.81%–21.87%的总通信，R0相对Ring减少24.43%–24.55%。原始map到压缩map的收益另列，以避免把压缩收益归于selective。对ρ，SDE和R0的整体通信收益约8.3%和11.6%；其后端自身仍分别减少约21.9%和24.5%，整体比例较低是因为未改变的前树流量占比。每个种子都验证了“总体节省=原后端占比×后端自身节省”。','',
        '相对节省与绝对成本需要同时比较。在本64B认证布局和uniform负载下，Freecursive+SDE约32,007字节/请求，Freecursive+R0约45,889字节/请求。R0相对自身Ring基线的节省更高，并不意味着其绝对通信低于SDE。分项图显示认证和头部在小块配置中占比较大。','',
        '配套图：`figures/composition_paired_progress.pdf` 与 `figures/frontend_bandwidth_breakdown.pdf`。原始240次运行和120对计算在XLSX中，来源hash随行保存。','',
        'Freecursive预声明的五组敏感性切片也已全部完成，100次新运行加60次既有对照独立核对来源、返回值、账单、前端时隙和对象空间，32格绝对开销与36组配对效应见49号报告。64B压缩前端改变PLB为4/32条或β为4位时，SDE仍减少21.80%–21.85%，R0减少24.45%–24.48%；4096B配置下，SDE减少24.04%–24.08%，R0减少22.05%–22.09%。两条路线均超过20%只限于这些已测配置，不是对全部ORAM的保证。','',
        '前端参数的代价独立列出：PLB8→32条降低通信约39.2%–39.3%，但使用更多客户端PLB空间；β14→4位使group reset测量均值增至283.8次，总通信增加约91.1%。这些代价不能归为selective效应。4096B时raw/compressed两种map在暖机后均驻留于PLB，压缩没有可辨识的额外通信节省；同前端的selective收益仍然存在。块长切片同时改变X和固定PLB条目数所对应的字节预算，不是固定X或固定可信内存的单因素对比。该证据不含原生PMMAC、硬件控制器和真实可信峰值。','',
        'Freecursive敏感性双面板矢量图见51号报告及 `output/pdf/completed_free_sensitivity.pdf`：左侧列同前端配对减少率，右侧列四后端在PLB/β变化后的绝对KiB/request。32组图元全部从原始账单重算，最终渲染已审阅。','',
        'ρ的120次新敏感性及60次既有对照现已全部完成，九配置、四后端各五次，36格绝对成本、18组selective与24组参数效应通过独立复核。50号报告保留全部分账，55号报告与 `figures/completed_rho_sensitivity.svg` 给出完整图表；从原始收据重算54组均值/区间，并核对SVG实际柱宽和最终渲染。独立地址模型执行45组缓存重放，逐帧检查唯一驻留、总人口及前后树迁移摘要；它不替代安全证明。预声明220次Freecursive/ρ新敏感性已全部收齐。','',
        'Uniform的前后树访问比n从1、3增至5时，SDE整体节省分别为14.122%、8.290%、5.864%，R0分别为17.863%、11.647%、8.629%。九配置整体范围为SDE 5.864%–14.122%、R0 8.629%–17.863%，不是所有负载的保证。后端自身仍约22%/24.5%，未优化前树流量解释整体收益的变化。','',
        'ρ在Hot-90中将LLC32→128，绝对通信降低约43.6%，但selective整体比例仍约8.3%/11.6%，因为前后树随帧数一起减少。在Zipf(0.9)中将ρ缓存128→32，SDE/R0相对各自基线的减少率升至9.34%/12.83%，但自身总通信分别增加约3.43%/5.22%。这些已完整重复的切片说明更高的相对减少率不一定对应更低的绝对成本；容量变化同时改变资源和前树几何，不能称等可信内存优化。','',
        '## 核心、消融与有限调优','',
        '核心保留Path、Deferred、SDE、Ring、GC-Ring、R0，以区分维护策略、selective读取和省根差异。60次核心与80次静态IR/AB组件全部完成独立答案、账单、递归时钟及配对统计审计，28格各5次、18个效应均未触发追加门槛。B1同Z4/A3/S3配置中，SDE对Path约35.80%–35.89%、对Deferred约24.13%–24.24%，R0对Ring约26.54%–26.63%；这些是同固定参数结果，不能替代双方分别调优的主比较。见36号文档。','',
        'B2的45个观测已全部独立审计。compact开启后，Z4配置的fusion仅减少约0.84%字节，但减少约15.51% RPC；Z7配置字节减少约0.40%。小map、compact、fusion、Z/A/S及几何调整的顺序链合计减少约31.15%字节，不能称纯selective收益，也不能把各步百分比相加。完整四格与顺序链见34号文档及 `output/pdf/completed_r0_ablation.pdf`。RPC减少不是实测延迟收益。','',
        '72个有限候选先用完整周期模型筛选，各方独立选择后，B3的50次实测均已完成独立审计；每种负载各5个配对种子，六组比较均未触发追加门槛。N16384、数据块4096B、map块256B、R256；Path/Deferred/SDE选Z4/A3，Ring选Z7/A6/S9，R0选Z7/A6/S6。SDE相对调优Path减少35.767%–35.788%，相对Deferred减少24.176%–24.200%；R0相对调优Ring减少25.366%–25.394%。完整绝对开销、95%配对区间、50行原始数据和已核验矢量图见47号文档及 `output/pdf/completed_tuned_bandwidth.pdf`。','',
        '该测量窗口在完整初始化及2048次暖机后计量4096次请求，数据层仅覆盖49152维护周期的1/12，位置表层覆盖768周期的16/3。五个种子的区间不包含改变维护相位的效应，因此不将实测比例改称稳态收益。Ring→R0完整周期模型为24.579%，较本次有限窗口配对值低0.787–0.815个百分点；48号文档保留模型与实测分栏及全部100行逐层时钟。N256/B64校准误差不能外推到此不同规模和窗口。','',
        '上述主比较采用共同资源筛选上限，实际占用另列；范围不覆盖全部Z/A、XOR、缓存、递归布局或所有先进ORAM，不能称全局最优。Path Z5/R258补充批次不混入该主图。规模/块长批次仍在执行，进度见15号文档；前端敏感性已完整报告。','',
        '独立空间核验已按深度重算220份完成运行的服务器对象与缓存前缀，形成30格对照；另检查72个候选和每个入选配置的一份实际对象账单。入选Ring(Z7/A6/S9)为1067.267MiB、R0(Z7/A6/S6)为870.210MiB，R0少18.464%；这只说明其空间代价，不是新的带宽百分比。双方核心stash预留payload加terminal均为1.063477MiB。共同4GiB服务器上限不意味着实际占用相同，256MiB客户预算也仅覆盖已声明的有限口径。','',
        '44号文档分别列服务器内容、可信缓存前缀、stash payload预留和terminal，组合前端还保留PLB/LLC及完整PosMap等声明。8种自洽或不自洽的损坏空间账单均被拒绝。56/58号完整集成IR/AB结果也已逐层重算对象空间及已列客户资源，其余未完成切片仍待补。并存密文、decoded payload、final-write帧、认证scratch及元数据/分配器未被完整计入，因此尚不能声称真实可信峰值预算已通过。','',
        '## 公开trace局部性回放','',
        'Financial1和WebSearch1各5个预选相邻窗口，两个前端各运行四后端，80次全部完成；N16384/B64，每窗2048条暖机、4096条测量命令。独立重放61440条源命令验证键映射、读写和时间边界，并从版本历史重算返回值摘要。窗口范围不代表独立总体置信区间；原始I/O长度及到达时间未重放，主张限定为命令起始键局部性。各比较同输入、同前端工作量；ρ还核对前树转录完全一致。','',
        *public_table,'',
        'Freecursive总通信节省约22.04%–22.06%（SDE）和24.04%–24.08%（R0）；ρ整体分别约9.10%–9.11%和12.25%–12.26%。ρ各窗口仍精确满足“整体节省=原后端占比×后端自身节省”。这些是明确适配范围内的公开窗口结果，不代表完整原生系统或全部实际应用。42号文档及 `output/pdf/completed_public_workloads.pdf` 提供16格绝对开销、8组配对结果、80份原始来源及核验。','',
        '## 规模与敏感性（证据尚未收齐）','',
        '规模切片、块长、PLB、β、LLC、ρ缓存和前后树帧比例按12号文档执行。完整周期模型与有限前缀实测分栏。N256/B64的8组配置、每组5次完整周期校准已完成；最大平均相对模型偏差绝对值为0.15648%，八组95%区间均包含零偏差。图为 `figures/completed_model_calibration.pdf`，两张CSV包含全部40次及8组汇总；数值重算与版面核验通过。该误差范围不能推广到未测规模或新CB/DeadQ协议。详见26号文档。公开trace没有输入到达时间，不能据此推出DWB减少了多少CPU阻塞或完成时间。','',
        '## IR与AB（仍有原生机制和证明缺口）','',
        '当前IR四格为异质真实容量与固定树顶缓存，统一使用通过条件数值准入的R480。AB四格为静态dummy容量与固定树顶缓存。两类静态组件均已每格完成5次。异质IR静态组件在4KiB块下对Deferred减少约21.53%，在64B下约19.24%；静态AB对Ring约23.98%–25.95%。完整IR-Stash的随机位置相关命中和set冲突、AB的green迁移及DeadQ远端槽复用尚未被当前SOC3容量证明覆盖。组件结果应单独标注，不等同于完整原生系统收益。','',
        '独立新增IR-Stash双索引、冲突跳过和加密本地读写后端，6组功能与6个远端认证失败检查通过。数据块本地命中接口有12组前端/LLC/DWB组合检查；后续已扩展到全部raw map层，以临时句柄直接访问本地canonical map，远端map才转移到PLB。新增两种递归深度的24组检查、6个map认证失败和过期句柄检查通过。压缩reset尚未接入；这些测试不作为性能样本。固定公共时隙需由DWB或dummy填充，不能将本地命中率直接乘入总通信节省。新自适应安全和容量归约仍待完成。详见35、38号文档。','',
        '进一步的精确转录审计在当前本地跳过适配中发现反例：L1/N2/Z1/A2和相同可观察初始化前缀下，请求0或1的下次远端路径分布分别为(3/4,1/4)与(5/8,3/8)，总变差为1/8；关闭skip的对照均为均匀分布。384次实际加密执行复核了此路径字段投影，说明固定时隙与独立均匀dummy不足以证明该适配安全。此结论针对本项目的UID贪心/跳过适配，不是原生IR论文攻击或目标规模优势估计。新skip版本暂不进入性能主张，继续修复和理论研究；功能检查通过不替代安全。详见39号文档。','',
        '修正候选的精确模型进一步枚举长度1至4的全部请求串，覆盖24种策略组合、96行结果。5376次实际加密执行复核了42个两请求PMF：随机平局放置消除单请求目标差异，但00和01两请求串的路径投影TV仍为3/16；旧叶dummy且不remap也从两请求起出现差异。40号文档给出公开历史下的条件混合分布必要条件。模型中排除本次目标回填的局部候选也不足以修复；该候选及长度3/4结果仅为精确模型诊断，不冒称原生IR复现或全部加密交叉核对。','',
        '进一步对齐秘密随机装载顺序与排除当前目标的Path回填，6个候选的两请求见证由2176次加密执行复核，差异仍未消失。另在Z4、叶深度L2、N2、缓存根的无容量争用实例中完成2048次加密交叉检查：相同公开初始化前缀[0,0]下，请求串00/01的第二叶落入{2,3}的概率分别9/16和3/8，差值及两路径TV均3/16。这是本项目明确适配的反例，不是完整原生IR系统攻击或目标规模的量化结果；尚不能以增大桶/stash或只修初始化排序来签发安全准入。见43号文档。','',
        'DWB现已接入真实异质树、前缀缓存、raw递归位置表、组相联LLC与公共时隙控制器；已验证中途前台驱逐map后的继续执行、dirty版本变化、最终ACK与永久停止。120次有限前缀及60次完整周期实验均已完成，每格5次，各自40/14组条件效应未触发追加重复门槛。双方固定W时隙与Q个已完成请求，终点允许LLC中dirty驻留。Path/Deferred在该分母下DWB开关的总字节相同；移出前台的回写不能直接称通信节省。该运行管线未启用上述新skip适配。详见19、21、22号文档。','',
        '64B集成实验包含N4096数据块、4369个数据及位置表记录，128次暖机及256次测量应用请求，分别固定1024和2048个公共时隙。非均匀桶配置下，SDE相对同维护Deferred减少19.10%–19.25%，相对Path减少9.63%–9.80%；均匀桶对照分别为20.20%–20.36%和13.75%–13.93%。认证与桶头可以使Deferred总成本高于Path；不能只引用较大的百分比，也不能宣称除ρ外均超过20%。这些是已完成的有限窗口结果，不等于稳态或完整原生IR。','',
        '配套图为 `figures/ir_integrated_finite_gain.pdf` 和 `figures/ir_integrated_finite_breakdown.pdf`，均另有SVG；表格为 `tables/IR_DWB_120_runs.csv` 和 `tables/IR_DWB_40_comparisons.csv`。表中每项均可追溯原始收据及hash，均值和95%区间已从原始总字节重新计算。详见23号文档。','',
        '完整周期复核采用相同N4096/B64异质布局、前6层缓存、PLB8和LLC8组×2路；初始化后7919个dummy槽独立计费对齐，暖机1536请求/12288槽，测量6144请求/49152槽，覆盖四个Deferred/SDE维护周期。Path使用同长度参考窗口。SDE对Deferred减少19.195%–19.216%，对Path减少9.750%–9.773%。固定时隙下DWB使Path/Deferred总通信变化严格为零；SDE的热点/均匀负载效应为−0.004%/0.025%，95%区间分别[−0.054%,0.046%]/[−0.016%,0.067%]，不据此声称DWB本身减少总通信。有限周期不等同稳态。41号文档及 `output/pdf/completed_ir_periodic.pdf` 提供全部60行、14组比较和已核验矢量图。','',
        '压缩map跨时隙DWB的75个正式观测已全部收齐，并与60份raw-map对照固定在58号报告。β14主组60次全部完成；SDE相对同布局Deferred减少19.1871%–19.2002%，相对Path减少9.7415%–9.7561%。31个预声明比较位置中26组有完整五对，5组涉及未完成压力窗口，不报告成功子集的性能均值。Path/Deferred在相同完整时隙窗口下的DWB和packing对照字节相等；前端工作减少并不自动减少固定窗口的总通信。','',
        'β14主组全部60次测量均未触发group reset。β4压力组的15次中，只有seed101的三后端完成；seed102–105的三后端分别在暖机完成1535、1534、1531、1535个请求时到达公开窗口末尾，均未达到1536个请求，因此没有进入正式测量。这12次不是stash溢出，也没有独立partial-answer摘要，不计算每个正确完成请求的收益。启动前pilot的6143/6144发生在measurement阶段，与正式失败阶段不同。59号报告与 `figures/completed_ir_compressed.svg` 同时展示八组主性能比较和全部15个压力结果；主组不能用于声称reset代价很小，亦不包含IR-Stash或原生PMMAC。','',
        '60号报告的诊断重放与原Hot90/DWB-on的30份加密运行记录匹配，发现原暖机最后一次到达后只剩8槽，而失败截点都有尚未结束的底层组重置。逻辑续行需额外20–26槽完成暖机，不能将此预测当作新的实测带宽或延迟。为获得完整reset压力对照，另固定两阶段各增加一个公开维护周期的新设计：β14/4、三个后端、五个种子共30次新运行。额外尾部对所有方案相同且全部计费，正式测量槽数增加25%；原75个结果不修改。六组小规模真实密文检查和七项损坏账单拒绝已通过，目标规模结果仍待收齐，不据此补写性能结论。','',
        'AB的CB已实现独立认证原型，包含加密green计数、非目标真实块保留、逐层物理dummy为零，以及公开count决定的维护读取长度。24组引擎功能检查、2658个局部有理数分布检查和三个主动失败检查通过。递归raw map、PLB、inclusive LLC和阈值后台控制已接入；另有12组控制器、6组串行压缩map、3组显式较高装载率及2个后台主动失败检查。串行压缩map检查不代表压缩map的跨时隙DWB已实现。','',
        '六组N512/B64集成试运行及十二组压力诊断均已通过独立收据审计；压力控制使用普通CB dummy Transfer，可能搬出green块，尚未等同于原文strict-dummy后台策略。R0的已缓存根只保留标签，因此实际缓存对象比Ring/GC-Ring少1868字节；三者缓存层数和PLB/LLC/stash预算相同，未将省下空间再分配。原H48阈值在测量阶段没有触发，新增H24/L16与关闭压力的对照只作事先声明的单种子压力诊断。底部D0/H24点Ring、GC-Ring和R0测量后台时隙分别776、1、16；不据此推断稳态、尾界或普遍性能。','',
        '进一步预定义了60次N4096/B64的CB条件实验：2种布局×3后端×2负载×5种子；初始化后对齐，暖机1个完整维护周期、测量4个周期。首个Ring+CB在连续初始化加载时发生R500 stash溢出，批次已停止。公开节拍加载修订随后通过均匀桶三组受控检查，但底三层D0的Ring在65536时隙内未完成请求，新批次启动门槛将其拦下。逐时隙诊断显示这些时隙全部用于后台、完成请求为零；不能将该配置的通信除以4096伪造bytes/op。','',
        '独立增加优先未读dummy、必要时green的选择策略，依据AB与String对CB的描述，保留原全未读槽均匀选择实现。修订已有24组功能、2658组局部精确分布、3个认证失败、12组递归/LLC/压力以及6组周期驱动和7个损坏收据拒绝检查。相同目标规模诊断中，新策略完成4096个正确读回、后台槽位为零、完成边界stash峰值11；这是一种子正确性诊断，不能当作独立正式性能组。六组目标规模受控验证全部通过后才生成ABDF的60格正式计划。它在满真实D0桶中仍可能搬green，不声称严格dummy后台或完整自适应模拟。详见27、30号文档。尚无green感知容量归约或DeadQ，不能将旧静态Y=0结果或试运行推广为完整AB收益。','',
        'ABDF的60次正式运行现已全部完成，12格各五种子、18组配对效应及全部资源/分项账单冻结在56号报告。R0相对Ring+CB减少20.2372%–21.9777%；相对GC-Ring+CB的四组均值仅−0.002497%至+0.002485%，全部95%区间包含零，RPC数量也未减少。可信缓存已经覆盖树根，因此省根没有可再次消除的远程根通信。主文需同时保留强对照，不能把相对Ring的全部节省归为超越GC-Ring的额外贡献。','',
        '57号报告与 `figures/completed_ab_cb_bandwidth.svg` 并列展示Ring和GC-Ring两种分母。green迁移和neutral重建实际发生，但全部12格测量阶段的background_slots均为零；H48/L32阈值配置和功能测试不能替代正式后台压力性能证据。本批仍是无DeadQ、允许green回退的条件协议结果。新DeadQ分配器尚未接入，其索引和认证成本没有被计入这60次结果。','',
        'DeadQ另有一个未进入性能实验的新分配器候选：限制活跃借用关联组件至多K个桶，原桶维护时暂存并联合重建整个组件，再尝试扩张。它在零额外持久数据槽下给出首次扩张见证，避免只覆盖原位槽而破坏借用者；代价是至多K−1个连带重建桶及认证映射开销。两组小域归一化状态图共1976个状态、12792条转移自然闭合，另有2500步符号记录和九项提交/租用检查。详见52号报告。它是新增公开所有权契约，尚无加密ORAM集成、真实可信峰值或正带宽结论，不能替代原生AB DeadQ，也不能改变既有ABDF的证据范围。','',
        '54号报告进一步实现了该分配器的外部Merkle索引和AES-GCM记录路由：客户端不常驻完整owner表，验证公开组件后暂存并重建，最终提交通过后才发布根和虚拟消费租用。1,000步加密对照包含111次扩张、101次连带重建，13项认证/中止检查通过；六份原始wire共18,364个RPC、1,006次提交另行重算认证根和字节。四物理槽的六操作见证保留远端真实记录，总通信21,719字节，只有16.28%属于密文记录，其余为索引、证明和控制。此微观成本不等于完整AB收益；CB/γ/fresh remap、动态阈值、容量与自适应转录仍未集成。','',
        '## 经典基线的安全参数核对','',
        '经典基线现已绑定成功认证前缀的逻辑放置过程、真实递归初始化访问数及完成态时钟。24组加密诊断核对5076个完成态，包含三层递归、非空stash、neutral恒等与fusion目标移除；22个主动响应检查覆盖Path Z5和Ring Z7/S9。它们是有限实现核验，完整转录模拟及PRF预算仍不由测试代替。详见45号文档。','',
        '当前核心按2^56个应用请求、每层Q_j=2^56+Σ(i≤j)N_i和stash预算2^-130记账。Ring显式采用A−1阶段余量，其Z4/A3和Z7/A6现用R256仍通过经典stash表达式。Path Z4仍保留为经验调优强基线；补充Z5/R258的uniform/hot90各5次已全部完成，657456 bytes/op为每次实际帧账单的测量值，并与确定性模型一致。结合20次复用的Path Z4/SDE，53号报告冻结30份来源、六格及六组配对结果。SDE相对Z5减少48.448%–48.464%，仍保留相对Z4减少35.767%–35.788%作为主比较，不用更贵的补充基线放大主文收益。','',
        '29号文档的2^96寿命表保留为历史算术口径；若将Ring界用于任意完成访问边界，45号文档给出加入A−1后的保守修订。上述账本限定均匀核心、固定地址历史和理想独立叶标签；完整主动安全准入、公开寿命执行限制及真实可信峰值仍须补齐。IR-Stash、CB、异质容量和DeadQ不能继承该账本。','',
        '## 当前必须补齐的交付','',
        '- 全部正式重复、预设追加样本门槛及失败记录审阅。',
        '- 剩余规模/块长主图与原始表；已完成Freecursive/ρ敏感性、经典Path补充表、调优主比较、核心、静态组件、消融、公开trace及IR周期图表不重复生成。',
        '- IR-Stash安全修复及压缩map联动；完成新公开尾部窗口的30次reset压力补充及统计，保留原未完成窗口。AB CB的容量归约、原生后台策略与安全边界、DeadQ与CB集成及同物理预算对照。',
        '- 每个主表配置的独立安全准入和基线保证，真实服务器对象空间与逻辑客户端预算。',
        '- 全要求逐项审计及可独立复现的最终工件。无需用真实加速比作为完成条件。']
    (PACKAGE/'18_实验章节草稿_持续更新.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    extra=['ir_dwb_controller_checks.json','ir_dwb_analysis_checks.json','ir_dwb_statistics.json','ir_periodic_runner_checks.json','cb_engine_checks.json',
        'ab_cb_frontend_checks.json','pilot_ab_cb_audit.json','ab_cb_audit_checks.json','ab_cb_pilot_summary.json','ab_periodic_checks.json',
        'ir_finite_exports_audit.json','ir_finite_visual_review.json',
        'calibration_completed_snapshot.json','calibration_exports_audit.json','calibration_visual_review.json',
        'ab_paced_controlled_failure.json','ab_dummy_first_checks.json','ab_dummy_first_frontend_checks.json',
        'ab_dummy_first_periodic_checks.json','ab_selection_diagnostic.json','ab_selection_diagnostic_audit.json',
        'baseline_capacity_arithmetic.json','baseline_capacity_arithmetic_audit.json',
        'core_components_complete_audit.json','ablation_complete_audit.json',
        'ir_stash_engine_checks.json','ir_stash_frontend_checks.json','ir_stash_raw_maps_checks.json',
        'core_components_exports_audit.json','core_components_visual_review.json','ir_stash_transcript_counterexample.json',
        'ir_periodic_statistics.json','ir_periodic_exports_audit.json','ir_periodic_visual_review.json',
        'ir_skip_repair_exact_model.json','ir_skip_repair_model_crosscheck.json','ir_skip_repair_evidence_audit.json',
        'public_completed_audit.json','public_exports_audit.json','public_visual_review.json',
        'ir_initialization_alignment_model.json','ir_initialization_alignment_crosscheck.json','ir_z4_skip_projection.json',
        'ir_source_alignment_evidence_audit.json','storage_components_audit.json','storage_audit_rejections.json',
        'classical_execution_projection_checks.json','classical_stash_execution_ledger.json',
        'classical_stash_execution_ledger_audit.json','classical_active_failstop_checks.json',
        'classical_reference_evidence_audit.json','classical_minima_audit.json',
        'tuned_completed_snapshot.json','tuned_exports_audit.json','tuned_visual_review.json','tuned_model_window_audit.json',
        'free_sensitivity_completed_audit.json','free_sensitivity_tables_audit.json',
        'free_sensitivity_exports_audit.json','free_sensitivity_visual_review.json','rho_sensitivity_audit.json','rho_sensitivity_checks.json',
        'ab_deadq_allocator_model_checks.json','ab_deadq_allocator_evidence_audit.json','classical_completed_snapshot.json',
        'ab_deadq_routed_checks.json','ab_deadq_routed_evidence_audit.json',
        'rho_sensitivity_completed_snapshot.json','rho_sensitivity_exports_audit.json','rho_sensitivity_visual_review.json',
        'rho_sensitivity_completed_evidence.json',
        'ab_dummy_first_completed_snapshot.json','ir_compressed_completed_snapshot.json',
        'ab_ir_completed_tables_audit.json','ab_ir_completed_exports_audit.json',
        'ab_ir_completed_visual_review.json','ab_ir_completed_evidence.json',
        'ir_reset_window_replay.json','ir_guarded_runner_checks.json','ir_guarded_preparation_evidence.json']
    save(PACKAGE/'results/evaluation_draft_sources.json',dict(generator_sha256=sha(__file__),paired_statistics_sha256=sha(p),
        additional_sources={n:sha(PACKAGE/'results'/n) for n in extra},complete_frontend_rows=16,complete_public_rows=8,
        completed_ir_periodic_runs=60,completed_free_sensitivity_runs=100,reused_free_sensitivity_controls=60,
        completed_rho_sensitivity_runs=120,reused_rho_sensitivity_controls=60,
        completed_ab_cb_runs=60,observed_ir_compressed_runs=75,passed_ir_compressed_runs=63,
        incomplete_ir_compressed_runs=12,reused_ir_raw_controls=60,full_chapter_complete=False))
    print(json.dumps(dict(frontend_rows=16,full_chapter_complete=False)))

if __name__=='__main__':main()
