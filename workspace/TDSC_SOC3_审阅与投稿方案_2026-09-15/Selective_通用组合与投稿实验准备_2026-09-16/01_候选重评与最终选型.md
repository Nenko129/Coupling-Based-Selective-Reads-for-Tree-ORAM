# 按“selective read 思想可组合”重新选型

本轮问题不是把 SOC3 移植到更多系统，而是：在保留宿主的一项实质性机制后，加入 coupling-based selective read，能否在明确模型下正确、安全地减少其总通信。允许宿主适配；必须公开说明适配，保留能代表该宿主的机制，不能把原方案已经完成的省读重复计为贡献。

结论：保留 Freecursive、ρ、IR、AB 四个代表，按四种机制组织，重点补强 IR-Alloc 与 AB 的静态按层布局。没有发现一个新候选能同时在证明难度、新增收益、现有证据和实验成本上优于它们。这里不把 IR/AB 的完整原生系统复现作为必要条件。

| 候选 | 本次最小组合对象 | 判断与依据 |
|---|---|---|
| Freecursive | 递归位置表、组计数压缩、PLB；后端切换为全读/选择读 | 主文代表：说明与位置表压缩组合。保留 rollover 工作及全部后端调用计费；不声称复现原硬件控制器和 PMMAC。 |
| ρ: Relaxed Hierarchical ORAM | 地址驱动缓存、前后两棵树、固定比例迁移 | 主文代表：说明与流量分流组合。两边使用相同前端，记录完整迁移及 dummy。必须报总通信，不能只报后端降幅。 |
| IR-ORAM | IR-Alloc 非均匀真实桶容量、相同树顶缓存 | 主文代表：说明非均匀容量兼容。明确标为 IR-Alloc 风格适配；原论文还包含 IR-Stash 和 IR-DWB。DWB/压缩位置表已做的集成结果可作补充，不再要求实现原生 stash-hit skip。 |
| AB-ORAM | 公开的按层 dummy 数量/阈值，真实容量固定 | 主文代表：说明与 bucket provisioning 组合。标为 AB 静态配置适配，Y=0，不把 CB、green 回迁、DeadQ、动态借槽作为前置条件。它不是完整 AB-ORAM。 |
| Hitchhiker | 原生路径转向 + session 批量驱逐 | 暂不替换。调度依赖实际所在层和 stash；路径不是预先给定的独立全路径。把它改成固定批处理会删去重要机制；保留原调度则需新的请求分布/批维护耦合。原文 III–IV 已有同 session 桶只读一次，不能重复算成我们的优化。 |
| Palermo | 并行 Ring 协议 | 暂不替换。原文算法2第25行已经在 ResetBucket 后标记 ReadPath bypass；“复用 ER 读回的数据”不是新贡献。若做真正的 GC 读集合裁剪，仍需检查 pending 地址、CommitHead 和重叠读写的耦合。作者完整评估要求很大的模拟资源，不能凭串行缩小配置声称硬件性能提高。 |
| Shadow Block | dummy 槽中的影子副本 | 暂不替换。主块、影子块同路径且影子更深；整路径读取帮助一起读回与失效。选择读可能跳过旧影子，需补副本版本/清理关系，不能仅删读取语句。不是不可能组合，但不如 IR/AB 简洁。 |
| EP-ORAM | 缩短 EvictPath 的 NVM/DRAM 配置 | 暂不替换。原生 ER 会回填 stash，主要配置没有周期性 full-path eviction；下层依赖 ER 服务。当前只重加密的 neutral 与公开完整维护周期不能直接代替它。 |
| Fork Path ORAM | 相邻请求共享前缀 | 不选作新增效果展示。共享前缀的读写消除已经是原机制；进一步叠加 GC 需要处理延迟写回，不可把已有缓存命中算成选择读收益。 |
| TaoStore / ConcurORAM | 非阻塞路径读取、异步写回 | 后续候选。新组合要保持 fresh subtree / 缓冲和提交可见性；串行化以后只说明一个受限子机制。当前不比静态异质布局省证明成本。 |
| Tianji | Sequencer 与多服务器/秘密共享架构 | 本轮排除：不属于当前单服务器、标准球箱通信口径。与其比较需要新信任与计算模型。 |
| Treebeard | Ring 风格批处理、复制恢复 | 后续候选。Z=1、多路径与故障恢复协议要单独审计；目前不能借 Z4/Z7 容量点。 |
| DC-ORAM | 数据与位置表压缩 | 理论上正交，但暂不替换。需先界定压缩长度、固定填充和观测模型，避免把可压缩性引起的长度泄漏忽略。若只固定压缩后块长，则退化为块长敏感性，不能冒称原方案复现。 |
| PageORAM / PrORAM / RFORAM 等 | DRAM 页面/多块访问/相关标签 | 有潜力，但页面激活、批量目标和标签相关性不在当前单目标独立标签证明内。先不扩主文实验面。 |
| LatORAM / XOR / 层次 PIR 类 | 已压缩在线返回或不同服务器计算 | 保留相关工作和机制分析，不作为本文最有说服力的新增带宽组合。缺少共同成本口径时不报“优于”。 |
| PathWeaver | — | 按用户要求不考虑。 |

## 论文命名与主张

使用“与四类代表性树状 ORAM 优化机制组合”，比“四个完整系统全部复现”更符合实际。图例建议使用 `Freecursive-style map compression`、`ρ-style frontend`、`IR-Alloc profile`、`AB static bucket profile`，并在表中列出保留与适配的部分。机制范围不能只藏在附录。

推荐论文主张：**Coupling-based selective read composes with representative tree-ORAM optimizations in position-map compression, frontend traffic shaping, heterogeneous real-bucket capacity, and public dummy-slot provisioning.**

不能据此声称所有 ORAM 可组合、无条件保留任意宿主安全证明、优于所有先进 ORAM。四篇代表足以展示范围，但不足以支持全称命题。

## 一手来源

- [Freecursive 原文](https://people.csail.mit.edu/devadas/pubs/freecursive.pdf)
- [ρ 原文](https://users.cs.utah.edu/~rajeev/pubs/asplos19.pdf)
- [IR-ORAM 原文](https://mehrnoosh.net/research/IR-ORAM-HPCA%2722.pdf)：IR-Alloc、IR-Stash、IR-DWB 是不同机制，需分别命名。
- [AB-ORAM 原文](https://mehrnoosh.net/research/AB-ORAM-HPCA%2723.pdf)：静态 dummy 布局不能代表全部可调整桶功能。
- [Palermo 原文](https://arxiv.org/abs/2411.05400)、[作者代码](https://github.com/Linestro/Palermo-ORAM)：算法2第25行是本次排除“已有 bypass 再发明”的关键证据。
- [EP-ORAM 原文](https://mehrnoosh.net/research/EP-ORAM-DAC%2723.pdf)、[Shadow Block 原文](https://ceca.pku.edu.cn/docs/20190308102945094320.pdf)。
- Hitchhiker、Fork、TaoStore、DC、Treebeard 等使用项目内已下载原文及逐页提取文本；精确文件、定位词与 SHA256 见本目录的来源清单。

此表是研究优先级判断，不是证明被搁置方案无法组合，也不是声称逐篇穷尽了所有设计空间。
