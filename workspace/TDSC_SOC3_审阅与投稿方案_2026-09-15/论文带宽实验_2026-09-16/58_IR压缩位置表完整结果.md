# IR压缩位置表：完整75格观测与raw对照

预声明75格全部取得最终结果：63格完整完成，12格固定窗口未完成；复用60份已完成raw-map对照，总共135份来源。所有失败和pilot保留，pilot不进入正式均值。完整五次配对才报告性能区间，未完成组不以成功子集替代。

N4096/B64，压缩X32后人口4229，L12/A3/R480；异质Z=[4,4,4,4,4,4,2,2,2,3,3,4,4]，前六层缓存、PLB8、LLC8×2。主组β14包含DWB开/关、Uniform/Hot90和Path/Deferred/SDE；压力组β4固定DWB开、Hot90。

初始化4229个Transfer，8059槽对齐至12288；暖机12288槽/1536请求，测量49152槽/6144请求，最终t73728。计入每个公开空闲时隙，测量四个维护周期；dirty LLC和私有pending reset可留在终点，不追加不计费drain。Path使用等长参照窗口。

## 全部配置与完成率

| 组 / 负载 / DWB | 后端 | 完整运行 | bytes/request | RPC/request | reset槽均值 | dummy槽均值 |
|---|---|---:|---:|---:|---:|---:|
| main_beta14 / hot90 / 0 | deferred | 5/5 | 66,048.000 | 21.3333 | 0.0 | 33285.4 |
| main_beta14 / hot90 / 0 | path | 5/5 | 59,136.000 | 16.0000 | 0.0 | 33285.4 |
| main_beta14 / hot90 / 0 | sde | 5/5 | 53,366.627 | 21.3333 | 0.0 | 33285.4 |
| main_beta14 / hot90 / 1 | deferred | 5/5 | 66,048.000 | 21.3333 | 0.0 | 33250.4 |
| main_beta14 / hot90 / 1 | path | 5/5 | 59,136.000 | 16.0000 | 0.0 | 33250.4 |
| main_beta14 / hot90 / 1 | sde | 5/5 | 53,375.274 | 21.3333 | 0.0 | 33250.4 |
| main_beta14 / uniform / 0 | deferred | 5/5 | 66,048.000 | 21.3333 | 0.0 | 27821.6 |
| main_beta14 / uniform / 0 | path | 5/5 | 59,136.000 | 16.0000 | 0.0 | 27821.6 |
| main_beta14 / uniform / 0 | sde | 5/5 | 53,374.144 | 21.3333 | 0.0 | 27821.6 |
| main_beta14 / uniform / 1 | deferred | 5/5 | 66,048.000 | 21.3333 | 0.0 | 28552.8 |
| main_beta14 / uniform / 1 | path | 5/5 | 59,136.000 | 16.0000 | 0.0 | 28552.8 |
| main_beta14 / uniform / 1 | sde | 5/5 | 53,370.132 | 21.3333 | 0.0 | 28552.8 |
| reset_stress_beta4 / hot90 / 1 | deferred | 1/5 | 不报告成功子集均值 | — | — | — |
| reset_stress_beta4 / hot90 / 1 | path | 1/5 | 不报告成功子集均值 | — | — | — |
| reset_stress_beta4 / hot90 / 1 | sde | 1/5 | 不报告成功子集均值 | — | — | — |

## 同配置配对结果

| 因素 | 组 / 负载 / DWB | 比较 | 通信减少 | 95%区间 |
|---|---|---|---:|---|
| backend | main_beta14 / hot90 / 0 | path → sde | 9.7561% | [9.7186, 9.7936]% |
| backend | main_beta14 / hot90 / 0 | deferred → sde | 19.2002% | [19.1667, 19.2338]% |
| backend | main_beta14 / hot90 / 1 | path → sde | 9.7415% | [9.6916, 9.7914]% |
| backend | main_beta14 / hot90 / 1 | deferred → sde | 19.1871% | [19.1425, 19.2318]% |
| backend | main_beta14 / uniform / 0 | path → sde | 9.7434% | [9.6896, 9.7972]% |
| backend | main_beta14 / uniform / 0 | deferred → sde | 19.1889% | [19.1407, 19.2370]% |
| backend | main_beta14 / uniform / 1 | path → sde | 9.7502% | [9.6907, 9.8097]% |
| backend | main_beta14 / uniform / 1 | deferred → sde | 19.1949% | [19.1417, 19.2482]% |
| dwb | main_beta14 / uniform / 1 | path | 0.0000% | [0.0000, 0.0000]% |
| packing | main_beta14 / uniform / 0 | path | 0.0000% | [0.0000, 0.0000]% |
| packing | main_beta14 / uniform / 1 | path | 0.0000% | [0.0000, 0.0000]% |
| dwb | main_beta14 / uniform / 1 | deferred | 0.0000% | [0.0000, 0.0000]% |
| packing | main_beta14 / uniform / 0 | deferred | 0.0000% | [0.0000, 0.0000]% |
| packing | main_beta14 / uniform / 1 | deferred | 0.0000% | [0.0000, 0.0000]% |
| dwb | main_beta14 / uniform / 1 | sde | 0.0075% | [-0.0657, 0.0807]% |
| packing | main_beta14 / uniform / 0 | sde | -0.0076% | [-0.0675, 0.0522]% |
| packing | main_beta14 / uniform / 1 | sde | -0.0255% | [-0.1122, 0.0611]% |
| dwb | main_beta14 / hot90 / 1 | path | 0.0000% | [0.0000, 0.0000]% |
| packing | main_beta14 / hot90 / 0 | path | 0.0000% | [0.0000, 0.0000]% |
| packing | main_beta14 / hot90 / 1 | path | 0.0000% | [0.0000, 0.0000]% |
| dwb | main_beta14 / hot90 / 1 | deferred | 0.0000% | [0.0000, 0.0000]% |
| packing | main_beta14 / hot90 / 0 | deferred | 0.0000% | [0.0000, 0.0000]% |
| packing | main_beta14 / hot90 / 1 | deferred | 0.0000% | [0.0000, 0.0000]% |
| dwb | main_beta14 / hot90 / 1 | sde | -0.0162% | [-0.0390, 0.0066]% |
| packing | main_beta14 / hot90 / 0 | sde | 0.0023% | [-0.0489, 0.0535]% |
| packing | main_beta14 / hot90 / 1 | sde | -0.0100% | [-0.0692, 0.0491]% |

packing表示raw X16→compressed X32；beta表示β14→4；dwb表示关闭→开启。这些因素分别报告，不能将压缩、调度变化归为纯selective，也不能把百分比相加。负值保留。

预声明的31组比较中，26组有完整五对，5组因固定窗口未完成而不报告性能均值；追加重复门槛触发0组。

## 固定时隙为何限制压缩/DWB的带宽收益

相同树几何和公开时隙下，Path/Deferred每槽通信固定。少访问位置表、把前台dirty写回搬到后台、或者增加group reset，都可能只是改变有效工作与dummy的比例。因此前端计数改善不能自动解释为总字节节省。所有DWB/β对照的Path和Deferred总字节相等，raw/compressed主组也如此；SDE的有限差异需结合配对区间，不能把微小波动叫额外收益。

## 固定窗口未完成与pilot

β4目标pilot只完成6143/6144，启动前据此预先修订观测处理规则：保留全部15个压力格的完成率，只有已审计的窗口未完成允许继续收集；不改W、R、输入或协议。该pilot仍单独保存，不用正式结果覆盖。

| 正式ID | 阶段 | 完成/提交 | 公开时隙 | 全部计费字节 |
|---|---|---:|---:|---:|
| IRCM_B4_depth_path_dwb1_hot90_seed102 | warmup | 1535/1536 | 12288 | 90832896 |
| IRCM_B4_depth_deferred_dwb1_hot90_seed102 | warmup | 1535/1536 | 12288 | 101449728 |
| IRCM_B4_depth_sde_dwb1_hot90_seed102 | warmup | 1535/1536 | 12288 | 82008000 |
| IRCM_B4_depth_path_dwb1_hot90_seed103 | warmup | 1534/1536 | 12288 | 90832896 |
| IRCM_B4_depth_deferred_dwb1_hot90_seed103 | warmup | 1534/1536 | 12288 | 101449728 |
| IRCM_B4_depth_sde_dwb1_hot90_seed103 | warmup | 1534/1536 | 12288 | 81922096 |
| IRCM_B4_depth_path_dwb1_hot90_seed104 | warmup | 1531/1536 | 12288 | 90832896 |
| IRCM_B4_depth_deferred_dwb1_hot90_seed104 | warmup | 1531/1536 | 12288 | 101449728 |
| IRCM_B4_depth_sde_dwb1_hot90_seed104 | warmup | 1531/1536 | 12288 | 81899064 |
| IRCM_B4_depth_path_dwb1_hot90_seed105 | warmup | 1535/1536 | 12288 | 90832896 |
| IRCM_B4_depth_deferred_dwb1_hot90_seed105 | warmup | 1535/1536 | 12288 | 101449728 |
| IRCM_B4_depth_sde_dwb1_hot90_seed105 | warmup | 1535/1536 | 12288 | 82051944 |

## 资源、审计及主张边界

每份完整运行重新核对返回摘要、初始化/对齐/结束时钟、分项字节、RPC连续性、reset游标及slot守恒。对123份完整运行逐层重算服务器对象与可信前缀；另对12份未完成记录核查失败阶段、请求完成数、窗口及全部账单。PLB/LLC/stash/terminal和五个reset scalar字段单列。这些选定逻辑项不是并存ciphertext/decoded/write buffer/认证scratch的真实峰值。

本组仍不包含原生IR-Stash或PMMAC，不能复用被反例拒绝的skip适配来增强收益主张。R480数值模型只提供既定profile/population条件参照，不给该完整压缩控制器自适应归约，也不替代基线安全定理。完整周期、正确返回和五次重复不等于原生IR闭合或稳态。

完整结果为`results/ir_compressed_completed_snapshot.json`；复现入口`src/freeze_ir_compressed_completed.py`。33号动态报告和原始失败文件继续保留。
