# 当前续跑入口（2026-09-16；目标未完成）

> 此文件为旧状态。请先读 `执行衔接更新_20260916_第二版.md`；Freecursive/ρ基础批次已完成，扩展队列和DWB接口已有新进展。以下保留为历史记录。

完整目标仍为论文全部带宽证据：核心、消融、双方调优、规模/块长、四类组合、公开trace、图表与章节。不能把已经完成的窄组件改名为完整原生框架，也不能因剩余工作耗时而宣布完成。

## 进程状态入口

每次恢复必须先实际查进程或poll句柄，不从本文/状态JSON单独推断存活。下列为本次最后确认值，之后可能自然完成。

| 任务 | 工具session | 父PID | 当前说明 |
|---|---|---:|---|
| 核心+消融+修订缓存队列 | 42094 | 22128 | 已等旧子进程自然结束，开始真实run_fast子运行；180个具名输入，包含合法复用 |
| 双方调优队列 | 90409 | 47116 | 等待22128结束，之后执行50个B3输入；三个worker |
| Freecursive原始/压缩扩大实验 | 86447 | 34580 | 原身份，160个输入、两个worker；已推进到seed105 |
| 修复后的ρ扩大实验 | 38468 | 55820 | 新C2身份，80个输入、一个worker；已推进到seed104 |

旧核心parent51616、消融34384、缓存31080均已停止未来派发，未杀正在执行的子运行。记录在 `results/legacy_dispatch_drain.json` 及 `results/cached_v1_dispatch_stop.json`。旧核心session60795/消融48997/缓存28255不再是控制入口。新队列已核对完成收据并复用，不要重复启动同一spec。

数值session58208（IR480）、88280（native形状A2）、78601（A1）已成功结束；不是后台任务。

## 运行期间锁定的执行闭包

不要修改 common.py、meter.py、workloads.py、run_core.py、composition_runtime.py、run_composition.py、transfer_backend_fixed.py、run_rho_fixed.py、heterogeneous_oram.py、heterogeneous_fusion.py、cached_transport.py、cached_cost.py、run_cached_component.py、fast_prf.py、run_fast.py 及所有冻结源文件。运行前后核对哈希，改动会使结果失效。独立分析/绘图工具可继续编辑。

所有子运行输入、PID及日志在specs/results/processes/results/logs；完成收据在各formal目录。状态JSON仅作定位入口。通用batch_completion历史文件不能代表全部实验完成。

## 本次新增的实质结果

1. IR43缩放L12、A3，R256不能通过容量预算。C480/M128双方式网格最小数值准入R452，采用R480，上界约2^-146.3867（总时隙2^56，预算2^-132）。两侧四格统一改为R480；40个新IR结果放formal_cached_admitted，旧R256保留诊断。AB40输入不变，继续formal_cached_components。新计划formal_cached_admitted_plan.json，原计划不覆盖。
2. 原生形状的负载压力检查：A2和A1、叶λ35/8、其余λ=A/2，C280都未通过。该叶负载是包含一种X16递归人口的保守模型点，不是作者完整系统复现。新小域精确核对220个joint状态通过；不能把数值上界失败等同真实溢出。
3. HMAC前缀复用和C级异或逐字节等价：18完整配置、4缓存、6主动拒绝、两套原语边界，以及两组进程入口检查通过。原密码格式/计数不变。这里只提高运行器效率，不产生ORAM延迟结论。
4. 72个有限候选的周期成本选择已执行；当前N16384/B4096的Ring选Z7/A6/S9，R0选Z7/A6/S6，mapB256，预测节省24.58%。50个正式B3输入已进入独立等待队列，不能把预测当实测。
5. 两张图已导出PDF/SVG/PNG并查看布局。有限调优图明确MODEL ONLY；组合图仍PRELIMINARY，n<5不绘CI。数据及哈希位于figures。图表生成器使用本目录.plot-deps中的matplotlib，未改全局Python。
6. 七个冻结包514个清单绑定文件再次通过一致性检查。

## 更新统计和图

使用bundled Python，并加 `-B -X utf8`。`src/paired_statistics.py` 现在排除旧ρ及旧IR R256，并加入已完整写出的AB和新IR缓存结果。它支持同参数配对，**尚未加入B2的四格效应或B3不同参数最优点配对**，不能误以为已统计了所有计划。

首个完整n5结果已出现：free_raw/uniform/N4096/B64，Deferred→SDE为21.85264%（95%区间21.81029–21.89499），Ring→R0为24.47003%（24.42953–24.51054），均未触发追加重复门槛。新的IR R480四格首种子已完成，depth组节省19.35985%，仍只有n1。继续以逐run收据和重新生成的统计为准。

执行 `src/render_evidence_figures.py` 更新图；输入是paired_statistics和fair_tuning_candidates。若未来加入更多N/B，先扩展图选择器，不把不同规模混为一根柱。执行 `src/verify_frozen_inputs.py` 只读核查冻结包，旧包自己的validator可能改写工件，不要运行。

## 必须继续的工作

- 让正式批次完成，对真实失败保留证据并定位；完成n5配对CI与预设追加到n10门槛。不能用初始n1/n3数据作最终headline。
- 补B2实际四格/小map/参数族归因；B3调优实测和同空间展示；基线自己的容量/寿命/主动安全绑定仍未齐全。
- B4规模/块长代表切片和完整服务周期校准尚未正式准备/执行。不能把模型曲线标成实测。
- 两个公开SPC trace已下载并预处理5×6144窗口，但尚无执行适配器/完成结果；语义只是command-start-key局部性回放，不假定LBA单位或称完整块设备重放。
- Freecursive还需PLB/β/更大块长与重映射敏感性；ρ还需前后端/缓存分账、参数敏感性和完整位置表/长度泄漏边界。
- IR-Stash/DWB、AB CB/DeadQ尚未完成原生集成。保持研究任务，继续补机制或实质不可组合证据，不把静态配置结果等同原生完整系统。
- 最终原始表格、矢量图、章节草稿、统计复现及全目标完成审计仍未完成。goal必须保持active。
