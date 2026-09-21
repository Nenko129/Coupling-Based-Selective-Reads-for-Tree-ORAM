# 执行衔接更新：第十六版

完整目标继续active。上轮完成ρ独立调度审计和Free敏感性图，本轮推进AB DeadQ分配契约并完成C1全部结果，两轮均为progress。没有须用户解除的阻塞，不标complete或blocked；总体原生机制、安全/资源和剩余实验缺口仍保留。

## 本轮主进展：DeadQ首次扩张及原桶覆盖问题

重新读取并在线核对AB原文§V-B/C和§VI，保留每层FIFO、整轮维护后扩张、队列不足回退等来源规则。没有把额外的联合重建规则归称作者原算法。

- 新 `src/ab_deadq_allocator_model.py` 是**公共分配器模型，不是密码ORAM**。固定单层M个桶，每桶b个物理槽，共P=M·b；逻辑槽数b或b+r。记录活跃逻辑→物理所有权、租用generation、重建epoch、FIFO、scheduled位置。
- 活跃借用图连接logical owner与physical home；限制每组件≤K。原桶重建时暂存并重建其完整组件，从而不覆盖组件外对象。恢复各桶基准容量后只对触发桶尝试FIFO前r项扩张；短队列或组件过大会完整回退，不部分授予。
- `gather`可以重新收集此前队满跳过的dead槽；只对调用者已认证的公开physical home调用，实际认证IO尚待集成。queued槽去重及版本检查。
- 事务working state在最终ACK边界后才发布。支持原子`rebuild_consume`：先工作状态重建、后虚拟消费，不能在ACK前将其dead槽出借。坏ACK和重放旧digest会fail-stop。**这里digest字符串是认证边界的模型，不是HMAC/AEAD实现。**
- 新 `src/check_ab_deadq_allocator_model.py` 独立构造owner数组/关联图并检查FIFO和组件界。两个两桶抽象状态图自然遍历闭合：K1的300状态/1932转移；K2的1676状态/10860转移。共1976状态、12792转移。K2含2376条扩张及1368条连带重建转移。
- 绝对generation在租用一致性校验后归一化；旧消息另测，不从有限图推断完整密码安全。深度上限24未触及，不是截断后宣称穷尽。
- 九项边界检查：未提交不发布、错误ACK、旧ACK、过期租用、组件上限、短FIFO、fusion发布顺序、fusion坏ACK，以及队满后gather。五个四桶符号记录试验各500步，共2500；独立public action RNG与payload放置RNG分离，真实UID可放在远端槽，记录保持通过。不是加密运行或性能样本。
- 最小E0见证：两个桶各两物理槽，完整scheduled暖机后消费A两槽，B借A一槽扩张；触发A重建时组件为{A,B}，B的远端活跃槽先被暂存，全部物理数据槽仍四个。旧938强独立预留定理保持有效，新设计以允许联合重建改变前提。
- **52号报告** `52_AB_DeadQ所有权与联合重建.md`给出四个所有权/空间/提交论证、具体见证和完整集成门槛。
- `results/ab_deadq_allocator_model_checks.json`为执行证据；`src/audit_ab_deadq_allocator_evidence.py` → `results/ab_deadq_allocator_evidence_audit.json`绑定原PDF、代码和报告，status=evidence_consistent。

### 不得越过的范围

新模型解决公开分配可行性，不等于原生AB。最多K−1个连带重建桶会带来额外通信；实际physical-routing认证、反向所有权索引、variable n/τ及局部证明、CB/SOC3集成、green容量归约、主动转录模拟、真实峰值和重复带宽实验均未完成。不能将现有ABDF的20%–22%贴到这个模型上。

模型的P不含新metadata，更不能不计成本地保留O(P)可信owner表。正式实现应采用认证外部公共索引并核算所有查询/写入。模型stage槽数≤K·b、写入槽数≤K·b+r只是组合上界，不是可信内存峰值。epoch/generation都不是SOC3 γ；γ及nonce语义还要在实际引擎中绑定。

未修改任何运行中的AB/IR/核心源码。模型仍独立，下一步应实现真实认证路由与联合提交接口，再接CB；不要用更多纯摘要或模型性能预测取代这项集成。

## C1经典Path补充全部完成

- 真实父46680及其子已退出；`results/classical_reference_queue_bulk_completion.json` status=passed，十行均通过。**不要重启C1。**
- `src/audit_tuned_reference.py`更新为all_runs_audited，B3 50/50、C1 10/10，八组效应，未触发追加重复。
- 新 `src/freeze_classical_completed.py`再次核对十个补充原始收据、复用的二十个Path Z4/SDE收据，冻结 `results/classical_completed_snapshot.json`（30份来源、六格、六组比较）；重复调用要求与既有快照完全相同。
- **53号报告** `53_经典Path补充完整结果.md`列通信、RPC、服务器对象、已列客户端资源及分母。
- N16384/B4096/mapB256；Path Z5/R258每次实际657456 bytes/op，Path Z4/R256每次527664。SDE uniform338932.57、hot90 338824.32。
- SDE相对Z5：48.447870% / 48.464335%；相对Z4主基线仍35.767% / 35.788%。不以更贵Z5替换Z4放大主张。
- Path Z5较Z4贵24.597%；服务器对象654.695198 vs525.051003 MiB；stash payload＋terminal1097.5 vs1089 KiB。后者不是完整峰值。
- 仍仅45号固定历史/理想叶/初始化/寿命stash账本范围，不冒称同完整主动安全保证。
- 本轮未创建PDF，不调用marker；所有此前PDF不重导、不重复交付。C1此轮以完整表格交付。

## 文档与校验

18号稿及生成器新增DeadQ限定证据、C1已完成状态和冻结来源；README链接52/53。最终build_evaluation_draft通过，full_chapter_complete=false；只读冻结核验7包514文件passed。

更新ρ审计后仍顺序执行check_rho_sensitivity_audit.py再生成18号稿。C1已冻结，后续不要修改其相关账本或审计来源而不显式维护固定证据链。

## 最后审计快照

- calibration40/40、public80/80、tuned50/50；C1现在10/10。
- 总sensitivity206/220（最后轻量总审计）；ρ独立审计稍早为104/120新＋60对照，164份、32格、16组selective＋20组参数效应，41组缓存重放，未触发追加。
- B4 slices57/150（25个B1别名＋32个新运行）。
- ABDF49/60，零失败；压缩IR49/75，49通过。
- 上述不同调用的快照不是同一时刻，不猜后续完成数。

## 最后CIM确认的父子

| 批次 | 父PID | 子PID / 工作 |
|---|---:|---|
| sensitivity | 15408 | 7652 / SENS_rho_ratio5_deferred_seed103 |
| B4 bulk | 19648 | 50608 / B4_ring_N16384_B64_seed102 |
| ABDF | 50656 | 38692 / ABDF_uniform_r0_uniform_seed105 |
| compressed IR | 54408 | 46524 / IRCM_depth_path_dwb1_uniform_seed105 |

C1和B3都已真实终止成功；旧session失效不需重启。其余四父仍实际运行。所有common/core/组合/extended/bulk/缓存、IR与AB的现有源码锁继续有效；独立新增分配模型可继续开发，但不可改写冻结实验语义。

继续收齐ρ（只剩ratio5部分）、ABDF、压缩IR（含β4预声明压力）、B4。ρ齐备后做完整180份快照和最终图。ABDF齐备也仍是无DeadQ的条件协议。IR skip反例尚未修复，不能用no-skip替代；完整主动安全、异质/green归约和可信峰值也仍缺。保留总目标，不提前complete。
