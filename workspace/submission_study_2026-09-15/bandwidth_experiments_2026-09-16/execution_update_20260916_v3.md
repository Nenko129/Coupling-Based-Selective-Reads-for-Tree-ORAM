# 当前续跑入口（第三版，全目标未完成）

本轮属于实质进展：完成IR集成结果审计、CB认证原型与检查、完整周期IR驱动及新批次；没有把全目标缩成静态组件。继续完成核心Path/Ring、四组合、消融/调优/规模/公开数据/敏感性、最终表图和独立复现。未发现必须由用户解决的阻塞。

## 正在执行和等待的进程

本轮均通过实际进程查询确认存在。下面进度只是快照，下一轮必须重新查进程/工具session，不能仅据此或状态文件判断存活。

| 任务 | session | 父PID | 本轮末观察 |
|---|---|---:|---|
| 核心/消融/静态缓存 | 42094 | 22128 | 75/180，3个worker；含合法复用 |
| B3双方有限调优 | 90409 | 47116 | 等22128结束，再做50次 |
| 校准/公开trace/敏感性 | 82050 | 15408 | 79/340 |
| B4规模bulk执行 | 93513 | 19648 | 等47116成功完成；125新运行+25引用 |
| IR-DWB有限前缀 | 76629 | 22552 | 65/120已审计，继续执行 |
| **新：IR完整周期复核** | **29903** | **6200** | 等22552成功完成，再做60次 |

状态文件分别为 `formal_resumed_queue_state.json`、`formal_tuned_queue_state.json`、`extended_small_queue_state.json`、`extended_scale_queue_bulk_state.json`、`ir_dwb_queue_state.json`、`ir_periodic_queue_state.json`。新周期完成文件为 `ir_periodic_queue_completion.json`。

曾观察到可用内存低于1.5GiB，IR派发器合法等待后已继续运行。不要因等待或工具观察超时重启。Freecursive160次、ρ80次基础实验已完成，不要重复启动。原scale父25248/session55798已被19648替代，不要恢复旧派发器。

## 锁定的执行源

保留第二版锁定的所有运行文件。新增锁定：`dwb_staged_frontend.py`、`ir_transfer.py`、`ir_dwb_runtime.py`、`ir_dwb_controller.py`、`run_ir_dwb.py`、`run_ir_periodic.py`。COMPOSITION与SOC3冻结文件均只读。本轮已重新核查7包514文件全部未变。

不要在活跃批次期间运行生成器覆盖上述文件。`prepare_ir_periodic.py`为一次性建档器，已经运行；60次计划已经绑定源身份。`dispatch_ir_periodic.py`已经启动，勿重复启动。

新增CB文件没有正式性能批次占用，可以继续开发，但任何执行代码变化后必须更新其差分/来源并重做受影响检查，不能用本轮旧hash收据覆盖新代码。

## 已完成的新工作

### IR-DWB集成与审计

`StepwiseFront`每时隙重新遍历当前map，并只完成一个Transfer。这样前台驱逐PLB里的map后，后台不会继续使用旧对象引用。Controller有inclusive set-LRU LLC、公共固定时隙、前台优先、set轮询DWB、版本/LRU失效取消、最终ACK后clean与fail-stop。

`ir_dwb_controller_checks.json`：24个功能组合、4主动失败、stale map专门测试通过；这一收据在正式120次运行之前生成，**不要重跑并覆盖**，现有运行绑定其文件hash。

`analyze_ir_dwb.py`：核对具名spec、源码/控制器证据、冻结前端来源链、输入hash、独立重算答案摘要、字节分项、RPC连续性、时钟、LLC工作量守恒、配置/内存预算、条件容量包。20种坏证据拒绝检查见 `ir_dwb_analysis_checks.json`。后端和布局配对核对相同remove/admit摘要和前端指标；DWB开关只固定公共W与应用Q，允许调度不同。

**重要结果边界**：64B集成配置中，SDE对Deferred初步约19%–21%，对Path约10%–14%；因为认证/桶头开销，Deferred总成本可以高于Path。n<5仍是过程结果。不能再泛化“除ρ外都在20%以上”。同固定W/Q时DWB对Path/Deferred的总字节节省严格为0，SDE保留路径差异造成的正负波动。

`19_IR集成DWB通信结果.md`生成120次有限前缀表；`22_IR集成协议与周期复核方案.md`解释契约、比较分母、账单分解及范围。

### IR完整周期复核

`formal_ir_periodic_plan.json`预定义60次：depth布局×DWB开关×Path/Deferred/SDE×uniform/hot90×5种子。N4096/B64/X16/PLB8/LLC8×2/缓存6层/R480保持不变。

人口4369，period=12288。初始化后单独计费7919个dummy对齐时隙，再暖机1536请求/12288时隙，测量6144请求/49152时隙。Path只用参考窗口，不能称其有bit-reversal周期；有限周期不自动等于稳态。

`run_ir_periodic.py`由旧驱动独立生成，diff见`ir_periodic_driver.diff`。`ir_periodic_runner_checks.json`包含六个小域跨后端/DWB执行及三个损坏证据拒绝检查，全部通过。pilot不进入正式统计。分析命令增加`--periodic`，输出21号文档和`ir_periodic_statistics.json`。

### AB Compact Bucket

阅读String原文PDF第6–8页及AB原文。新`cb_oram.py/cb_fusion.py/cb_transfer.py`是实际密文/认证原型：C真实容量、D物理dummy、Y overlap、τ=D+Y；密文头内保存G。目标优先，非目标在G<Y时从所有未读槽选择，G满时只选dummy。green保留原UID/leaf，最终ACK后进入stash。

关键修正：维护cover长度必须是min(C,n−count)。CB末期未读槽数可能小于C；零cover先验证头部、无需空READ_SLOTS，仍执行最终认证写回。不能把D0写成旧SOC3的S0。

`cb_engine_checks.json`通过24组（3后端×4布局/CB设置×2缓存）、3主动失败、2658个局部有理数分布检查（80组零cover）。每组160次读写+80固定路径dummy是功能压力，**不是正式性能样本**。

生成器`build_cb_engine.py`和`cb_engine.diff`记录18项改动；Transfer函数仅换引擎导入。`20_AB_CB实现与证明接口.md`有局部cover/选择证明及未解决事项。**完整adaptive模拟和green容量界未完成；后台阈值维护、DeadQ、递归前端集成也未完成。** 不能将旧AB静态Y0的24%–26%推广到CB/完整AB。

## 本轮统计及论文工件

更新03正式配对、13消融、15扩展统计；最近B2 26/45，校准25/40、公开24/80、敏感性24/220、规模10/150、调优0/50。后续会随运行增长，不能只引用这些快照。

18号实验章节草稿已加入IR/CB新进展与范围，README指向本版。已完成基础前端XLSX及两张PDF/SVG/PNG图仍有效，输出位置和验证方式见第二版。没有把不完整组写入完成的XLSX。

## 安全刷新和下一步

使用bundled Python `-B -X utf8`。分析文件可变，运行闭包不可变。必要时依次运行：

1. `paired_statistics.py`、`analyze_ablation.py`、`analyze_extended_results.py`。
2. `analyze_ir_dwb.py`与`analyze_ir_dwb.py --periodic`；分析器变动后运行`check_ir_dwb_analysis.py`。
3. 统计刷新后再运行`build_evaluation_draft.py`，避免章节来源hash落后。

下一轮优先继续：

- 检查全部批次的真实进程状态、收据与必要n10追加门槛；完成后的组再制成最终表图。
- AB-CB接入递归前端，并解决阈值后台维护的可计费执行与新的容量归约；继续DeadQ的时序所有权、donor refresh和认证账单。
- IR-Stash随机位置相关命中/冲突与压缩map跨时隙reset仍为完整组合缺口，不得删除。
- 公开负载/敏感性、核心/消融/双方调优/规模主图、所有配置的基线与新构造安全准入、最终独立复现审计尚未齐。

本轮检查sessions26211、78766、14304均已成功终止。新长期session29903保持运行。不要因预算或阶段结果漂亮而标记全目标完成。
