优化实施与基线对比：SDE-Path / R0-Ring，SOC3 研究变体

2026-09-14，第二轮推进。以原技术报告及 SOC2 冻结成本表为对照。本轮已经实现紧凑 header、Ring neutral/read 融合，完成 Z7/A6 新数值证书，并把异构递归、参数和全部应用帧成本纳入同一配置比较。

**主要结论：推荐的 512 B 位置表配置下，SDE 相对原 SDE 的通信降低 31.05%；R0 采用 Z7/A6 后相对原 R0 降低 38.95%。相对原表 Path/Ring，后者分别降低 64.62% 和 52.88%。**

所有数字都是完整服务周期中的应用协议请求＋响应字节期望，包含 data、header、认证及控制字段；逻辑数据量保持 48 GiB，顶层 payload 为 4096 B。它们不是实测吞吐率、TCP/TLS 字节、设备页粒度 I/O 或 48 GiB 部署压测。

**与原报告的四个基线比较。** 降幅统一为 1−新成本/参照成本；因此不能把多项改动的百分比直接相加。

| 原参照 | B/顶层请求 |
|---|---:|
| Path，Z4 同格式参照 | 1,285,248.00 |
| Full-read Ring，原 lazy-neutral 参照 | 964,858.49 |
| 基础 SDE | 820,133.68 |
| 基础 R0 | 744,737.84 |

| 新配置 | B/请求 | 比基础 SDE 少 | 比基础 R0 少 | 比原 Path 少 | 比原 Ring 少 |
|---|---:|---:|---:|---:|---:|
| SDE：512 B map＋紧凑 header | 565,470.86 | 31.05% | 24.07% | 56.00% | 41.39% |
| R0：保留 Z4/A3，512 B map＋紧凑 header＋融合 | 521,624.54 | 36.40% | 29.96% | 59.41% | 45.94% |
| R0：Z7/A6、512 B map＋紧凑 header＋融合 | 454,657.53 | 44.56% | 38.95% | 64.62% | 52.88% |
| R0：Z7/A6、404 B map，含路径预算的搜索点 | 450,762.21 | 45.04% | 39.47% | 64.93% | 53.28% |

对 SDE，原表相对 Path 的优势为 36.19%，本轮相对原 Path 扩大到 56.00%，增加约 19.81 个百分点。对 R0，原表相对 Ring 的优势为 22.81%，本轮相对原 Ring 扩大到 52.88%，增加约 30.06 个百分点。这里“百分点增加”与“相对自身降低 38.95%”是不同指标。

**实际实现了什么。** SDE 路线保留 Z4/A3/m2 的 mask、service 和 canonical placement，只调整递归块大小及固定 header 布局。R0 路线增加了 mixed slot read：由公开 count 判定哪些桶需 neutral，一次请求读取这些桶的 Z 个 slots、其他桶的一个 slot，全部 openings 验证后本地完成重排与消耗，最后只写一次最终 path。

descriptor 仍保留 UID16/address8/leaf4/slot2；移除保留 padding 后，Z4 header 为 204 B、Z7 header 为 300 B。tag 仍为 64 B，nonce 仍为 16 B；采用独立 SOC3 frame 和 PRF context。原 SOC2 证据包没有被改写或冒用其契约。

R0 成本的实际递进为：744737.84（原配置）→539001.84（仅采用较小 map 并重选容量）→521624.54（紧凑 header、融合读取、Z4/A3）→454657.53（Z7/A6 新证书及联合配置）。后两步的成本都由新序列化执行和独立计费模型支撑。缓存、XOR、SDE 路径交集复用和按需 payload 解密尚未计入这些数字。

**推荐配置及客户端空间。** 以下每一行都保持对应原 SDE/R0 的数值 stash lifetime 上界，连同各层 setup 请求重新计算；并非通过放宽原失败上界换取性能。

| 配置 | B0/B1 | Z0/Z1 | A0/A1 | S0/S1 | L0/L1 | R0/R1 |
|---|---|---|---|---|---|---|
| SDE：512 B map＋紧凑 header | 4096/512 | 4/4 | 3/3 | 3/3 | 23/16 | 192/160 |
| R0：保留 Z4/A3，512 B map＋紧凑 header＋融合 | 4096/512 | 4/4 | 3/3 | 3/3 | 23/16 | 192/159 |
| R0：Z7/A6、512 B map＋紧凑 header＋融合 | 4096/512 | 7/7 | 6/6 | 6/6 | 22/15 | 149/147 |

| 配置 | 持久 payload＋末级表 | 报告口径的路径 payload | 两者合计 | 服务器对象存储 |
|---|---:|---:|---:|---:|
| 原 SDE | 1,425,408 B | 397,312 B | 1,822,720 B | 264.95 GiB |
| 原 R0 | 1,425,408 B | 380,928 B | 1,806,336 B | 471.90 GiB |
| SDE：512 B map＋紧凑 header | 1,261,568 B | 397,312 B | 1,658,880 B | 262.49 GiB |
| R0：保留 Z4/A3，512 B map＋紧凑 header＋融合 | 1,261,056 B | 380,928 B | 1,641,984 B | 469.54 GiB |
| R0：Z7/A6、512 B map＋紧凑 header＋融合 | 1,078,784 B | 634,880 B | 1,713,664 B | 435.02 GiB |
| R0：Z7/A6、404 B map，含路径预算的搜索点 | 1,168,432 B | 634,880 B | 1,803,312 B | 435.32 GiB |

这是按原报告公式作的 payload 预留比较，不是 Python RSS 或完整总 RAM。header、descriptor、cached ciphertext、认证/加密 scratch、递归局部变量及运行时另计。Z7/A6 减少持久 stash，但更大的桶使数据路径 workspace 从 93 增至 155 个 4 KiB blocks；上表明确计入了这一变化。512 B 主配置的两项合计仍低于原 R0。

如果只约束持久 payload＋末级表不超过原来的 1425408 B，网格内的 R0/SDE 混合点 B=(4096,264) 可达 439475.20 B/请求：相对基础 R0、原 Path、原 Ring 分别少 40.99%、65.81%、54.45%。但加上 Z7 路径 workspace 后，该点超过原 R0 的两项合计预算，故不把它作为同路径空间预算下的主结果。约束两项合计后，纯 R0 的 B1=404 搜索点为 450762.21 B/请求，相对基础 R0 少 39.47%。

512 B 主配置比 404 B 搜索点只多约 0.86% 通信，却保留了更多该口径的空间余量，因此更适合作为下一阶段工程默认配置。搜索网格为 B1=128..4096、步长 4，按每层原有 failure contribution 选最小证书充分 R；这不是连续全局优化或最小 stash 下界。

**给 Path/Ring 同样调优后，剩余优势是多少。** 下面各参照也使用 B=(4096,512)、紧凑 header；Ring 同样融合 neutral 和 logical read，并在 S=1..10 内按树选择。A=6 的 Ring 因 full-read 频率更高，最优 S 是 9，不沿用 R0 的 S=6。

| 对照方式 | 同样调优后的参照成本 | 我们的配置成本 | 仍减少 |
|---|---:|---:|---:|
| SDE vs Path，Z4 | 886,152.00 | 565,470.86 | 36.19% |
| R0 vs Ring，双方 Z4/A3 | 670,505.29 | 521,624.54 | 22.20% |
| R0 vs Ring，双方 Z7/A6 | 592,498.81 | 454,657.53 | 23.26% |
| R0 vs Ring 数据树＋相同 SDE map 的混合参照 | 578,285.26 | 454,657.53 | 21.38% |

因此，相对原表 Ring 的 52.88% 包含递归和通用报文优化的收益；在双方获得相同通用优化及 Z7/A6 后，仍保留约 23.26% 的通信优势。再给 Ring 使用本项目的 SDE 小块 map，R0 主配置仍少约 21.38%。

这些 Path/Ring 行沿用“同格式成本参照”的身份：本轮没有为它们建立与新 SDE/R0 相同的 stash 失败证书，也没有穷尽缓存、XOR、所有 Z/A 及全部递归结构。Path Z4 的 L/N 布局尤其不能自动借用 Path 论文 Z5 的 stash 定理。它们不是对全面优化且所有安全/内存约束均相等的最佳 ORAM 的全局胜出声明。

**新证书与安全预算。** 上轮 Z7/A6 只有近似筛查，本轮已经计算 Phi_7/Poi(3) 的完整三维联合上界网格：cap=280、h≤24、Poisson cutoff=128，两种模式各 6744 个端点，并用较大者作 exact dyadic 查询。root/fresh offset 重新取 12。

| 新 R0 主配置的层 | h | R | 传入 H 的阈值 | 单时刻上界 |
|---|---:|---:|---:|---:|
| 0 | 23 | 149 | 137 | 4.8386708338e-62 |
| 1 | 16 | 147 | 135 | 1.8370401215e-64 |

包括 setup 的 lifetime stash 上界为 8.9596596618e-43，低于原 R0 约 2.41354e-42。按 n≤13 重算采样误差、并使用更保守的 PRF 调用预算后，条件 ORAM advantage 上界约 3.6913391656e-40，通过 2^-128 目标。

这里的“条件”保持原研究假设：variable-input 512-bit PRF 在给定调用预算下每次 hybrid advantage≤2^-132；单客户端、串行、不可回滚、fail-stop、固定且独立于 ORAM 随机性的逻辑历史。源码身份、数值上界和手工归约说明被独立 variant_contract 绑定；它不是形式化证明助手证书或生产部署认证。

**延迟方面的区别。** 原 R0 两层的串行 RPC 周期期望约 10.5738；新纯 R0/Z7 主配置为 7。新 R0 数据树＋SDE map 的 512 B 混合配置为 458666.55 B/请求、约 6.1667 RPC：它的通信比纯 R0 多约 0.88%，但往返更少。高 RTT 环境可能更偏好混合配置，必须通过网络实测决定；SDE 两层仍约 5.3333 RPC。

**执行验证。** 本轮包含原参数下 2700 个集成请求、6 类参照各 1000 个请求、Z7 新配置 1440 个请求、16-slot Ring/404 B map 对照 360 个请求，以及融合计费专用轨迹。所有对应整树认证、RAM 读写和逐帧计费检查通过。新增配置还覆盖目标位于 neutral 桶、一次多个 neutral、单槽和多槽混合请求。

数值方面有 160 条独立 Fraction 不等式、1/4 线程逐位一致；结构方面有 1280 次 field/count 等式、1280 次 commutation、640 次 root shift、108 个 A6 marking 快照；认证复用套件有 20 类拒绝场景；计费有 2250 条融合前后精确恒等式和 48 组独立精确 Binomial 周期期望包围；gate 有 10 类错误配置/身份拒绝及 horizon 在 I/O 前拒绝。小规模实验并不替代稀有失败概率的证明或大规模性能实测。

**建议采用的阶段结果。** 以 SDE-v3-512 和 R0-v3-Z7-512 作为新的研究主配置，保留原表作为历史比较，另列同样调优后的 Path/Ring 表。高 RTT 场景再比较 Hybrid-v3-Z7-512。下一阶段可利用剩余客户端空间实现固定顶部缓存，并按相同缓存预算重调 baseline；该收益尚未计入本报告。

完整表与证书配置：[profile_comparison.json](D:/projects/SDE-R0/research_20260914/optimization_v1/results/profile_comparison.json)。

归约、认证及密码学预算说明：[variant_reduction_and_authentication.md](D:/projects/SDE-R0/research_20260914/optimization_v1/proofs/variant_reduction_and_authentication.md)。

研究实现：[optimized_oram.py](D:/projects/SDE-R0/research_20260914/optimization_v1/src/optimized_oram.py)、[融合流程](D:/projects/SDE-R0/research_20260914/optimization_v1/src/fused_logical.py)、[独立成本模型](D:/projects/SDE-R0/research_20260914/optimization_v1/src/optimized_cost.py)、[独立参数入口](D:/projects/SDE-R0/research_20260914/optimization_v1/src/optimized_gate.py)。

新数值证书重算记录：[recompute_receipt.json](D:/projects/SDE-R0/research_20260914/optimization_v1/numerics/recompute_receipt.json)。
