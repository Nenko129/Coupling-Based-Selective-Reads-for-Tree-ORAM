# 公开访问记录：80次完整运行与组合带宽结果

Financial1和WebSearch1各选定5个相邻窗口，分别运行Freecursive压缩前端、ρ两树前端的Deferred/SDE/Ring/R0，全部80/80完成。每窗2048条暖机命令、4096条测量命令，N16384/B64；同族profile为Z4/A3/S4，PLB8、LLC32、ρ容量128、R256。不是双方独立调优结果。

源数据来自UMass Trace Repository的Storage Performance Council访问记录；原始压缩文件、下载URL和SHA256在 `datasets/download_receipt.json`。独立重新解析61440条源命令，核对ASU/LBA键映射、操作、时间边界和命令长度元数据；另从版本历史独立重算全部返回值摘要。
适配器将每个命令起始键映射为一个64B记录，保留重复键和读写顺序。未按原始I/O长度拆块、未回放到达时间，不能称完整块设备重放。五个相邻窗口并非工作负载总体的独立抽样；主表报告配对节省的均值和窗口最小—最大值，不给总体置信区间。

## 8组完整配对结果

| 前端 | 公开记录 | 比较 | 基线bytes/op | selective bytes/op | 平均节省 | 五窗口范围 |
|---|---|---|---:|---:|---:|---|
| free_compressed | Financial1 | deferred → sde | 54677.109 | 42617.228 | 22.057% | [22.009%, 22.124%] |
| free_compressed | Financial1 | ring → r0 | 81083.116 | 61560.798 | 24.077% | [24.062%, 24.096%] |
| free_compressed | WebSearch1 | deferred → sde | 56468.297 | 44019.923 | 22.045% | [22.021%, 22.077%] |
| free_compressed | WebSearch1 | ring → r0 | 83750.601 | 63615.068 | 24.042% | [23.974%, 24.116%] |
| rho | Financial1 | deferred → sde | 28094.292 | 25538.650 | 9.096% | [9.077%, 9.105%] |
| rho | Financial1 | ring → r0 | 33663.712 | 29538.338 | 12.254% | [12.204%, 12.284%] |
| rho | WebSearch1 | deferred → sde | 48764.400 | 44323.173 | 9.108% | [9.082%, 9.120%] |
| rho | WebSearch1 | ring → r0 | 58434.548 | 51269.186 | 12.262% | [12.223%, 12.325%] |

Freecursive组合SDE约22.04%–22.06%、R0约24.04%–24.08%；ρ组合SDE约9.10%–9.11%、R0约12.25%–12.26%。这些是当前两组公开窗口的总通信结果，不能外推为全部实际应用的平均收益。

## ρ分账

各窗口均校验前树转录及字节完全相同，并用有理数验证：整体节省 = 原后端流量占比 × 后端自身节省。以下分别对窗口取均值；不能用均值的乘积替代逐窗口乘积的均值。

| 公开记录 | 比较 | 前树bytes/op均值 | 原后端占比均值 | 后端自身节省均值 | 整体节省均值 |
|---|---|---:|---:|---:|---:|
| Financial1 | deferred → sde | 16480.331 | 41.339% | 22.004% | 9.096% |
| Financial1 | ring → r0 | 16480.331 | 51.044% | 24.007% | 12.254% |
| WebSearch1 | deferred → sde | 28606.603 | 41.337% | 22.032% | 9.108% |
| WebSearch1 | ring → r0 | 28606.603 | 51.045% | 24.022% | 12.262% |

## 16格绝对通信与RPC

| 前端 | 记录 | 后端 | n | bytes/op均值 | 五窗口范围 | RPC/op均值 |
|---|---|---|---:|---:|---|---:|
| free_compressed | Financial1 | deferred | 5 | 54677.109 | [52569.023, 55264.336] | 7.232422 |
| free_compressed | Financial1 | sde | 5 | 42617.228 | [40938.441, 43083.311] | 7.232422 |
| free_compressed | Financial1 | ring | 5 | 81083.116 | [77917.352, 81965.711] | 10.848633 |
| free_compressed | Financial1 | r0 | 5 | 61560.798 | [59142.426, 62243.492] | 10.848633 |
| free_compressed | WebSearch1 | deferred | 5 | 56468.297 | [56301.328, 56773.828] | 7.469336 |
| free_compressed | WebSearch1 | sde | 5 | 44019.923 | [43892.098, 44271.814] | 7.469336 |
| free_compressed | WebSearch1 | ring | 5 | 83750.601 | [83438.344, 84235.734] | 11.204004 |
| free_compressed | WebSearch1 | r0 | 5 | 63615.068 | [63419.297, 64002.305] | 11.204004 |
| rho | Financial1 | deferred | 5 | 28094.292 | [26574.750, 31029.211] | 4.992676 |
| rho | Financial1 | sde | 5 | 25538.650 | [24162.539, 28204.123] | 4.992676 |
| rho | Financial1 | ring | 5 | 33663.712 | [31854.750, 37178.809] | 5.760791 |
| rho | Financial1 | r0 | 5 | 29538.338 | [27954.336, 32616.820] | 5.760791 |
| rho | WebSearch1 | deferred | 5 | 48764.400 | [48756.094, 48766.477] | 8.666113 |
| rho | WebSearch1 | sde | 5 | 44323.173 | [44315.756, 44337.336] | 8.666113 |
| rho | WebSearch1 | ring | 5 | 58434.548 | [58415.660, 58462.402] | 9.999316 |
| rho | WebSearch1 | r0 | 5 | 51269.186 | [51256.750, 51277.996] | 9.999316 |

## 证据和适用边界

- `output/pdf/completed_public_workloads.pdf`：8组总通信效应，误差线明确为窗口范围；另有SVG和PNG。
- `figures/completed_public_workloads_data.json`：全部80行的spec、原始来源hash、真实字节分项、配置、服务器对象及前端内存记账；每个原始收据还单列初始化和暖机。
- `results/public_completed_audit.json`：80份收据、10个源窗口、16个绝对开销格、8组效应及40个配对窗口。
- `results/public_exports_audit.json`、`results/public_visual_review.json`：独立数值与PDF结构核验、最终版面审阅。

实现范围沿用基础组合：Freecursive统一压缩map/PLB但无原生PMMAC/硬件控制器；ρ保留既定公开frame长度及可信Full PosMap条件，无ECC/compact/原生异步。参数R256和运行成功不提供缺失的组合安全归约。进程内真实协议字节不包含TCP/TLS，逻辑内存表也不代表可信峰值实测。
这些范围随结果保留，避免把局部性回放或成功计费表误写成完整原生系统复现。
