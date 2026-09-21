# 执行衔接更新：第十一版

完整目标继续active，无需用户解除的阻塞。本轮与上一轮均为progress：上一轮完成IR60/Public80和两图；本轮新增4224次加密转录检查、Z4见证和225份运行的空间核对（220正式完成组＋5个入选配置空间见证）。不能据此缩小总目标或标complete。

## IR源对齐与Z4证据

重新读取原文§II-B、III-B、IV-C，并在线打开作者PDF：`https://mehrnoosh.net/research/IR-ORAM-HPCA%2722.pdf`。关注两点：随机初始化块顺序、Path写回排除当前目标。仍不声称完整原文状态机已复现。

新增文件及结果：

- `src/ir_initialization_alignment.py`、`results/ir_initialization_alignment_model.json`：Path L1/Z1的六个代表候选，秘密初始顺序、remote/all target hold、UID/随机平局、独立dummy/旧叶dummy/no_skip。全二地址请求串长度1至4，24行exact Fraction结果。
- `src/check_ir_initialization_alignment.py`、`results/ir_initialization_alignment_crosscheck.json`：2176次真实加密执行、每候选两个n2见证。known-order remote-hold TV5/16；secret-order remote-hold7/32；secret-order random-ties3/16；secret-order hold-local-too3/16；secret-order oldleaf3/8；full-remap控制0。
- `src/check_ir_z4_skip_projection.py`、`results/ir_z4_skip_projection.json`：新增独立Path模型，L=2表示叶深度2/总三层，N2/Z4/A3/R16/cache1。两个真实块，无容量争用。秘密均匀初始化顺序，两初始化打开路径均0；初始化/远端请求的目标不立即回填。本地命中不remap，公开槽由独立均匀dummy填充。
- Z4模型全部二地址请求串n1..4，skip最大TV为0、3/16、17/64、43/128；no_skip全0（有限投影控制，非证明）。实际加密仅核对skip开/关×请求00/01，4格各512次，共2048次。session34388已terminal exit0，不要重启。
- Z4每个时隙仅枚举一个新四值叶，用作当前分支的dummy或fresh remap；未用坐标积分掉。此等价只用于路径随机性枚举，不把非路径完整transcript全部判为相等。
- Z4区域投影：0=叶{0,1}、1=叶{2,3}。请求00的区域00/01/10/11概率为3/8、1/4、1/16、5/16；请求01为15/32、5/32、5/32、7/32。第一条区域分布二者相同(5/8,3/8)，第二条落入区域1的概率分别9/16和3/8，相差3/16。该简单事件已证明当前适配的两请求差异。
- `src/summarize_ir_source_alignment.py`和43号文档，从原始PMF独立复核概率、TV、区域事件，并绑定模型/运行器/原PDF hash。`results/ir_source_alignment_evidence_audit.json`状态evidence_consistent，4224次新执行，**security_admission=false**。

这说明问题不依赖Z1容量争用，也不能只靠隐藏装载顺序或保留当前目标闭合。但仍是本项目明确适配的条件小域反例，**不是原生IR论文攻击、完整LLC/递归/时序复现或N4096泄漏量估计**。不可把full-remap控制重新命名为本地skip修复，不可启动新skip性能队列。仍需条件混合分布不变量与fresh remap/父map/canonical owner/时钟的联合协议设计。

所有候选通过独立进程中的实例monkeypatch，未修改现有IR-Stash模块、正式worker或旧proof JSON。39/40号原反例证据仍保持。

## 物理对象空间对照

- 新 `src/audit_storage_components.py`，结果 `results/storage_components_audit.json`；44号文档为可读表。
- 对已审计B1＋静态IR/AB的140收据和Public80收据，独立按树深度重算header、ciphertext slots、局部认证树节点、bucket/global tags；与真实存储对象分项、物理桶数和缓存前缀账单逐项相等。220行、30格。
- 再独立验证72个预声明候选。每个入选配置取已完成的B3 uniform seed101作空间见证，共5份；不是把这些当作B3性能完成。
- Ring局部认证节点数使用独立公式 `sum_j ceil(n/2^j)`，j=0..ceil(log2 n)；R0根仍保留两种64B标签，不能漏掉或将cached root当作远端删除。缓存按cut真实分到客户端和远端。
- 调优入选Ring7/6/9实际对象1067.267372MiB；R0 7/6/6为870.210464MiB，少18.463687%。共同服务器上限不意味着实际对象相同。核心stash预留payload＋terminal均1.063477MiB；**不是可信峰值内存**。
- 客户端各项分别记账，未包含全部record metadata/容器/分配器、并存密文/解码payload/最终write帧/认证scratch。集成IR/AB和剩余规模/敏感性的空间表仍待补。不要把这个表改标为256MiB可信峰值已通过。
- 新 `src/check_storage_audit_rejections.py` 拒绝8类坏账单（包括总额不变的错分项、缓存层数、完整PosMap漏记等）；`results/storage_audit_rejections.json`passed。两工具已针对最终源码运行。

## 文档与校验

README、章节生成器/18号稿加入43/44结论与源绑定。`build_evaluation_draft.py`最终运行通过，full_chapter_complete仍false。冻结核验7包514文件passed。

本轮没有创建/修改PDF，也没有重新交付旧图。第十版的 `completed_ir_periodic.pdf` 和 `completed_public_workloads.pdf` 已在上一轮最终回复各交付一次；禁止无必要重导或再次标记artifact operation。其余已交付图同理。

## 最后已审计快照及实际存活

实际Get-Process确认父15408、19648、47116、50656、54408仍存活。此前本轮两次CIM查询还确认各父的实际子worker及运行spec；没有因观察超时重启任何任务。

- tuned B3：36/50。
- calibration40/40、public80/80、sensitivity92/220、slices25/150。
- ABDF：29/60，18组过程效应，无失败；队列指向bottomD0 R0 uniform seed103。
- compressed IR：18/75完整完成；队列指向Path DWBoff hot90 seed102。主β14与β4压力处理修订继续按原计划。
- B4父19648的 `extended_scale_queue_bulk_state.json` 为waiting_for_verified_process，依赖实际live的B3父47116及其completion。slices25是B1别名，不重跑。

这只是审计时快照，下一轮必须重新看实际进程和收据。原始raw IR60、有限前缀IR120、Public80、核心/static140、B2 45、Free/ρ240、calibration40已完成，不启动重复实验。

## 下一步及不可改动边界

1. 收集并严格审核B3/ABDF/压缩IR/敏感性/B4剩余结果，完整组再做最终图表。B3快于其他批次，结束后B4应由原依赖进程自然启动。
2. IR的条件转录修复仍优先于新增skip性能；源对齐只完成两项机制，不对小域反例作论文原系统攻击的外推。
3. AB green容量归约、原生后台与DeadQ尚待推进；当前CB周期结果仅覆盖优先dummy适配。
4. 经典Path/Ring执行归约、完整资源边界、最终逐项全目标审计仍未齐。
5. 所有活跃源码闭包锁沿第七至十版继续：common/core/缓存/异质/组合、IR raw/compressed及其proof、AB周期/策略及其proof都不得中途修改。新增独立研究/核验/报告文件可继续使用。冻结验证只能使用只读 `verify_frozen_inputs.py`，不能旧mutating验证器。
