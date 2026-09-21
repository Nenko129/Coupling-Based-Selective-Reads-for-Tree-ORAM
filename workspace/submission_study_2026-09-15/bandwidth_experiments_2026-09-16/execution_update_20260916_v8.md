# 执行衔接更新：第八版

目标仍 active，未缩小实验/论文交付范围。本轮为实质进展，不存在用户输入阻塞。用户当前追问“除ρ外是否均能减少20%以上”，应简洁回答不能；以下数字已写入带宽收益口径核对文档。

## 本轮新增且通过的IR-Stash接口

- `ir_stash.py`、`ir_stash_runtime.py` 是独立后端，未改原 live closure。双索引/MD5公开组索引、满组跳过、F/S本地读写、树顶可信边界根、认证根更新、远端ACK后提交索引。
- `check_ir_stash_engine.py` 第一版随机轻装载没有本地命中，触发覆盖断言；改为明确标注的确定性叶碰撞功能夹具，保留全部不变量。最终6组后端、6远端篡改及本地篡改检查通过，收据 `results/ir_stash_engine_checks.json`。检查gamma不变/wv递增、uid/leaf/t/g不变、完整远端对象和账单不变、失败后索引/根/边界根未提交。
- 新 `ir_stash_frontend.py` 的 StashDataFront 仅接**数据块**本地命中：先探测F/S，miss时查询raw父map但不先remap数据，map Transfer后再次探测，真正远端数据访问才更新leaf。位置表块仍用旧exclusive PLB/Transfer，不是全递归map的原生IR-Stash，也没有压缩reset接入。
- 新 `ir_stash_controller.py` 的 LocalHitController 可完成零Transfer本地步骤，但每公共tick仍恰好一个Transfer，由后续前台、DWB或dummy填充。本地DWB成功才clean，有限队列保证本地循环终止。
- `check_ir_stash_frontend.py` 最终12组（dedicated/indexed × 3后端 × DWB开关），每组48请求/384公共时隙；独立解密oracle核对全部owner、rawmap叶指向、LLC数据与答案，3个控制器篡改失败，全部通过。初次末尾JSON输出包含bytes导致序列化失败，改为答案hash后重跑通过；没有把失败文件当passed。
- 前端check绑定后端check哈希；后端check绑定runtime/code/checker。新源可继续开发，但改变依赖需重新绑定相关测试，不能留下旧passed证据。无长跑导入新模块。
- `35_IR_Stash本地命中接口与证明边界.md` 写明完成态不变量、认证/nonce、固定时隙计费条件和未完成安全/容量归约。测试Z1和碰撞夹具不是性能数据。不能将局部空transcript推成全交互模拟，也不能把命中率直接当总通信减少。

## 核心及静态组件完成

- PID22128/core resumed 已退出；存在 `formal_resumed_queue_completion.json` passed，180/180（含已完成B2观测）。状态文件最后仍stage running属写法遗留，完成收据和实际进程退出优先。
- B3 PID47116已不再等待，实际子19136/7460/42908开始seed101 Path/Deferred/SDE；旧state可能仍显示draining，当前源码每一个run完成才刷新，不能误判没启动。B4 PID19648仍等待47116。
- `paired_statistics.py` 重跑：42组全部n5。
- 新 `audit_completed_core_components.py` 实际通过：60核心+40静态AB+40R480静态IR，140物理观测，28配置，18配对，追加门槛false。审计独立SHAKE答案、源码/加速收据、账单分项、RPC序号、窗口和、递归初始化累积时钟；Path g=t，其余g=floor(t/A)。
- admitted plan还含AB别名，不应把相同AB文件算两遍；当前auditor在旧plan只取AB，在admitted只取IR，140为去重真实运行数。
- 输出 `results/core_components_complete_audit.json` 和 `36_B1核心与静态组件完整结果.md`，未生成新的PDF，既有B2/校准PDF不重复导出。
- 固定Z4/A3/S3核心：SDE对Path35.80–35.89%，对Deferred24.13–24.24%；R0对Ring26.54–26.63%。这不是分别调优主结果。
- 静态IR异质4KiB对Deferred21.53%，64B19.24%；同质对应22.91%/20.25%。静态AB四格23.98–25.95%，均n5，但仍无CB/DeadQ。

## 最新已审计快照

- Free/ρ240和有限IR120未改。Free压缩SDE21.81–21.87%，R024.43–24.55%；ρ总体8.29–8.31/11.64–11.65%。有限异质IR相对Deferred19.10–19.25%、Path9.63–9.80%。
- `analyze_ir_dwb.py --periodic`：46/60，后端配对3–4种子。19.20–19.22%对Deferred，9.76–9.78%对Path。实际PID6200仍跑，末次子29244。
- `analyze_ab_dummy_first_periodic.py`：7/60，9效应，0失败。均匀D3单种子R0对Ring20.274%，底三层D0单种子21.989%；不要当n5结论。PID50656仍跑，末次子49896。
- `analyze_extended_results.py`：calibration40/40，public69/80，sensitivity68/220，slices25/150，tuned0/50。PID15408末次子15728 public WebSearch rho deferred seed104；tuned尚无完整收据但实际已启动。
- 新压缩观察队列PID54408仍等待rawIR6200，75格尚未测量。旧失败/修订按第七版保留，禁止重启旧gate/dispatcher。
- frozen只读validator再通过7包514文件。

## 更新的文字与后续

`带宽收益口径核对_20260916.md` 已更新静态AB五次、静态IR块大小差异和ABDF/IRPER快照。`build_evaluation_draft.py` 与18号草稿已更新核心/B2完成状态、IR-Stash数据接口及未闭合边界，并绑定新audits/checks。不把140完成或局部检查当全部论文完成。

后续仍需：所有正式队列完成及逐行审计、B1和最终tuned/scale等图表；全递归map本地接入/压缩reset及IR自适应安全容量；AB green/后台/DeadQ；经典基线执行归约；最终逐要求审计。当前新接口仅raw数据，不能混用到正在跑的raw/compressed批次。所有第七版live源码锁继续有效，虽core父退出，B3/B4/其他长跑仍依赖其通用源码。
