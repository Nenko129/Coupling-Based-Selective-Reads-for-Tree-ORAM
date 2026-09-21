# 执行衔接更新：第十四版

完整带宽证据目标仍active。本轮为progress，没有须用户解除的阻塞，不标complete或blocked。用户追问“除了ρ是否都可减少20%以上”，已按整体通信与不同分母纠正：Freecursive已测配置约22%–25%，IR异质布局约19.2%（Deferred分母）/9.8%（Path分母），AB静态组件约24%–26%但完整AB未验证，ρ整体约8%–12%。

## 本轮完成：Freecursive全部五组敏感性

- 新 `src/audit_free_sensitivity_completed.py` 完整选取预声明100个Free运行，加60个既有B64对照；没有更改协议源码、运行队列、输入或选择条件。
- 逐份核对源码身份、最终extended标记、两份等价执行证据、计划参数、几何/合法打包、每阶段账单分项、RPC连续性、时隙和缓存计数守恒、对象存储及声明的前端内存项。
- 独立重新生成10条地址/版本trace，按64B/4096B初始值与更新规则重算15组返回值摘要，共92160个返回值。初始值是address的8B编码加零，不是core的version0 SHAKE payload。
- `results/free_sensitivity_completed_audit.json`：160行来源，32格绝对通信/RPC/前端工作量/资源，16组selective效应，20组前端参数效应。均n5，没有触发追加重复条件。来源不绑定仍在变化的extended_statistics.json。
- **49号报告** `49_Freecursive敏感性完整结果.md`：已完成全部表格；尚未创建新PDF/SVG/CSV。32格资源在JSON中逐项保留，不把已列资源称为真实可信峰值。
- 独立 `src/verify_free_sensitivity_tables.py` 从160份原始账单重算32格、36组效应和36行Markdown数值，验证通过；结果 `results/free_sensitivity_tables_audit.json` 绑定最终报告、原始来源与审计器hash。
- `build_evaluation_draft.py`新增结果与来源核验；18号稿、README、带宽收益口径核对均更新。后者的IR周期旧进度已纠正为60/60，AB当前独立审计快照为40/60。
- 只读冻结核验7包514文件passed。

### 新结果与解释

64B压缩前端的PLB4/PLB32/β4三个切片：SDE减少21.804%–21.854%，R0减少24.452%–24.484%。4096B raw/compressed两个配置：SDE减少24.037%–24.083%，R0减少22.054%–22.090%。限于具名受限实现与有限窗口，不能称全部原生Freecursive或所有ORAM都超过20%。

PLB8→4使总字节增加约21.2%；PLB8→32减少约39.2%–39.3%，同时使用更多可信PLB资源。β14→4使测量平均group reset为283.8次，增加8335.8个后端时隙，总字节增加约91.1%；selective相对比例稳定不意味着绝对开销不变。

4096B两种map在暖机后均驻留PLB，测量均0次PLB miss、4096个Transfer；raw→compressed的Deferred差为精确0，其余三后端平均约−0.002%至−0.062%，区间包含0。保留负值，不声称存在额外压缩通信收益。B64→4096同时改变X和固定PLB条目数对应的字节预算，不是固定X/固定可信内存的单因素消融。

## 最新已审计计数

- calibration40/40，public80/80，tuned50/50。
- 全前端sensitivity155/220；本轮独立冻结其中100个Free，并复用60个基础对照。
- B4 slices36/150（25个B1复用＋11个新运行）。
- ABDF40/60，零失败；压缩IR36/75，36通过；C1经典Path4/10。
- 上述为不同审计调用的最后快照，后续继续按真实收据更新，不能猜后续完成数。

## 最后真实进程

| 批次 | 父PID | 子PID / 最后工作 |
|---|---:|---|
| sensitivity | 15408 | 20632 / SENS_rho_rho32_r0_seed104 |
| B4 bulk | 19648 | 50792 / B4_deferred_N4096_B4096_seed103 |
| ABDF | 50656 | 49160 / ABDF_bottom_d0_r0_uniform_seed104 |
| compressed IR | 54408 | 55292 / IRCM_depth_path_dwb0_uniform_seed104 |
| C1 Path Z5 | 46680 | 51608 / C1_path5_uniform_seed103 |

不要因旧工具session观察过期重启。B3已完成退出，不重启、不重新生成其PDF；此前PDF均已交付，本轮无新PDF、无PDF marker。

## 下一步与锁定边界

继续收齐ρ的LLC/ρ-cache/帧比例六组、C1、B4、ABDF和压缩IR；完成的整组再独立审计、制作论文表图。ρ的LLC8/128四十次已在总统计中收齐，可先作独立证据，完整120次仍需等待。Free的新表可在需要统一敏感性主图时引用，不要把其160份审计来源重复算作160次新实验。

所有第十三版及先前源码锁继续有效：common/core/组合/extended/bulk/缓存执行、IR raw/compressed和AB策略/周期及proof闭包不改；C1绑定的经典容量账本和其audit不改。新审计和文稿代码是独立增加。

IR skip的已知条件转录反例仍未修复；不能将no-skip主批或功能测试称为原生IR闭合。AB green容量归约、strict后台、DeadQ仍缺；不能将当前20%–22%过程结果冒称完整AB收益。经典基线的完整主动安全预算、公开寿命执行和真实可信峰值也未整体闭合。全目标最终审计仍未通过，不能因单批完成缩小范围。
