# 图表草稿与引用边界

已生成PDF、SVG和PNG；每张图旁附JSON数据，`figures/figure_receipt.json` 记录输入及输出哈希。图的坐标、标签、脚注已查看PNG核对。最终论文图需在正式批次和必要审计结束后重生成。

## 有限调优的成本—存储图

`figures/finite_tuning_model.pdf` 展示72个公开候选的周期成本与序列化服务器对象空间，星号标示各方案的所选最低成本点。这里是解析模型；图内已明确标注MODEL ONLY。

英文图注草稿：Periodic communication and serialized server storage over a finite set of 72 configurations at N=16,384 and B=4,096 bytes. Stars indicate the minimum predicted communication for each scheme under the common resource ceilings. The search does not include XOR, tree-top caching, or heterogeneous parameters across recursive layers. These points are model predictions; baseline-specific lifetime bounds and true peak client memory are separate requirements.

当前选择的Ring为Z7/A6/S9，R0为Z7/A6/S6，两侧map块均256B；预测通信降低24.58%。该结果对应当前规模及有限集合，不能代替旧大规模点的21–23%，也不能称全局最优。相应50次实际配对运行已单独列入 `formal_tuned_plan.json`，尚未完成。

## 组合实验的过程图

`figures/composition_paired_progress.pdf` 展示已完成的Freecursive压缩组件及受限ρ组件，各柱标出实际配对种子数量。未满五次时不绘制置信区间，并在图顶标注PRELIMINARY。

英文图注草稿：Paired reductions in total serialized communication at N=4,096 and B=64 bytes for the implemented Freecursive and restricted rho components. Costs include ciphertext, headers, authentication, and framing. Each bar labels the number of completed paired runs; confidence intervals are omitted while fewer than five pairs are available. R0 includes root omission in addition to selective reading. The figure is an interim record, not a completed native-system evaluation or a latency result.

IR与AB不会以仅有的旧单种子样本混入这张组合主图。IR将在R480修订矩阵完成后加入，AB则以相同缓存与静态布局的正式配对加入；原生未实现组件继续明确列出。
