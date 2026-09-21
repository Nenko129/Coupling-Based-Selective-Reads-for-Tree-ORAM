# 执行衔接更新：第十八版

完整目标继续active，不标complete或blocked。上一个有实验工作的goal轮完成AB/IR冻结图表，属于progress；紧邻的简短问答仅澄清既有带宽口径。本轮将这些证据接入章节、补齐索引，并诊断IR reset压力失败，完成新真实执行门控、预声明并启动30次补充，属于progress。没有需要用户解除的阻塞。

## 1. ABDF和原压缩IR批次已终止；不要重启

- ABDF完成文件 `results/ab_dummy_first_periodic_queue_completion.json` 为passed60。父50656已不在真实进程列表。新冻结快照 `results/ab_dummy_first_completed_snapshot.json` 为60份、12格、18效应，所有比较各5对，无追加重复门槛。
- 56号完整原始表/资源/分项；57号强基线与机制覆盖。R0对Ring+CB减少20.2372%–21.9777%；对GC-Ring+CB四组均值仅−0.002497%至+0.002485%，全部95%区间包含0。实际RPC不变；根已在缓存中。正式12格测量background_slots全部0，green/neutral非零，不把控制器功能测试当压力性能结果。
- 原压缩IR完成文件 `results/ir_compressed_observation_completion.json` 为completed_with_incomplete_windows，75个全部收齐、63成功、12失败。父54408已退出。不能为覆盖失败而重跑这75个ID。
- β14主60/60；β4 stress15中seed101三后端完成，其余12均停在warmup：seed102/103/104/105分别1535/1534/1531/1535，分母1536。不是stash overflow，未进入measurement。原β4 pilot另为measurement6143/6144，不能混淆。
- 58/59号和 `results/ir_compressed_completed_snapshot.json` 冻结75新观测+60raw对照。15格，26完整比较，5个涉及未完成压力格的比较保留位置但不报告成功子集均值。135份来源中123份完整运行重算资源，12份失败核对窗口/账单；原失败无独立partial-answer摘要。
- IR主SDE对Deferred减少19.1871%–19.2002%，对Path9.7415%–9.7561%。主60次measurement reset槽全部0，不能推断reset成本小。仍无原生IR-Stash/PMMAC，新skip适配反例未修复。

### 已完成图表及绑定

- `src/verify_ab_ir_completed_tables.py`：195份来源，独立配对统计/分项/资源/矩阵覆盖；11种损坏被拒绝。
- `figures/completed_ab_cb_bandwidth.svg`、PNG、data JSON；实际12根SVG有符号柱宽核对。
- `figures/completed_ir_compressed.svg`、PNG、data JSON；实际8根柱宽及全部15个压力色块核对。
- 最终PNG已实际审阅，AB2190×1107、IR2334×1158；无未解决版面缺陷。无需无理由重绘。
- `results/ab_ir_completed_tables_audit.json`、`ab_ir_completed_exports_audit.json`、`ab_ir_completed_visual_review.json`、`ab_ir_completed_evidence.json` 均完整绑定。56–59号报告不要直接修改而不刷新绑定。
- `src/freeze_ab_dummy_first_completed.py`、`src/freeze_ir_compressed_completed.py` 已绑定不可变快照；不要随意改源码后重新生成。它们保留原协议边界，不是完整原生AB/IR安全准入。

## 2. IR窗口诊断：逻辑重放与原真实执行吻合

新增 `src/ir_reset_window_replay.py` 和 `results/ir_reset_window_replay.json`。

- 使用原staged compressed frontend/Controller，单独以明文地址→(leaf,payload)字典作诊断backend；逐Transfer验旧叶和所有权、返回值。该O(N)字典只是test oracle，不是免费生产可信结构，不提供通信数值或安全证明。
- 原Hot90/DWB-on、β14/4、五种子×三个后端共30份加密记录全部匹配：成功者完整答案与schedule/metrics；失败者阶段、部分完成数、reset游标、队列、时钟、map计数及移除/接纳摘要。
- 原最后一次到达后只有8槽，底层group reset最多32个子块。β4 seed102–105原暖机截点分别在reset cursor12/15/28/7。
- 逻辑续行完成原暖机另需22/20/21/26槽；是模型诊断，不是实测延迟或新密文性能。新暖机guard后的measurement仅seed102越过原截点17槽；其余为0，不可当作原失败者的旧measurement结果。
- 逻辑模型不能补造旧失败的partial-answer摘要，也不证明任意请求串存在通用完成界。

## 3. 新公开尾部补充：两目标pilot已通过，30次正式运行中

新增文件：

- `src/run_ir_guarded_periodic.py`：相同密码后端和controller，不改旧来源；每阶段固定额外一个period，不因提前完成缩短；全程核对返回值并保存原截点和最终答案摘要、完整账单及尾部费用。
- `src/audit_ir_guarded_periodic.py`：独立答案/截点摘要、总帧/分项/序号/尾部差额、逐层对象空间、reset守恒及逻辑schedule核对。
- `src/check_ir_guarded_periodic.py`：N64/B64，β2/14×Path/Deferred/SDE，共6真实运行；β2测量均8个reset槽。七种错误拒绝（漏guard、假完成、错partial digest、错分母、隐藏reset、改schedule、覆盖旧结果）。审计首次内存对象tuple/list差异已改为读取序列化收据，不重跑成功执行，不涉及协议修订。
- `src/prepare_ir_guarded.py`、`src/dispatch_ir_guarded.py`：真实目标前固定完整新矩阵，来源锁、1.5GiB空闲内存门控、串行隐藏进程、遇异常停止并保留记录；不隐式重试已有日志。
- `formal_ir_guarded_plan.json` hash：`e11d4a653562f7bc1d616a3efa8b2f68e184e67a1acc7ec7dda831e3915b802a`。原75个计划/来源不变；新设计明确是看过原结果及逻辑诊断后的补充，不声称盲预注册。

固定参数：N4096/B64/X32、PLB8/LLC8×2、cache6/R480、Hot90、DWB-on，β14/4 × 三后端 × seeds101–105，共30。到达gap8不变，Qwarm1536/Qmeasure6144；period12288，两阶段各附加1P：warm24576（原来的2倍），measure61440（原来多25%）。所有方案完整支付尾部，无按结果追加/提前结束。整周期是保守相位对齐设计，不是最小padding或最坏情况保证；不能把新旧窗口差异归为selective。

- 原值W与新值W+P、尾部bytes/RPC、完整请求、reset/dummy、原截点完成数分别保留。新失败有每个已验证返回值的前缀摘要。
- 七组比较：每β内Path/Deferred→SDE（4），每后端β14→4（3）。完整5对才报均值/Student-t；CV>10%或区间半宽>5pp时整个相关组补至10，不能选成功子集。
- seed901/1901的SDE β14和β4目标pilot均已通过audit，`results/ir_guarded_target_checks.json` 为passed。pilot独立，不进入正式均值。无需再跑。
- 父 **55976** 正在运行，最后CIM子 **10440**：`IRGUARD_beta14_path_seed101`。正式才开始，最后 `src/analyze_ir_guarded.py` 审计0/30、0失败、目标pilot2/2；未宣称新正式收益。
- `src/analyze_ir_guarded.py` 是新增动态分析入口，生成 `results/ir_guarded_statistics.json` 和 **61号 `61_IR公开尾部补充实验进度.md`**。保持六格/七比较位置，缺完整组不报性能。之后需要在新结果到达时运行，完成后做独立冻结表/图和追加重复判断。
- **60号 `60_IR重置压力诊断与补充实验.md`** 是准备与诊断报告；`results/ir_guarded_preparation_evidence.json` 刻意保留target_experiment_complete=false，不能当全部30次完成标志。报告已请求在Codex中打开（queued）。

新guard运行依赖的runner/controller/model replay/auditor/helpers/门控/plan/原证据均已锁定，队列运行期间不要修改；新增分析和图表工具可以写独立文件。任何允许的修订须另立版本/计划并保留旧尝试。

## 4. 章节、索引与完整性

- `src/build_evaluation_draft.py` 现逐份校验195个AB/IR来源，以及快照/表/图/实际渲染/报告hash；接入56–60号及新guard准备证据。
- `18_实验章节草稿_持续更新.md` 已成功生成；`results/evaluation_draft_sources.json` 记录AB60、原IR75/63pass/12incomplete、raw60，full_chapter_complete=false。
- README加入56–61及本续跑入口。带宽口径说明更新为完整ABDF/IR数据，保持Free/ρ范围，不再称旧批次运行中。
- 本轮只复用已有SVG/PNG，**没有新PDF、没有PDF marker**，不要重复生成或再次交付以前PDF。
- 最新只读 `src/verify_frozen_inputs.py`：7包514文件不变。不要使用会改旧MANIFEST的验证器。

## 5. B4与剩余完整目标

- 最后完整统计快照：calibration40/40、public80/80、sensitivity220/220、tuned50/50、**B4 slices100/150**（含25个旧B1别名）。随后真实队列已继续，不能把进程state的数直接当独立audit数量。
- B4父 **19648** 一直真实活跃，最后CIM子 **5700**：`B4_sde_N16384_B1024_seed101`。继续原队列，不重启。其memory_threshold按预计对象空间门控；不要因旧session句柄失效判断已终止。
- ABDF、原compressedIR、Free/ρ敏感性、C1、B3都已结束，不要重启。
- 后续优先完成B4余下规模/块长和新guard30的真实证据、配对表及矢量图，然后整合最终章节/复现包。
- IR-Stash当前skip反例仍须修复及压缩reset联动；不能以no-skip冒充原生IR已实现。
- AB认证DeadQ仍未接入CB。关键接口：动态n/τ与加密descriptor/header；count/used及cover选择；scheduled跨桶放置而非独立原桶保留；UID128/leaf/address格式；同一事务中的root、γ、remap/nonce及finalACK；全体比较同物理预算并计入认证路由成本。54号分配器不是这些义务的替代。
- green感知容量归约、完整转录边界、真实资源口径、全部要求逐项审计仍未齐，不据现有可用表图结束完整目标。原要求暂不需要实测加速比。

更早已完成数据、SOC3输入包、Free/ρ来源限制和AB分配器详细检查见第十七版及对应原始报告，继续保留全部source locks。
