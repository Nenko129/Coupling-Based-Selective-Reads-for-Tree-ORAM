# 执行衔接更新：第十三版

完整目标继续active。本轮与上一轮均为progress：上一轮补经典基线检查并启动C1，本轮完成B3全部50次的独立审计、冻结、矢量主图和原始表，并核清有限窗口/周期期望差异。没有须用户解除的阻塞，不标complete或blocked。

## B3已完成，不要再启动或重复导出

- 实际B3父47116已退出，`results/formal_tuned_queue_completion.json`为passed。50个最终加密运行收据均通过独立答案摘要、分项账单、RPC序列、递归时钟和实际对象存储核对。
- `src/freeze_tuned_completed.py`生成不可变 `results/tuned_completed_snapshot.json`：50行、10格、6组效应，全部n5；无追加重复门槛触发。只包含B3，不依赖随后继续变化的C1进度JSON；不要因C1推进而重冻或重新导出主图。
- 冻结快照逐项复核入选参数确为原72个有限候选的选择。配置：Path/Deferred/SDE Z4/A3，Ring7/6/9，R0 7/6/6；map B256，R256，N16384/B4096，warmup2048/request4096。
- `src/render_completed_tuned.py` → **47号报告**、`output/pdf/completed_tuned_bandwidth.pdf`、同名SVG/PNG、`figures/completed_tuned_data.json`、`tables/tuned_50_runs.csv`、`tables/tuned_6_comparisons.csv`。
- 主图一页两面板：绝对KiB/request与明确分母的配对减少率。包括参数、五个种子、95% t区间、共同上限与不同实际存储、有限窗口/经验PathZ4/非全局最优/不声称延迟的标注。
- `src/verify_tuned_exports.py` → `results/tuned_exports_audit.json`：独立从原始字节重算16组图元、50+6行CSV、参数和收据哈希，验证一页矢量PDF与嵌入字体，passed。
- 最终PDF经Poppler 150dpi渲染至 `tmp/pdfs/completed_tuned_review-1.png`，实际通过view_image检查，无裁切、标签重叠或不可读脚注；`results/tuned_visual_review.json`状态visually_reviewed，绑定最终PDF/PNG和数值审计哈希。
- 创建前PDF技能marker已成功运行**一次，create / expected-output-count 1 / pdf**。本轮只有这一张新PDF；最终回复交付一次，后续不因普通续跑重复生成、重复交付或重复marker。

### 最终B3数据

| 比较 | uniform均值/95%区间 | hot90均值/95%区间 |
|---|---|---|
| Path→SDE | 35.767% / [35.658,35.877]% | 35.788% / [35.682,35.893]% |
| Deferred→SDE | 24.176% / [24.046,24.305]% | 24.200% / [24.075,24.324]% |
| Ring→R0 | 25.366% / [25.186,25.546]% | 25.394% / [25.157,25.631]% |

不将不同基线的百分比混用，也不把当前25.37%推广为所有规模或稳态。

## 新增有限窗口/模型核对

- `src/audit_tuned_model_window.py` → `results/tuned_model_window_audit.json`，**48号报告**。
- 50份原始收据、100行逐层时钟、10格绝对成本、6组配对/模型差异。数据层scheduled周期49152，计量t18432→22528，只4096次=1/12周期；map层周期768，覆盖16/3周期。均非整数周期。Path不采用scheduled周期，这些长度仅作参考。
- Ring完整周期期望341421.86 bytes/op；R0 257504.69，模型节省24.579%。本有限窗口实测多0.787/0.815个百分点，全部差异保留。
- R0实测对其模型约低1.54%–1.63%，Ring约低0.50%–0.56%；不直接判定模型错，也没有证明全部差异来自相位。
- 小N256/B64整周期校准0.15648%的误差不能外推到本规模/窗口。主文明确当前结果是具名有限窗口，五种子区间不包含换相位效应；稳态主张仍需额外覆盖。原实验计划未改变、未择优换窗口。

## 文档与校验

`build_evaluation_draft.py`已加入完整B3、最终PDF数值/视觉绑定及窗口审计；18号稿重新生成，仍full_chapter_complete=false。README链接47/48和本衔接。只读冻结核验7包514文件passed。

重新读取了AB源论文§V-B/C的DeadQ和动态S规则，确认首次扩张在一整轮驱逐后、空队列回退等源条件；本轮未实现新的DeadQ，也未将该阅读冒称组合闭合。此前IR skip反例、AB green/DeadQ、基线完整主动安全和峰值资源缺口仍在。

## 最后已审计快照

- tuned B3 **50/50**。
- 经典Path补充C1 **2/10**，独立审计仍为partial，完整B3状态不受其影响。
- calibration40/40、public80/80、sensitivity **135/220**。
- B4 slices **28/150**：含25个B1复用，新增完成3个；原B4依赖已自然解除。
- ABDF **38/60**，18组过程效应，零失败。
- 压缩IR **31/75**，31通过、26组过程效应。

这些只是本轮最后快照；续跑必须按真实进程和最终收据更新。

## 最后CIM确认的实际父子

| 批次 | 父PID | 最后实际子PID/工作 |
|---|---:|---|
| sensitivity | 15408 | 54412，SENS_rho_llc128_r0_seed104 |
| B4 bulk | 19648 | 43048，B4_ring_N4096_B4096_seed101 |
| ABDF | 50656 | 47408，ABDF_uniform_r0_uniform_seed104 |
| compressed IR | 54408 | 55440，IRCM_depth_deferred_dwb0_hot90_seed103 |
| C1 Path Z5 | 46680 | 31988，C1_path5_uniform_seed102 |

C1工具session19203由上一轮启动仍由原父推进；不要因句柄观察过期重启。B4完成回执为`extended_scale_queue_bulk_completion.json`，C1为`classical_reference_queue_bulk_completion.json`。上次CIM中的临时审计进程12596/47036已随调用结束，不是长期worker。

## 继续推进的重点

1. 已完成B3图表只引用，不重导。收集C1剩余、B4全部切片、Freecursive/ρ敏感性、ABDF和压缩IR，完整组再做最终表图。Freecursive五个敏感性配置很可能已全部完成，应先核实并按原始账单独立复核，而非重复已有基础批次。
2. IR-Stash条件转录修复仍有实质缺口，不能把no-skip或功能测试改称原生组合闭合；AB的green容量归约、严格后台和DeadQ仍须实质推进。
3. 经典基线账本目前只覆盖既定理想stash/成功前缀范围，完整主动安全预算、寿命执行限制和真实可信峰值还未整体闭合。
4. 不修改在跑的common/core/bulk/缓存/组合、IR raw/compressed、AB策略/周期及各自proof闭包。C1仍绑定上一轮的classical_stash_execution_ledger和其audit，不改写。只读冻结验证继续用verify_frozen_inputs.py。
5. 全目标最终审计尚未开始通过，不能因本次主图完成而缩小成只交付B3。没有实际延迟要求。
