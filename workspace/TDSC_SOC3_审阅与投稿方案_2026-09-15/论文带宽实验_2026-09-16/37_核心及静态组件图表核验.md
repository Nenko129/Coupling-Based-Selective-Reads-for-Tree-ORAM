# 核心与静态组件图表

两张图来自已完成并独立审计的140次运行。每个柱及其95%区间都绑定五个原始run；减少率先按种子配对，再求均值。

- 核心图：`output/pdf/completed_core_bandwidth.pdf`。左侧为6后端、两种负载的绝对总通信，右侧区分Path→SDE、Deferred→SDE、Ring→GC-Ring、Ring→R0、GC-Ring→R0。固定Z4/A3/S3，不用作分别调优主结果。
- 静态组件图：`output/pdf/completed_static_components.pdf`。IR/AB分面，64B与4KiB分组，均匀与逐层桶分开。IR按Deferred分母，AB按Ring分母；未纳入完整原生机制。

各图另有SVG和PNG；`figures/completed_core_components_data.json` 保存30组逐柱数值、原始ID、单位和置信区间。原始140行与28格绝对开销见36号文档对应审计收据。

核心图说明：同固定参数下，SDE对Path的改善包含维护策略改变；以Deferred为分母可更直接观察selective的增量。Ring→GC-Ring与GC-Ring→R0分开显示，避免将省根全部称为少读收益。

静态图说明：4KiB时数据流量占比上升，IR异质配置相对Deferred超过20%；64B同配置约19%。两种块长不能合并成“IR均超过20%”。AB图只说明静态dummy布局组合，不替代带CB与DeadQ的条件实验。

生成、数值审计、PDF嵌入字体与版面审阅分别记录。实际审阅状态以results中的core_components_exports_audit.json和core_components_visual_review.json为准。
