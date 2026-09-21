# 当前续跑入口（第二版，目标未完成）

此版替代早期衔接说明和第一版。完整目标仍为论文全部带宽证据；核心、四组合、原生机制边界、实验矩阵与独立复现都保留。上一个询问回复后实际刷新了配对统计，本轮又完成工件、分析程序和新DWB接口，均属于实质进展，不是仅等待。

## 存活进程

最后实际查询确认下列四个父进程存在。恢复时仍须再次查询进程/工具session，不能仅用本文或状态文件判定存活。

| 任务 | session | 父PID | 最后观察 |
|---|---|---:|---|
| 核心/消融/缓存队列 | 42094 | 22128 | 51/180队列项，仍有真实子运行；计数含合法复用 |
| B3调优队列 | 90409 | 47116 | 等22128成功结束，然后50个新输入 |
| 小型扩展 | 82050 | 15408 | 43/340；校准、公开trace、前端敏感性交错执行 |
| B4规模批量执行器 | 93513 | 19648 | 等47116且核对成功收据，然后125个新输入 |

Freecursive基础160次、修复后的ρ基础80次已全部完成并独立核账，不要重启。原scale父25248/session55798在尚未派生子运行时已停止，已经被19648替代。不要恢复旧scale派发器。

新进度文件是 `results/extended_scale_queue_bulk_state.json`，不是旧无bulk后缀文件。具体PID、spec、日志见results/processes和results/logs。观察超时不是终止，不应因超时重复启动同一输入。

## 执行源文件锁定

运行期间不要改common、meter、workloads、run_core、composition_runtime、run_composition、transfer_backend_fixed、run_rho_fixed、heterogeneous_oram/fusion、cached_transport/cost、run_cached_component、fast_prf、run_fast、public_trace、run_extended、run_extended_composition、bulk_prf、run_bulk_scale，以及冻结目录内文件。分析和绘图文件可以独立改动。

本轮重新只读核查7个冻结包514个文件，全部未变。新DWB文件独立于正式运行闭包，可以继续开发，但变动后必须重做其受影响检查，不能拿旧hash收据代表新代码。

## 本轮交付与检查

1. `outputs/01a09f23-0c2e-75e3-9ce5-d8ef0a277d5e/Freecursive_rho_基础实验.xlsx`：240行原始运行、120行逐种子配对、24组均值与CI。由artifact-tool生成，改变输入后重算并恢复，全部均值/CI对照独立Python结果。另用openpyxl只读核对已导出的240行来源与24组缓存数值；没有运行原生Excel。表格已视觉检查，来源与原始行包含在同一个可排序表中。
2. `figures/composition_paired_progress.*` 已更新为完整n5；新 `frontend_bandwidth_breakdown.*` 分开data slots、data nonce、headers、authentication、framing。PDF/SVG/PNG都导出，PNG已查看。小块下R0相对Ring节省更大，但绝对总字节仍高于SDE。
3. `src/analyze_extended_results.py` 核查calibration/public/sensitivity/slices/tuned的具名输入、执行身份、trace、答案、计费与配对。支持B4的B1别名与bulk身份。公开窗口明确无iid CI。新增7类错误证据拒绝检查，并检查tuned spec没有study字段的分支，收据extended_analysis_checks.json。
4. 完整周期校准已经覆盖8类首批配置；Path/Deferred账单与模型精确一致。其他模型误差在15号文档中保留，n<5不作为最终结果。Path窗口不是bit-reversal维护周期。
5. `src/dwb_staged_frontend.py` 新增raw-map的DWB分阶段接口。36个取消/版本/前台接管用例、5类主动失败、6类串行逐字节对照和6类同endpoint dummy/data大小检查通过。证据 `results/dwb_stage_checks.json`。最后运行的测试sessions83919/72612均已完成。
6. 文档12列扩展计划，16解释DWB不变量/带宽口径，17解释bulk HMAC等价，18是含完整前端表的实验章节草稿，其余未完成范围保留。

## 新DWB接口的下一步

已实现取消时不回退已提交map访问、在child完成所有权迁移后才暂停、inclusive replace、最终ACK后才标clean、dirty版本变化重启和fail-stop。无中断时与原raw Freecursive Transfer逐字节相同。

尚未实现：公共时隙/应用到达调度器、原生round-robin set-LRU候选集成、压缩counter的跨时隙group reset、IR异质树缓存和IR-Stash集成。固定W和同公开路径形状时dummy→DWB不删除通信时隙；不能以dummy比例下降或原文speedup来填写带宽节省。应进一步确定测量终点并计入所有dummy/回写/取消成本。

## 统计刷新

bundled Python必须加 `-B -X utf8`，不写冻结pycache。`paired_statistics.py`负责核心/完成前端/新IRR480/AB；`analyze_ablation.py`负责B2；`analyze_extended_results.py`负责B3/B4/周期/公开/敏感性。这些是不同分析，不能只跑其中一个就声称全部统计完成。

最后B2观察数18/45，核心/IR/AB重复尚未收齐。新IR仍必须用R480，旧R256结果不进主表。全部主比较n5后执行预设n10门槛。公开相邻窗口不套这个iid门槛，应单独保持预定窗口设计。

Excel构建脚本是 `src/build_frontend_workbook.mjs`，node_modules为bundled依赖junction。已经运行过一次create标记，不要为同一创建任务重复标记。表格只含已完成基础前端，后续全证据表需更新设计和来源，不混入半完成组。当前图表使用本目录.plot-deps，不修改bundled依赖目录。

## 尚未满足全目标

- 运行并审阅全部正式批次，必要时按门槛完整增加重复；保留失败/低收益，不选择性删点。
- 核心、干净消融、双方调优和规模/块长正式主图与表；基线独立安全保证仍未齐。
- 公开trace和前端敏感性，包含β/group reset、LLC/ρ/帧比例变化和与基础对照的条件差。
- IR-Stash、DWB全链和AB CB/DeadQ的新状态过程、实现与公平比较。不能把静态组件重命名为完整原生系统。
- 最终章节、全部原始表格/矢量图、独立重现命令和逐项完成审计。

目标必须继续保持active；本轮不存在需要用户才能继续的阻塞。
