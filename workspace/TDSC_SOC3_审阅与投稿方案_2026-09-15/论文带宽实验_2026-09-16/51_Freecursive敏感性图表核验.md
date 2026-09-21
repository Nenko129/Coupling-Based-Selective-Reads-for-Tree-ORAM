# Freecursive敏感性：论文矢量图与审计

49号报告的100次敏感性运行、60次既有对照已整理成一张双面板矢量图。没有新增或重复执行这些实验，也没有将60个对照计作新实验。

## 图的含义

- 左图：八个配置的SDE对Deferred、R0对Ring的配对总字节减少率。包括两种块长的raw/compressed map，以及64B Hot-90下PLB4/8/32和β4的切片；每个柱及区间均来自五个具名种子。
- 右图：固定64B压缩map和Hot-90，对PLB8/4/32以及β4配置分别给出四个后端的绝对KiB/request。PLB容量改变和group reset代价与selective收益分开。
- 计量包含认证、递归和所有维护的应用协议双向字节。块大小改变时合法X和固定条目数的PLB字节预算同时改变；不称固定X或固定可信字节预算消融。

五个新配置中，SDE减少21.804%–24.083%，R0减少22.054%–24.484%。PLB8→32单独使通信减少约39.2%–39.3%，但使用更多PLB空间；β14→4单独使通信增加约91.1%。不能把这些参数效应归功于selective，亦不能把相对比例稳定等同于绝对通信不变。

## 交付与复核

| 文件 | 内容 |
|---|---|
| output/pdf/completed_free_sensitivity.pdf | 最终一页矢量图 |
| figures/completed_free_sensitivity.svg | 可编辑矢量版本 |
| figures/completed_free_sensitivity.png | 预览 |
| figures/completed_free_sensitivity_data.json | 32组图元，绑定每组五个原始ID和原始单位 |
| results/free_sensitivity_completed_audit.json | 160份原始来源、32格与36组配对效应 |
| results/free_sensitivity_tables_audit.json | 原始账单到统计及Markdown表的独立核对 |
| results/free_sensitivity_exports_audit.json | 原始账单到32组图元、矢量和嵌入字体的独立核对 |
| results/free_sensitivity_visual_review.json | 最终PDF的150dpi渲染人工视觉审阅绑定 |

32组图元包括16个减少率柱和16个绝对通信柱。数值核验从原始measurement总字节重新计算五种子均值及95% Student-t区间，不将汇总摘要自洽当成来源核验。PDF只有一页，字体已嵌入，无栅格绘图对象；最终1888×986渲染经实际查看，未见裁切、文字重叠或脚注不可读。

范围仍是当前Freecursive-style前端与SOC3认证后端的有限窗口组合；未复现原生PMMAC、硬件控制器或真实可信峰值，不声称延迟提升、稳态或所有参数均优于基线。ρ的完整敏感性结果另行收齐，不能由本图替代。
