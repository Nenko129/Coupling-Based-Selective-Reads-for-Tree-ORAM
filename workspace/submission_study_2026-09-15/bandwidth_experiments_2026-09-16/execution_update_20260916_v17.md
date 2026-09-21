# 执行衔接更新：第十七版

完整目标继续active，不标complete或blocked。上一问答轮主要核对“除ρ外是否超过20%”的口径，没有新增实验工件；本轮重新确认真实进程后完成ρ完整图表，并把AB DeadQ公共模型推进到实际加密/认证路由，属于progress。无须用户解除的阻塞。

## 1. ρ敏感性全部完成；不要重启

- 父15408已真实退出，全部120次新运行的最终收据均通过独立审计；加60次既有对照，共180份。原220次前端敏感性计划现在220/220（Free100+ρ120）。
- `src/audit_rho_sensitivity.py`已生成 `results/rho_sensitivity_completed_snapshot.json`：complete_receipts_audited、36格、18组selective效应、24组参数效应、45组独立缓存重放，无追加重复门槛。
- 顺序运行 `src/check_rho_sensitivity_audit.py`：180份、36格、42组效应通过，六种损坏收据拒绝。当前volatile audit与complete snapshot内容hash一致；不要无理由改动已完成审计源码或反复重写快照。
- 新 `src/render_rho_sensitivity.py` → `figures/completed_rho_sensitivity.svg`、PNG及data JSON。**本轮只创建SVG/PNG，没有新PDF，没有PDF marker。** SVG字体轮廓化，无栅格嵌图。
- 新 `src/verify_rho_sensitivity_exports.py` 从180原始收据重算全部54组均值/区间，另解析SVG实际柱宽，用图内零点/最大值reference路径校准，54根全部一致。
- 最终2526×1331 PNG已实际view_image审阅。初版轴标签与图注重叠已修复（bottom=.30）；最终无缺陷。`results/rho_sensitivity_visual_review.json`绑定最终SVG/PNG和数值审计hash。
- 新 `src/summarize_rho_completed.py` → **55号报告 `55_rho敏感性完整图表.md`**，以及 `results/rho_sensitivity_completed_evidence.json`。本轮最终应交付新完整图表，不重复此前PDF。
- 全九配置SDE整体5.864%–14.122%，R0整体8.629%–17.863%。Uniform n1/3/5分别14.122/8.290/5.864与17.863/11.647/8.629。后端自身仍约22/24.5，前树摊薄解释变化；不是所有参数保证。
- 范围仍为address-LRU、公开帧长、full trusted backend PosMap；无原生ECC/异步控制器/set-associative、真实峰值或新安全证明。缓存参数变化不是等可信内存比较。

## 2. AB DeadQ：实际认证外部索引及AES-GCM记录

新独立模块，不修改运行中的CB/ABDF/IR/核心，也不修改52公共模型和其证据：

- `src/ab_deadq_authenticated_store.py`：实际二进制B/G/U/C请求和回复；SHA256 Merkle行存储，含行地址/长度域与独立叶/节点域。客户端当前根验证每次读与更新旧行proof，自算更新根。服务器working tree与committed分开，最终tx/step/root一致后客户端才发布根。
- `src/ab_deadq_routed_allocator.py`：logical map/valid/epoch、physical owner/version、FIFO及scheduled计数全部在认证外部行。按需组件BFS双向检查，不调用全状态Allocator或常驻O(P)owner表。事务缓存提交后清除；每次扫描FIFO和组件都有实际通信。
- 实际AES-256-GCM记录，nonce12/tag16，记录总长B+37（flag1、UID8、payloadB、nonce/tag）。AAD绑定domain（实例key与几何摘要）、logical bucket/slot、physical、epoch、generation。Merkle先于解密，输出所有槽包括dummy重新加密。
- nonce在prepare时单调消耗，错误永久停止，不回滚重用。默认fresh随机key，测试key是公开可复现fixture；部署不得相同key重置nonce。客户端无重启恢复。
- 支持consume/gather/rebuild/rebuild_consume，另有caller admissions接口用于符号UID重新接纳。该接口不做跨全系统重复UID/leaf检查；上层需负责正确所有权/放置。原52的K组件限制、整轮warmup、FIFO完整prefix、短队列/超K回退保留。
- prepare期间只改事务cache，不发布client root或committed server tree；commit逐行更新working tree并验根，最终ACK通过后返回消费记录。坏ACK可能发生在server已commit后，client永久停止；**不声称server回滚、持久性、恶意可用性或故障恢复**。
- generation/epoch不是SOC3 γ，尚无CB动态n/τ、green、fresh remap、递归树、scheduled球箱放置或ORAM模拟。不能称完整AB，也无带宽改善结论。

### 已执行检查和微观证据

- `src/check_ab_deadq_routed_allocator.py`：五种子×200=1000次真实加密状态转换；以旧完整模型作oracle（仅测试工具使用），逐项核对maps/valid/owner/version/epoch/FIFO/scheduled及独立AES-GCM解码的UID集合。
- 111次扩张、101次连带重建，有远端真实记录；含fused动作与nonce唯一性检查。prepare前后已提交目录不变，返回记录仅commit之后。
- 13项认证/中止检查：proof、ciphertext、更新根、坏finalACK、旧ACK、旧FIFO改上下文重放、六个AAD字段错误、abort nonce不重用。精确捕获AuthenticationFailure/InvalidTag，不把任意异常当通过。
- 固定120公共操作比较全dummy和每桶一个真实记录、不同私有shuffle/key；公共地址与帧长度相同。有限功能检查，不替代自适应转录证明。
- 四物理槽见证：B的真实UID91确实放在A的物理槽0，触发A重建后通过{A,B}联合暂存保持记录。6操作、95RPC、21719bytes，数据记录3535、metadata2042、proof10624、control5518。proof/索引/控制占83.72%；说明新增认证成本不能省略，不是理论下界或ORAM收益。
- 六个压缩原始wire保存在 `results/ab_deadq_routed_wire/`，`results/ab_deadq_routed_checks.json`绑定hash及每次账单。
- 新 `src/audit_ab_deadq_routed_evidence.py` 独立重算每条wire的Merkle根和四类字节，共18364 RPC、1006提交；三种损坏wire被拒绝。生成 `results/ab_deadq_routed_evidence_audit.json` 及 **54号 `54_AB_DeadQ认证路由与加密检查.md`**。
- selected持久字段120bytes不是trusted peak。初始化全表、Python对象、AES runtime、staging、cached rows、proof/write scratch、server working副本均不能视为免费。原始wire记录是harness，不是运行时可信表。

下一步应将路由适配到真实CB引擎并计费，同时补动态n/τ、γ/nonce域、scheduler/neutral与caller admissions契约；随后才做同物理预算的Ring/GC-Ring/R0完整对照。不要用更多小域模型或本micro数字替代ORAM组合实验。逐行proof成本高，batch/multiproof是可能的后续优化，需先保留同一认证语义。

## 3. 文档与完整性

- 18号章节及生成器绑定新的54/55及其证据，已成功生成，`full_chapter_complete=false`。
- README/带宽口径说明更新为ρ敏感性完整，分开ABDF条件性能和DeadQ微观成本。
- 最新只读冻结核验：7包514文件全部不变。
- 不重复生成此前已交付的Free/ρ基础、IR有限/周期、公开trace、核心、静态、消融、校准、调优、Free敏感性PDF。
- C1仍10/10完成，B3仍50/50；经典Z5补充表在53号，不能替换Z4主基线。

## 4. 最新审计快照与真实进程

独立auditor最后一次快照：calibration40/40、public80/80、sensitivity220/220、tuned50/50、slices73/150（含25个旧B1别名）；ABDF57/60、零失败；compressed IR63/75、全部63通过。不同审计调用不是同一时刻，不猜其后完成数。

最后CIM实际仍活跃：

| 批次 | 父PID | 子PID / 运行 |
|---|---:|---|
| B4 bulk | 19648 | 34288 / B4_ring_N16384_B64_seed105 |
| ABDF | 50656 | 32196 / ABDF_bottom_d0_ring_hot90_seed105 |
| compressed IR | 54408 | 44584 / IRCM_B4_depth_path_dwb1_hot90_seed102 |

ρ父15408已退出且全120最终审计通过，不重启。C1/B3此前也完成。继续尊重所有既有common/core/组合/IR/AB/frozen源码锁；本轮新增DeadQ模块可迭代，但一旦更改须刷新其原始trace、检查、审计及章节来源hash。

优先收齐ABDF剩余3和压缩IR预声明β4压力格，随后各自完整原始表与图；B4仍需剩余大规模切片。IR-Stash skip当前转录反例尚未修复，不能以no-skip替代原生目标；AB真实路由仍需CB集成与容量/转录准入。总目标未完成，没有新用户依赖，不做blocked/complete状态更新。
