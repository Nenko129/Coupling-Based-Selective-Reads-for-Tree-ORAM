# IR压缩位置表：完整周期实验与终点完成率

75个预定配置中，已审计75个结果：63个完整完成，12个固定窗口未完成。未完成配置仍列入75格；不能只对成功子集称完整五次重复。

主60格：depth×DWB关/开×Path/Deferred/SDE×uniform/hot90×5种子，β14。压力15格：同X32、β4、DWB开、hot90×三后端×5种子。N4096/B64、人口4229、L12/cache6/PLB8/LLC8×2/R480；初始化4229、对齐8059、暖机12288、测量49152时隙，最终t73728。

## 启动前的边界发现

同目标规模的β14 pilot完成全部请求。β4 pilot在测量末尾完成6143/6144，仍有一个前台请求、level0分组重置cursor12/32；未见stash overflow。所有49152时隙的账单保留，不追加不计费drain。它是独立pilot，不能混入正式五种子均值。原“两个pilot都成功才启动”门槛因此未通过，原启动器已退出。

结果处理修订在pilot之后、正式结果之前写入ir_compressed_observation_amendment.json。原75个spec、输入、W、R和协议实现均不变：β14继续采用完整完成准入；15个β4压力配置全部执行并保留完成率，只有审计确认的窗口未完成可继续收集后续配置，其余错误仍停止。该修订不是把失败改为通过。失败记录缺少独立部分答案摘要，因此不将其用于正确完成请求的性能结论。

| 轴 | 组 | 比较 | DWB | 负载 | 完整配对n/5 | 总字节减少 | 95%区间 |
|---|---|---|---|---|---:|---:|---|
| backend | main_beta14 | deferred->sde | False | hot90 | 5/5 | 19.200% | [19.167%, 19.234%] |
| backend | main_beta14 | deferred->sde | False | uniform | 5/5 | 19.189% | [19.141%, 19.237%] |
| backend | main_beta14 | deferred->sde | True | hot90 | 5/5 | 19.187% | [19.142%, 19.232%] |
| backend | main_beta14 | deferred->sde | True | uniform | 5/5 | 19.195% | [19.142%, 19.248%] |
| backend | main_beta14 | path->sde | False | hot90 | 5/5 | 9.756% | [9.719%, 9.794%] |
| backend | main_beta14 | path->sde | False | uniform | 5/5 | 9.743% | [9.690%, 9.797%] |
| backend | main_beta14 | path->sde | True | hot90 | 5/5 | 9.741% | [9.692%, 9.791%] |
| backend | main_beta14 | path->sde | True | uniform | 5/5 | 9.750% | [9.691%, 9.810%] |
| backend | reset_stress_beta4 | deferred->sde | True | hot90 | 1/5 | 19.190% | 待五次 |
| backend | reset_stress_beta4 | path->sde | True | hot90 | 1/5 | 9.745% | 待五次 |
| beta | beta14->beta4 | deferred | True | hot90 | 1/5 | 0.000% | 待五次 |
| beta | beta14->beta4 | path | True | hot90 | 1/5 | 0.000% | 待五次 |
| beta | beta14->beta4 | sde | True | hot90 | 1/5 | -0.011% | 待五次 |
| dwb | main_beta14 | deferred | True | hot90 | 5/5 | 0.000% | [0.000%, 0.000%] |
| dwb | main_beta14 | deferred | True | uniform | 5/5 | 0.000% | [0.000%, 0.000%] |
| dwb | main_beta14 | path | True | hot90 | 5/5 | 0.000% | [0.000%, 0.000%] |
| dwb | main_beta14 | path | True | uniform | 5/5 | 0.000% | [0.000%, 0.000%] |
| dwb | main_beta14 | sde | True | hot90 | 5/5 | -0.016% | [-0.039%, 0.007%] |
| dwb | main_beta14 | sde | True | uniform | 5/5 | 0.008% | [-0.066%, 0.081%] |
| packing | main_beta14 | deferred | False | hot90 | 5/5 | 0.000% | [0.000%, 0.000%] |
| packing | main_beta14 | deferred | False | uniform | 5/5 | 0.000% | [0.000%, 0.000%] |
| packing | main_beta14 | deferred | True | hot90 | 5/5 | 0.000% | [0.000%, 0.000%] |
| packing | main_beta14 | deferred | True | uniform | 5/5 | 0.000% | [0.000%, 0.000%] |
| packing | main_beta14 | path | False | hot90 | 5/5 | 0.000% | [0.000%, 0.000%] |
| packing | main_beta14 | path | False | uniform | 5/5 | 0.000% | [0.000%, 0.000%] |
| packing | main_beta14 | path | True | hot90 | 5/5 | 0.000% | [0.000%, 0.000%] |
| packing | main_beta14 | path | True | uniform | 5/5 | 0.000% | [0.000%, 0.000%] |
| packing | main_beta14 | sde | False | hot90 | 5/5 | 0.002% | [-0.049%, 0.054%] |
| packing | main_beta14 | sde | False | uniform | 5/5 | -0.008% | [-0.067%, 0.052%] |
| packing | main_beta14 | sde | True | hot90 | 5/5 | -0.010% | [-0.069%, 0.049%] |
| packing | main_beta14 | sde | True | uniform | 5/5 | -0.026% | [-0.112%, 0.061%] |

## 未完成窗口

| ID | 阶段 | 已完成/已提交请求 | 公共时隙 | 字节总量 |
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

固定时隙下，少做map工作可能只是多做dummy；同几何Path/Deferred的总通信应不变。压缩收益须同时报告前端工作量与实际字节。packing比较改变X和map编码，不能归为纯selective；β比较保持X32。

本实验不包含原生IR-Stash/PMMAC，不提供压缩前端完整自适应归约或新的容量证书，也没有稳态、真实峰值内存或延迟声明。正式数据尚未收齐时不补填预测值。
