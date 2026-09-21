# IR集成有限前缀：已完成图表与可复算数据

本批120次运行已全部审计。24个配置各5次，形成40组条件效应；所有组均未触发预设追加重复门槛。结果可用于论文的有限窗口小块配置图，不能标成完整原生IR或稳态性能。

## 图表及数据

| 文件 | 内容 |
|---|---|
| `figures/ir_integrated_finite_gain.pdf`、同名SVG/PNG | 均匀/热点两种负载，桶容量布局×DWB开关四格；同时报告SDE对Path及Deferred，五次配对均值与95% t区间 |
| `figures/ir_integrated_finite_breakdown.pdf`、同名SVG/PNG | 非均匀桶+DWB开启；Path/Deferred/SDE每应用请求KiB，分为数据槽、nonce、桶头、认证、控制帧 |
| `tables/IR_DWB_120_runs.csv` | 全部120次记录，含配置、总字节、分项、RPC、前端计数、原始路径及SHA256 |
| `tables/IR_DWB_40_comparisons.csv` | 全部40组比较的分母、条件、均值、95%区间与统计来源hash |

N=4096，B=64字节；raw递归map后人口4369；前6层缓存、PLB8、LLC8组×2路。128次暖机/1024公共时隙，256次测量/2048公共时隙。包括dummy、递归map、维护、认证和最终ACK；终点允许dirty LLC驻留，没有持久化屏障承诺。数据槽含真实块和dummy，不是有效payload。

## 完成批次揭示的结论

- 非均匀桶：对Deferred减少19.10%–19.25%，对Path减少9.63%–9.80%。
- 均匀桶：对Deferred减少20.20%–20.36%，对Path减少13.75%–13.93%。
- Deferred的小块认证/头部成本可以高于Path。正文必须保留两个分母，并给出绝对字节，不能只选较大的百分比。
- 在相同公共时隙与完成请求数下，Path/Deferred的DWB开关总通信严格相同。DWB改变前台与空闲时隙的工作分配，不能直接称为总字节节省；SDE中有限随机路径差异产生的小幅正负变化完整保留。

60次更长周期窗口复核独立执行，结果见21号文档。它不会自动将本图升级为稳态结果，也不能将两个不同窗口的数据混成一个均值。

## 核验链

`ir_dwb_statistics.json`追溯120份执行收据。`verify_ir_finite_exports.py`逐行验证导出的原始数值与来源，并由每对原始执行总字节重新计算40组均值和95% t区间；检查每份PDF只有一页、含可提取文本和字体、没有光栅图像代替矢量图。

`results/ir_finite_exports_audit.json`记录数值核验；`results/ir_finite_visual_review.json`绑定当前PDF及Poppler渲染图hash，记录实际版面审阅。收益图横轴已缩短，消除了四组文字相互重叠；两张最终PDF均已逐图检查。

尚缺原生IR-Stash、压缩map跨时隙机制、完整归约及基线安全准入。功能和账单审计不替代这些证明。
