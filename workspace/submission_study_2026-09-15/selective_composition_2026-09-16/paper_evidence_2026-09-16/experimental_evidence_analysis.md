# TDSC 论文实验章节完整分析

生成时间：2026-09-17T04:06:11+08:00

## 1. 冻结范围与结论边界

本证据包冻结了两组正式矩阵：纯 selective 组合矩阵 120 条、规模与块大小矩阵 125 条。没有增加协议分支；纯组合矩阵关闭 compact header、neutral/read fusion、省根、small-map 和 `(Z,A,S)` 重调，只改变逻辑读集合。所有核心效应均以同一 trace seed 成对比较，5 个独立种子报告 paired mean 与 Student-t 95% 置信区间。

可支持的核心结论有两层。第一层是当前 SDE/R0 完整设计在同一调优流程下的通信收益：uniform 下 SDE 相对 Path 为 **35.767%**，相对 Deferred 为 **24.176%**；R0 相对 tuned Ring 为 **25.366%**。第二层是 selective read 的可组合性：在 Freecursive-style、rho-style、IR-style 与 AB-style 四类宿主上，最小组合的实测通信下降落在 **9.618%–25.010%**；最低为 rho/host、B=4096，最高为 AB/depth、B=64。

这些结论不等同于“所有先进 ORAM 上全局最优”。IR/AB/Freecursive/rho 结果是冻结执行模型中的最小组合证据，不是四篇论文原作者代码的原生端到端复现。真实可信内存峰值与真实网络延迟没有测量，因此论文只能报告通信、RPC、持久存储口径和模拟器执行成本，不能把模型推断写成实测 latency 或 peak RSS。

## 2. 实验设计

- **执行环境**：Windows-11-10.0.26100-SP0，Python `3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]`，可见逻辑处理器 20；实现是可审计参考 harness，不是优化后的生产代码。
- **统计单位**：seed 级成对差值；每个正式格 5 个种子，置信区间基于 paired saving，而不是把请求当作独立样本。
- **主比较**：tuned Path/Deferred/SDE 与 tuned Ring/R0，N=16,384、B=4,096，uniform 与 hot90。
- **规模矩阵**：N/B 组合覆盖 `(4096,4096)`、`(16384,64/256/1024)`、`(65536,4096)`；每格 Path、Deferred、SDE、Ring、R0 各 5 个种子，共 125 条。
- **最小组合矩阵**：N=4,096；Freecursive-style、rho-style、IR-style、AB-style；B=64/4,096，并为 IR/AB 增加布局与 full-probe 归因控制，共 120 条。
- **消融**：small map → compact header → fusion → `(Z,A,S)` retuning，并单列 joint effect，避免把联合收益解释为各项相加。
- **稳健性**：公开负载、Freecursive/rho 参数敏感性、IR guarded 补充与条件式 AB+CB 补充。

## 3. 主结果：SDE 与 R0

同样调优后的结果应作为主文数字。uniform 下：

| 比较 | bytes/op（对照→方案） | 通信下降 | 95% CI | RPC 变化 |
|---|---:|---:|---:|---:|
| SDE/Path | 527,664.00 → 338,932.57 | 35.767% | [35.658%, 35.877%] | -33.325% |
| SDE/Deferred | 446,997.06 → 338,932.57 | 24.176% | [24.046%, 24.305%] | 0.000% |
| R0/Ring | 339,710.71 → 253,539.89 | 25.366% | [25.186%, 25.546%] | 0.000% |

SDE/Path 的 RPC 指标为负，含义是 SDE 为换取通信下降增加了 RPC；SDE/Deferred 和 R0/Ring 的 RPC 数量基本持平。论文中应把通信和 RPC 并列，避免只给 bytes 的单指标结论。规模矩阵的 15 个 paired effects 全部完成，通信下降总范围为 **22.399%–36.067%**；详细值见 `table_02_scale` 与 Fig. 2。

## 4. selective read 的最小组合证据

最小组合关闭所有 SOC3 辅助优化，所以这里测得的是 selective read 本身在宿主调度中的增益。10 个主格均通过重复数与变异门槛，4 个 IR/AB full-probe 控制把放置规则固定后再比较读集合。IR/AB 的理论期望与实测均值最大偏差为 **0.039 个百分点**，说明计费归约和执行收据一致；Freecursive/rho 因前端 tick 与命中行为由 trace 决定，不用单一固定理论值替代实测。

可写入论文的组合性表述是：“在四类公开设计抽象上，仅替换逻辑读选择即可取得可重复的通信下降。”不应写成“完整移植 SOC3”或“对原作者实现无条件获得同一收益”。

## 5. 消融与收益来源

五步消融给出的 paired communication saving 为：small map **15.405%**、compact header **2.052%**、fusion **0.841%**、参数重调 **16.203%**，联合结果 **31.151%**。联合结果是相对共同起点的效果，不能把四个边际百分比直接求和。fusion 的通信贡献较小，但 RPC 贡献明显；这正是分离消融比“compact+fusion 一起开”更有解释力的原因。

## 6. 公开负载、敏感性和补充证据

公开负载的全部窗口与区间见 `table_06_public_workloads`。Freecursive/rho 的完整参数敏感性保存在 `table_09_sensitivity_full`，用于说明收益随前端选择率和维护占比变化。IR guarded 与 AB+CB 结果放在补充表中：前者是 guarded adapter 证据，后者仍受容量安全准入限制，均不进入“原生系统复现”的主结论。

## 7. 存储、CPU 与延迟口径

`table_07_resources` 只统计远端持久对象、客户端持久对象、预留 stash payload 与 terminal map。它没有覆盖 allocator、索引、同时存活的多桶 ciphertext、decoded payload、final-write buffer 和认证 scratch，因此不能称为真实峰值可信内存。运行收据保留了 Python harness 的 CPU/harness seconds，可用于审计实验成本，不能外推为生产实现延迟。没有真实网络 RTT/吞吐实验，论文不得声称“实测 latency improvement”。

## 8. 审计闭合与论文写法

证据包包含 120 条最小组合收据、125 条规模收据、审计 JSON、计划与哈希锁、CSV/LaTeX 表格、PNG/SVG/PDF 图件和可编辑 Excel 工作簿。功能正确性由答案哈希、成对 trace、transcript、边界状态检查和 fail-stop 检查共同支撑。容量网格覆盖 12,506 点，记录的 lifetime bound 为 log2 `-146.3867`。

建议主文使用三组强结论：同调优主比较、跨 N/B 稳健性、四宿主最小组合。消融与公开负载放主文次级图表；完整敏感性、IR guarded、条件式 AB+CB 和原始收据索引放补充材料。旧 Ring 的 52.88% 只能作为历史配置结果，不再作为核心 selective gain。
