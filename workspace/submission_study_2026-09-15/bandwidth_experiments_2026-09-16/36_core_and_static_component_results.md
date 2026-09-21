# B1核心与静态IR/AB组件：完整重复审计

60次核心、40次AB静态组件、40次R480 IR静态组件全部完成。逐行核对独立答案摘要、运行源码、配置、完整字节分项、RPC序号和递归时钟；28个配置每格5次、18个比较均未触发追加重复门槛。

统计口径为测量阶段双向序列化字节/完成请求。初始化与暖机另列；不计TCP/TLS，不报告原型运行时间为延迟收益。核心均使用Z4/A3/S3，这不是双方分别调优后的比较。静态AB为Y0，无CB/DeadQ；静态IR无IR-Stash/DWB，不能替代完整组合结果。

| 家族/布局 | N/B | 负载 | 后端 | bytes/op均值 | RPC/op均值 |
|---|---|---|---|---:|---:|
| AB/depth | 4096/64 | uniform | r0 | 11,650.74 | 3.500 |
| AB/depth | 4096/4096 | uniform | r0 | 136,401.11 | 3.500 |
| AB/depth | 4096/64 | uniform | ring | 15,695.68 | 3.500 |
| AB/depth | 4096/4096 | uniform | ring | 184,194.91 | 3.500 |
| AB/uniform | 4096/64 | uniform | r0 | 11,567.74 | 3.500 |
| AB/uniform | 4096/4096 | uniform | r0 | 130,674.75 | 3.500 |
| AB/uniform | 4096/64 | uniform | ring | 15,388.86 | 3.500 |
| AB/uniform | 4096/4096 | uniform | ring | 171,895.66 | 3.500 |
| IR/depth | 4096/64 | uniform | deferred | 8,255.40 | 2.667 |
| IR/depth | 4096/4096 | uniform | deferred | 142,642.27 | 2.667 |
| IR/depth | 4096/64 | uniform | sde | 6,666.66 | 2.667 |
| IR/depth | 4096/4096 | uniform | sde | 111,933.75 | 2.667 |
| IR/uniform | 4096/64 | uniform | deferred | 9,577.95 | 2.667 |
| IR/uniform | 4096/4096 | uniform | deferred | 197,719.57 | 2.667 |
| IR/uniform | 4096/64 | uniform | sde | 7,638.22 | 2.667 |
| IR/uniform | 4096/4096 | uniform | sde | 152,431.42 | 2.667 |
| core/uniform | 16384/4096 | hot90 | deferred | 458,045.40 | 5.333 |
| core/uniform | 16384/4096 | uniform | deferred | 458,045.40 | 5.333 |
| core/uniform | 16384/4096 | hot90 | gc_ring | 328,815.28 | 8.000 |
| core/uniform | 16384/4096 | uniform | gc_ring | 328,789.59 | 8.000 |
| core/uniform | 16384/4096 | hot90 | path | 541,272.00 | 4.000 |
| core/uniform | 16384/4096 | uniform | path | 541,272.00 | 4.000 |
| core/uniform | 16384/4096 | hot90 | r0 | 307,162.10 | 8.000 |
| core/uniform | 16384/4096 | uniform | r0 | 307,356.26 | 8.000 |
| core/uniform | 16384/4096 | hot90 | ring | 418,668.20 | 8.000 |
| core/uniform | 16384/4096 | uniform | ring | 418,371.80 | 8.000 |
| core/uniform | 16384/4096 | hot90 | sde | 347,034.65 | 5.333 |
| core/uniform | 16384/4096 | uniform | sde | 347,515.59 | 5.333 |

| 家族/布局 | N/B | 负载 | 比较 | 字节减少 | 95%区间 | RPC减少 |
|---|---|---|---|---:|---|---:|
| AB/depth | 4096/64 | uniform | ring → r0 | 25.770% | [25.341%, 26.199%] | 0.000% |
| AB/depth | 4096/4096 | uniform | ring → r0 | 25.947% | [25.702%, 26.193%] | 0.000% |
| AB/uniform | 4096/64 | uniform | ring → r0 | 24.830% | [24.504%, 25.156%] | 0.000% |
| AB/uniform | 4096/4096 | uniform | ring → r0 | 23.980% | [23.628%, 24.332%] | 0.000% |
| IR/depth | 4096/64 | uniform | deferred → sde | 19.245% | [19.030%, 19.460%] | 0.000% |
| IR/depth | 4096/4096 | uniform | deferred → sde | 21.528% | [21.435%, 21.622%] | 0.000% |
| IR/uniform | 4096/64 | uniform | deferred → sde | 20.252% | [20.129%, 20.375%] | 0.000% |
| IR/uniform | 4096/4096 | uniform | deferred → sde | 22.905% | [22.729%, 23.082%] | 0.000% |
| core/uniform | 16384/4096 | hot90 | path → sde | 35.885% | [35.815%, 35.956%] | -33.337% |
| core/uniform | 16384/4096 | hot90 | deferred → sde | 24.236% | [24.153%, 24.319%] | 0.000% |
| core/uniform | 16384/4096 | hot90 | ring → gc_ring | 21.462% | [21.272%, 21.651%] | 0.000% |
| core/uniform | 16384/4096 | hot90 | ring → r0 | 26.634% | [26.471%, 26.796%] | 0.000% |
| core/uniform | 16384/4096 | hot90 | gc_ring → r0 | 6.585% | [6.468%, 6.702%] | 0.000% |
| core/uniform | 16384/4096 | uniform | path → sde | 35.796% | [35.769%, 35.824%] | -33.337% |
| core/uniform | 16384/4096 | uniform | deferred → sde | 24.131% | [24.098%, 24.163%] | 0.000% |
| core/uniform | 16384/4096 | uniform | ring → gc_ring | 21.412% | [21.298%, 21.527%] | 0.000% |
| core/uniform | 16384/4096 | uniform | ring → r0 | 26.535% | [26.405%, 26.665%] | 0.000% |
| core/uniform | 16384/4096 | uniform | gc_ring → r0 | 6.519% | [6.255%, 6.782%] | 0.000% |

IR静态异质布局在4KiB块下对Deferred约21.53%，在64B下约19.24%；因此“除ρ外均超过20%”仍不成立。块长度和是否包含系统机制都必须随数字报告。

原始140行及SHA256、28格绝对开销、18组逐种子效应和区间保存在 `results/core_components_complete_audit.json`。缺少的基线安全归约不因本批完成而自动补齐。
