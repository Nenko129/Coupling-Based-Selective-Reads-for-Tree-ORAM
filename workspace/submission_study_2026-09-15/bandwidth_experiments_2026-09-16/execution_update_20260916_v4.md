# 当前续跑入口（第四版，完整目标保持未完成）

本轮是实质进展：完成IR图表和数据复算，AB递归/压力原型的18组审计及压力检查，扩大AB批次后发现并保留真实初始化溢出，并开始同N/树高/R的公开节拍加载修订验证。上一问答回合核对了完整批次证据，纠正了“除ρ均超过20%”的结论；本轮没有缩减全目标。没有用户依赖阻塞。

## 真实运行状态快照

以下父进程均由进程查询确认；状态文件只是进度，后续必须重新查询实际进程或工具session。

| 任务 | session | 父PID | 本轮末快照 |
|---|---|---:|---|
| 核心/B2/静态组件 | 42094 | 22128 | 103/180，实际worker仍运行 |
| B3有限双方调优 | 90409 | 47116 | 等22128，再50次 |
| 校准/公开trace/敏感性 | 82050 | 15408 | 校准40/40，公开43/80，敏感性42/220；内存不足时合法等待 |
| B4规模bulk | 93513 | 19648 | 等47116；15/150已审计（包括可引用B1） |
| IR周期复核 | 29903 | 6200 | 10/60已审计，本轮末等待可用内存 |
| **AB公开加载节拍检查** | **94948** | **41532** | uniform三后端已通过，bottomD0三组继续 |

IR有限前缀120次已完成，原session76629已结束。AB六组集成pilot session22982和十二组压力pilot session70164均已成功结束。**AB周期主批次session59000已失败终止，不是仍在执行或等待。** 不得恢复旧AB队列或删掉日志后重跑。

## 完成的IR图表

- `figures/ir_integrated_finite_gain.pdf/svg/png`：24格完整120次、两个分母、95% t区间。修复横轴标签重叠。
- `figures/ir_integrated_finite_breakdown.pdf/svg/png`：depth+DWB开启，Path/Deferred/SDE绝对KiB分解。
- `tables/IR_DWB_120_runs.csv`、`tables/IR_DWB_40_comparisons.csv`：全部原始行及40组条件效应。
- `verify_ir_finite_exports.py`从原始总字节重算40组均值/区间，检查120行来源hash、PDF单页/字体嵌入/矢量内容；已通过。
- `results/ir_finite_visual_review.json`绑定实际审阅过的最新PDF及Poppler渲染hash；两图可交付。`ir_integrated_finite_receipt.json`的生成阶段pending标志由这份独立审阅收据解决，不需要重新渲染覆盖。

非均匀桶：对Deferred 19.10%–19.25%，对Path 9.63%–9.80%。均匀桶对照分别20.20%–20.36%、13.75%–13.93%。这解释了不能概括“除ρ外均20%以上”。仍是有限前缀，完整周期60次另报。

## AB递归/压力实现与证据

`ab_cb_runtime.py`接真实cache、raw递归map，`ab_cb_controller.py`做high/low滞回，每公共时隙一次普通CB Transfer。后台可搬green，尚不是原生strict-dummy策略。`ab_geometry_frontend.py`显式暴露公共L，避免自动按1.5装载扩大树。

`ab_cb_frontend_checks.json`：12控制器、6串行压缩map、3高装载几何、2后台主动失败通过。**这不是压缩map跨时隙DWB，也不是自适应安全证明。** 新frontend/runtime/proof目前保持不变，旧pilot收据绑定它们。

原6格pilot N512/B64/L8、人口547、C5/A5/τ7/Y4、常规D3或底三层D0、R500、缓存3/PLB4/LLC8×2、H48/L32，warm64、Q128、16槽/请求。测量期均无后台压力，只有部分暖机触发。

新增12格pilot预先声明H24/L16与关闭压力，其他相同。全部完成。bottomD0/H24的Ring/GC-Ring/R0测量后台槽位分别776/1/16。均完成相同请求，有用remove/admit子序列及前端工作量相同；全padding时序不要求相同。该现象单种子、不报CI、不作为普遍结论。

`audit_ab_cb.py`校验输入/答案/来源、人口与几何、账单分项、时钟/工作守恒、stash边界分布和独立重建的实际服务器/缓存对象大小。**R0缓存12104字节，Ring/GC-Ring13972；差1868来自空根仍留两个tag，不能错误要求cache字节相等。** 缓存层数和其他预算一致，省出空间不复用。

`check_ab_cb_audit.py`21种坏证据拒绝通过。`report_ab_cb_pilots.py`输出24号文档、18行CSV和summary；所有单元和负差分均保留。

压力pilot第一次session83867在首行成功执行后，因为内存tuple与JSON list比较被审计器拦截；已改成始终读落盘JSON，再从已有首行继续，没有重跑或改算法。失败连接记录保留`ab_pressure_pilot_failure.json`，不要把它当成ORAM溢出。

## AB扩大批次：真实失败与修订

`ab_periodic_plan.json`在目标运行前预定义60次：N4096/B64/L11/pop4369/C5/A5/Y4/R500，uniform/D0×Ring/GC-Ring/R0×uniform/hot90×5，缓存6/PLB8/LLC8×2/H48/L32。对齐5871槽，warm640请求/10240槽，Q2560/40960槽。

`run_ab_periodic.py`通过独立小域6组+4个坏对齐证据检查。新批次开始后，**首组`ABPER_uniform_ring_uniform_seed101`在GeometryFront连续初始化admit阶段发生R500 boundary stash溢出**。Controller在整个构造器返回后才创建，所以H48不能保护初始化。还没进入对齐、暖机或测量。日志、失败JSON、旧计划及原驱动均保留。`analyze_ab_periodic.py`目前输出0/60、1失败、stopped_after_failure，25号文档已说明。小域通过不覆盖目标初始化峰值。

不能为了过测试降低装载、增大R后覆盖旧行或继续只跑Selective组。当前修订是**所有后端相同的公开加载节拍**：一个admit后跟A−1个普通CB dummy，初始化传输全部记在setup。它不改N、R、L、C/A/Y/D；不是私有stash依赖的无限冲刷，也不是容量证明。

新独立生成器`build_ab_paced_frontend.py`与`ab_paced_frontend.py`及diff已经生成，旧Geometry源未改。`check_ab_paced_initialization.py`正在执行6组N4096几何检查：每组初始化21845槽，然后逐项读取核对全部4096原始数据。uniform的Ring、GC-Ring、R0三组已通过，整体边界stash峰分别431、179、181，均≤500。bottomD0三组尚在执行，不能据此说全部通过。中间结果`ab_paced_initialization_progress.json`，完成结果`ab_paced_initialization_checks.json`。

**当前尚没有paced版周期驱动/正式修订计划。** 下一轮首先等待上述真实进程。全部通过后，独立生成新的周期驱动和新ID/计划，保留原失败。新初始时钟应为`population*A=21845`，而不是4369；对齐应是8875槽至30720，warm后40960，measure后81920。审计器的对齐与最终clock必须同步按新初始时钟核查，不能直接复用旧人口即初始时钟的假设。修订司机需单独小域/坏证据检查，然后才能启动。仍须保留green归约、原生后台策略和DeadQ缺口。

## 锁定文件与可修改范围

沿用第三版全部核心/IR正在运行源文件冻结，不改common/meter/workloads/任何执行闭包；7包514冻结文件本轮再次只读验证通过。

paced检查活跃期间，不改`check_ab_paced_initialization.py`、`ab_paced_frontend.py`，以及其`ab_cb_runtime.identity()`覆盖的CB、cache、递归、IRcontroller与frozen来源。新驱动、分析与文档可独立增加。不要再运行会覆盖源的生成器，直到确认该进程结束。

**不要重跑覆盖`ir_dwb_controller_checks.json`或`ab_cb_frontend_checks.json`。** 执行收据绑定其hash。审计器拒绝测试可重跑，但运行算法检查收据不能随意重建。

## 后续推进顺序

1. 核验paced初始化剩余3组并实现计费/时钟正确的新修订周期驱动；旧失败长期保留。
2. 继续IR周期、核心/B2/B3/B4及公开/敏感性正式批次。校准40次已完整，下一轮可以整理完成校准图；不把尚未齐的组混进去。
3. IR-Stash随机位置相关命中、压缩map跨阶段reset；AB green容量归约、原生后台策略、DeadQ生命周期/认证/可用空间仍需要真正完成。
4. 最终全部具名实验、失败审阅/追加门槛、独立安全准入与基线保障、主表/向量图/章节和独立复现逐项审计。

README和18/20/22/23/24/25号文档已更新。用户未要求网络实测加速比。目标保持active，不能以已有漂亮组件结果代替完整要求。
