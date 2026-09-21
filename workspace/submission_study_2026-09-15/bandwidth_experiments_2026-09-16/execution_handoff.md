# 执行衔接（不是完成声明）

**本文件是早期历史记录。当前应先读 `执行衔接更新_20260916.md`；下列旧派发进程多数已正常切换，不能据此重启。**

2026-09-16开始的用户目标仍为全部论文带宽实验，不仅是以下两个已启动批次。

## 已启动且应继续观察的进程

- `batch_core.py --batch formal_core_plan.json --workers 4`：工具 session **60795**。60次B1正式运行，N16384/B4096，2 trace×6 backend×5 repeat。
- `batch_composition.py --workers 2`：工具 session **97857**。240次扩大组合运行，N4096/B64，4 trace×3 frontend×4 backend×5 repeat。
- pilot批次 session99046 已终态成功，8/8。
- hetero检查 session13982、component pilots session38334、公开trace下载 session24651 已终态成功。

会话句柄是观察入口；每次恢复先实际poll确认，不能只从本文件推断仍在运行。逐run的PID与日志在results/processes；运行进度在results/live；完成收据在对应results子目录。未确认旧句柄终态或进程消失前，不要重复启动相同run。

## 当前运行期间不能修改的代码

common.py、meter.py、workloads.py、run_core.py、composition_runtime.py、run_composition.py，以及引用的所有冻结核心和旧组合源文件。每次run前后检查执行依赖hash；改变会使该run失败，不能混入同一批数据。分析/画图、新独立adapter、heterogeneous系列文件不在这两个批次的执行闭包内，可独立推进。

两个批次全量计划已经写入formal_core_plan.json和formal_composition_plan.json，trace文件已预生成，避免并发创建同一trace临时文件。batch_core最初通用的batch_plan/completion文件可能被不同批次覆盖；正式身份以两个具名plan和逐run收据为准，不能依赖通用文件判定所有批次完成。

## 本轮已取得的新证据

- 实际帧计量移植：10组完整transcript/状态/随机消耗差分、6组fail-stop篡改拒绝。
- 静态逐层Z/S新序列化器：8组同质精确差分、9组异质运行，2304个完整状态中核对uid、payload、位置表、gamma、选择覆盖等，2组篡改拒绝。
- 异质成本模型退化到同质时24组、全部7分项与冻结向外舍入模型相交。
- Freecursive/ρ计量移植12组transcript/完成态精确差分。
- 8个基础4KiB预试验，最大N16384；8个IR/AB静态组件预试验N1024/B64。
- 当前B1配置SDE/R0通过冻结SOC3 gate；Path/Deferred/Ring/GC-Ring没有被自动贴同寿命保证。见results/core_admission.json。
- Financial1/WebSearch1已从UMass下载、记录hash；各五段6144命令窗口已预处理但未执行。为避免假定原始LBA字节单位，仅准备command-start-key重放，不能称完整块设备工作负载。
- 七个旧包514个被清单绑定的文件检查通过，没有改写冻结证据。

## 下一步仍必须推进

1. 观察上述正式批次，对实际失败定位修复且保留失败记录。用paired_statistics.py验证配对trace/schedule与n=5区间；不要靠pilot百分比做主结论。
2. B2两族compact/fusion四格、small map阶梯；B3双方调优、B4规模与块长代表切片、整周期模型校准。
3. IR/AB静态组件正式多种子/块长运行；真正顶部缓存序列化、IR-Stash/DWB与CB/DeadQ逐层机制仍未实现。异质容量准入未补。保持目标，不能把新静态fork称原生完整方案。
4. 更大组合的块长/缓存敏感性、两个公开trace、全递归和客户端/服务器存储口径。
5. 全部表、矢量图、章节文字、运行环境/版本/数据/统计复现说明和逐项完成审计。

更新进度表：运行src/summarize_progress.py；更新统计：src/paired_statistics.py。二者只读取已完成收据。没有最终manifest封包，也没有将goal标为complete。
