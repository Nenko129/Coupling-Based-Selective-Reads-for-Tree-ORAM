# 执行衔接更新：第十二版

完整目标继续active。本轮为progress：推进经典基线执行归约、完成新的独立检查、生成真实递归容量账本，并预声明和实际启动补充Path对照。没有用户输入型阻塞，不能标complete或blocked。第十一版的IR/Z4反例与空间核验仍有效，本轮未改动那些运行源码和收据。

## 本轮新增的基线证据

重新核对Path JACM原文§3.4–3.5/定理5.1，及Ring USENIX原文§4/附录B；在线打开作者/USENIX PDF。源PDF仍为baselines/path.pdf、ring.pdf。空树初始化、首次访问零值及整路径贪心回填可以对齐。固定递归访问的第j层初始化计数是Σ(i≤j)N_i。

- `src/check_classical_execution_projection.py` → `results/classical_execution_projection_checks.json`：24组诊断，独立不加密逻辑放置oracle逐地址比对实际加密状态；5076个访问边界、980次定期驱逐、3237次neutral恒等、2115次融合逻辑投影、3259个fused early桶。覆盖Path Z4/Z5、Ring Z4/A3和Z7/A6、S1/3/6/9、fusion开关、三层递归、集中叶碰撞和非空stash。session79959已正常exit0，勿重复启动。
- `src/check_classical_active_failstop.py` → `results/classical_active_failstop_checks.json`：22个坏opening、payload proof、ACK路由和重放检查；包含PathZ5与RingZ7/S9的n16。坏响应后无继续解密，committed anchor不变，后续零RPC；不要求远端回滚。
- `src/classical_stash_binding.py` → `results/classical_stash_execution_ledger.json`：实际B1/B3配置、在线2^56+逐层初始化计数、stash预算2^-130。Ring显式保守预留A−1，把驱逐后尾界转换为每次完成访问边界的界。R≥N采用当前记录数确定性界。
- B1 Ring4/3 R256：log2寿命stash上界约−298.638，所列表达式最小公共R137；B3 Ring7/6 R256约−249.57，最小公共R160。**没有据此缩小正在运行的R256**。
- PathZ4仍不获经典Z5定理覆盖。补充Path Z5/A3、相同B3递归布局下的最小公共R258，log2上界−130.32976837282325；map层N256≤R258，使用零失败计数界。这不是完整主动安全准入。
- `src/check_classical_stash_binding.py` → `results/classical_stash_execution_ledger_audit.json`：独立128阶指数包络、递归几何/初始化/分项界核验，拒绝6种篡改账本。
- `src/audit_classical_minima.py` → `results/classical_minima_audit.json`：另外独立确认3个最小公共R和4行旧寿命阶段修订。
- 旧29号文档的2^96/2^-128表保留历史算术；加入A−1后，Ring4/3最小R为164(K1)/167(K16)，Ring7/6为190/193。已给29号文档加后续修订说明，未改写原历史JSON。
- `src/build_classical_report.py` → **45号报告**与`results/classical_reference_evidence_audit.json`：归纳式逻辑过程对应、容量式、具体数据、源绑定和所有未覆盖事项。所有有限测试只作实现证据，不替代任意长度安全证明。

统一边界：理想独立叶标签、固定且与ORAM币独立的地址历史、均匀核心、成功认证前缀。完整主动转录模拟、PRF/认证/模偏差预算、公共寿命限制及真实可信峰值仍未整体闭合。IR-Stash、CB、异质容量和DeadQ不能继承这个账本。

## 新补充Path正式测量（已真实启动）

`src/prepare_classical_reference.py`生成：

- `formal_classical_reference_plan.json`：十次，uniform/hot90×seed101..105；N16384/B4096、map B256、terminal8192、暖机2048、测量4096。仅把Path Z4/R256改为Z5/R258，trace和ORAM seed逐一沿用B3。
- `classical_reference_queue.json`：单worker、现有bulk执行器、现有可用内存阈值。
- 周期模型657456 bytes/op，不能写成已收齐的测量；更不能替换较强的Z4调优主基线以制造优势。
- 执行：`src/dispatch_bulk_scale.py --queue classical_reference_queue.json`，**session19203，实际父PID46680**。
- 最后CIM独立确认子**17980**在执行`C1_path5_uniform_seed101`。起初内存不足时正确等待，后来正常启动；最后可用物理内存约2051824KiB。
- 输出`results/formal_classical_reference/`，状态`results/classical_reference_queue_bulk_state.json`，完成回执`results/classical_reference_queue_bulk_completion.json`。
- 队列绑定plan、classical_stash_execution_ledger和其audit的哈希，运行期间不要改写这些文件或其生产源码。报告与另外的minima审计不在该队列输入中，可独立维护。

## 调优/补充独立审计

新 `src/audit_tuned_reference.py`，**46号报告**，`results/tuned_reference_independent_audit.json`。

逐行独立重放payload版本并重算返回值摘要，验证真实字节分项、RPC序列、递归时钟、物理对象空间和配对trace。B3与新C1分别计进度。部分组给实际n、不报告最终95%区间；五次完整组才生成配对Student区间。保留预定CV>10%或区间半宽>5个百分点的追加门槛。

最后独立审计 **B3 46/50、C1 0/10**，6个过程效应，当前完整组无追加门槛触发。C1首个真实worker在运行，不能据文件尚无完成收据重复启动。

## 最后经过核验的其余进度和实际进程

- extended_statistics稍早快照：calibration40/40、public80/80、sensitivity99/220、slices25/150、tuned45/50；tuned随后由新的独立审计更新为46/50。不要误用较早45回退。
- ABDF最后分析：**35/60**、18组效应、零失败；实际父50656、子45720，bottomD0 R0 hot90 seed103。
- 压缩IR最后分析：**27/75**、27通过、26组效应；实际父54408、子48516，Path DWB1 uniform seed103。
- B3实际父47116，最后子56256 Deferred hot90 seed105、17544 SDE hot90 seed105、46412 Ring hot90 seed105；余下R0应由原父自然调度。
- 敏感性实际父15408、子45320，rho llc8 R0 seed101。
- B4实际父19648，`extended_scale_queue_bulk_state.json`仍等待真实live的B3父47116及completion；不能以等待或句柄超时为由重启。
- 最新CIM中审计临时进程47696/9888已随工具正常结束，不是长期worker。

这些只是本轮最后快照；下一轮要重查真实进程及终态，不以旧状态文件代替live证据。运行源码锁仍沿第十一版及此前各版：common/core/bulk/缓存/异质/组合、IR raw/compressed、AB策略/周期与它们绑定的proof均不可中途编辑。

## 文档与冻结校验

README已链接45/46和本衔接；`build_evaluation_draft.py`已加入45号证据检查和新的公平比较说明，并重新生成18号稿，full_chapter_complete仍false。最后只读冻结校验7包514文件passed。

本轮没有生成、改写或重新交付任何PDF，没有artifact marker操作。此前完成的核心/static、消融、IR周期、公开trace图继续使用，不重复导出。

## 下一步仍须保持完整目标

1. 优先收齐B3最后四次并完成调优主图/表；保留C1补充、B4规模切片、敏感性、ABDF和压缩IR的既定全批次。不要重复本轮已通过的有限检查来代替剩余性能数据。
2. 更新46号独立审计时使用实际完成收据，注意bulk runner有短暂中间receipt，必须等最终execution_revision后才记完成。
3. IR本地skip仍无安全准入。39–43的反例继续有效；需要解决条件转录分布，而非继续堆同类功能测试或把no-skip重命名为原生IR。
4. AB green容量归约、严格后台策略及DeadQ尚待实质推进；当前dummy-first周期不能充作完整原生AB结论。
5. 完整基线主动安全预算、资源计量边界和最终全目标逐项审计仍未完成。补充Path Z5不替代原有调优Path Z4主比较，也不自动把所有方法标为同完整保证。
