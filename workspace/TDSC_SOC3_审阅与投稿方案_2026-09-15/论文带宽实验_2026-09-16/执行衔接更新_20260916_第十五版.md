# 执行衔接更新：第十五版

完整目标继续active。上一轮完成Free敏感性160份审计，本轮完成Free最终矢量图并新增ρ独立缓存/来源/统计审计，两轮均为progress。没有须用户解除的阻塞，不标complete或blocked；IR/AB机制及安全缺口、尚未收齐的正式批次仍在总目标内。

## 新完成的Freecursive图

- `src/render_free_sensitivity.py`读取第十四版已经冻结的160份证据，生成唯一一张新PDF：`output/pdf/completed_free_sensitivity.pdf`；同名SVG/PNG和 `figures/completed_free_sensitivity_data.json`。
- 左面板八配置、两个selective比较，右面板四个64B Hot-90前端配置、四后端绝对KiB/request。共32组图元，各组绑定五个原始ID。100个新实验＋60个复用对照，不将复用重复算作新实验。
- `src/verify_free_sensitivity_exports.py` 从原始总字节重新计算所有柱及区间，检查一页矢量PDF、嵌入字体和参数/范围脚注。结果 `results/free_sensitivity_exports_audit.json` passed。
- 最终PDF经Poppler150dpi渲染为1888×986，并实际通过view_image审阅：无裁切、文字重叠或不可读脚注。`results/free_sensitivity_visual_review.json`绑定PDF、PNG和数值审计hash，status=visually_reviewed。
- **51号报告** `51_Freecursive敏感性图表核验.md`新增；49号原数值报告和冻结来源不改，避免破坏其数值审计。
- 本轮PDF技能marker成功调用一次，create / expected-output-count1 / pdf；最终回复交付该PDF一次。后续不因普通续跑重新生成、重复marker或重复交付此前PDF。

## 新增ρ参数矩阵独立审计

- `src/audit_rho_sensitivity.py`：完整预声明120次新配置＋60次既有对照，共180目标；只认最终extended/fix标记，保留缺失/中间态；只对20/20（四后端×五种子）的完整配置给最终统计。
- 独立重建Uniform/Hot90/Zipf0.9的地址/版本、初始address编码值及更新payload，重算15条trace/92160个返回值。
- 独立地址驻留机器**不调用原前端、树或PRF**：以地址LRU、目录slot与后端集合重放每阶段调度，每完成帧核对LLC/ρ/backend唯一所有权、总人口、目录slot分区。逐阶段前端全部计数和两棵树remove/admit摘要与真实收据完全一致。
- 核对source/plan/加速证据、每阶段账单/RPC序号、前后树几何和实际服务器对象/声明客户端项。前树PathZ2、R=ρ可容纳其全部人口，但不称获得SOC3数值证书；完整可信后端PosMap明确计入。
- `results/rho_sensitivity_audit.json` 和 **50号报告** `50_rho敏感性独立统计.md`为过程数据。最后独立快照：71/120新运行＋60复用=131份；24格、12组selective效应＋12组参数效应，33组独立缓存重放。仍有未完成配置，不生成完整冻结快照。
- 全部180份齐备后该程序才写 `rho_sensitivity_completed_snapshot.json`；若追加门槛触发，仍须执行原计划的额外重复，不能只据complete_receipts_audited称论文完成。
- `src/check_rho_sensitivity_audit.py` 独立重算绝对/分账/配对统计及追加门槛。六个损坏收据被拒绝：计数自洽但错误的cache hit、迁移摘要、backend时隙、漏计完整PosMap、错误答案摘要、错报frame ratio。结果 `results/rho_sensitivity_checks.json` passed。
- ρ两树前树账单和完整transcript逐对相同；逐种子有理数恒等式核对整体节省=原后端占比×后端自身节省。不要用两个均值乘积冒充乘积均值。

### 新的完整切片观察

- Hot90 LLC32→128：四后端绝对通信减少43.59%–43.65%；selective整体比例仍约8.3%/11.6%。前后树帧数共同减少。
- LLC32→8：绝对通信增加约82.9%，但selective比例相近。
- Zipf0.9 ρ缓存128→32：SDE/R0对各自基线的相对减少率升到9.342%/12.830%；SDE/R0自身绝对通信却增加3.431%/5.217%。不能把相对比例提高写成总成本降低。ρ容量变化同时改变目录/PosMap/stash和前树几何，不是等可信字节预算比较。
- 小缓存组是预声明且已满五种子，保留其负参数效应。ρ512及n1/n5尚未全部收齐，本轮没有用其部分种子输出最终图。

## 已更新和校验

18号章节生成器新增Free图数值/视觉绑定和ρ过程证据绑定；README链接50/51。重新生成章节，full_chapter_complete=false。只读冻结核验7包514文件passed。

**更新ρ审计后要顺序执行check_rho_sensitivity_audit.py，再build_evaluation_draft.py。** 章节绑定当前ρ审计及check/report哈希，不能只改过程报告而不重新核验。Free最终图来源是固定的free_sensitivity_completed_audit，与ρ进度无关，不需要随其刷新。

## 最后不同审计调用的快照

- calibration40/40、public80/80、tuned50/50，均先前完成。
- 总sensitivity174/220（轻量总审计）；ρ独立审计稍早为71/120新＋60对照。
- B4 slices44/150（25个B1别名＋19个新运行）。
- ABDF43/60，零失败；压缩IR40/75，40通过；C1经典Path6/10。

## 最后CIM真实父子

| 批次 | 父PID | 子PID / 工作 |
|---|---:|---|
| sensitivity | 15408 | 26876 / SENS_rho_rho512_ring_seed104 |
| B4 bulk | 19648 | 44664 / B4_r0_N4096_B4096_seed104 |
| ABDF | 50656 | 34640 / ABDF_uniform_r0_hot90_seed104 |
| compressed IR | 54408 | 21928 / IRCM_depth_sde_dwb1_uniform_seed104 |
| C1 PathZ5 | 46680 | 45484 / C1_path5_uniform_seed104 |

续跑先验证真实进程与最终收据，不因句柄观察过期重启。B3已终止成功，不再启动。所有第十三/十四版源码锁和C1容量账本锁继续有效；本轮仅新加独立审计/绘图/文稿代码。

下一步继续收齐ρ六切片、C1、B4、ABDF、压缩IR。ρ当前审计已覆盖全部计划，可复用到完整180份后冻结并制图。IR skip的条件转录反例、AB的green容量/strict后台/DeadQ、基线完整主动安全和可信峰值仍未闭合；本轮没有修复这些问题，也没有以新表图替代它们。总体目标不得缩小或提前完成。
