# IR完整周期图表与原始表

60/60正式运行，12格各5次。14组配对效应全部保留，95%区间为逐种子相对节省的Student-t区间；未触发预定义追加重复门槛。

图左侧区分Path和同维护策略Deferred两种分母，图右侧单独报告固定公共时隙下DWB开关。右轴单位也是百分比，但量程显著更小。
SDE对Deferred约19.195%–19.216%，对Path约9.750%–9.773%。DWB开关对Path/Deferred总字节严格为零；SDE两个区间均覆盖零，不作为确定通信收益。

完整配置与前端工作量见21号文档。图为 `output/pdf/completed_ir_periodic.pdf`；SVG、PNG及全部60行和14组效应在 `figures/completed_ir_periodic*`。

## 14组配对效应

| 轴 | 条件 | 比较 | n | 基线bytes/op | 组合bytes/op | 节省 | 95%区间 |
|---|---|---|---:|---:|---:|---:|---|
| backend | ['depth', False, 'hot90'] | path → sde | 5 | 59136.000000 | 53367.855469 | 9.754032% | [9.719890%, 9.788174%] |
| backend | ['depth', False, 'hot90'] | deferred → sde | 5 | 66048.000000 | 53367.855469 | 19.198378% | [19.167809%, 19.228947%] |
| backend | ['depth', False, 'uniform'] | path → sde | 5 | 59136.000000 | 53370.074479 | 9.750280% | [9.716181%, 9.784379%] |
| backend | ['depth', False, 'uniform'] | deferred → sde | 5 | 66048.000000 | 53370.074479 | 19.195018% | [19.164487%, 19.225549%] |
| backend | ['depth', True, 'hot90'] | path → sde | 5 | 59136.000000 | 53369.920833 | 9.750540% | [9.713479%, 9.787600%] |
| backend | ['depth', True, 'hot90'] | deferred → sde | 5 | 66048.000000 | 53369.920833 | 19.195251% | [19.162069%, 19.228433%] |
| backend | ['depth', True, 'uniform'] | path → sde | 5 | 59136.000000 | 53356.508854 | 9.773220% | [9.743031%, 9.803409%] |
| backend | ['depth', True, 'uniform'] | deferred → sde | 5 | 66048.000000 | 53356.508854 | 19.215557% | [19.188527%, 19.242587%] |
| dwb | ['depth', 'deferred', 'hot90'] | False → True | 5 | 66048.000000 | 66048.000000 | 0.000000% | [0.000000%, 0.000000%] |
| dwb | ['depth', 'deferred', 'uniform'] | False → True | 5 | 66048.000000 | 66048.000000 | 0.000000% | [0.000000%, 0.000000%] |
| dwb | ['depth', 'path', 'hot90'] | False → True | 5 | 59136.000000 | 59136.000000 | 0.000000% | [0.000000%, 0.000000%] |
| dwb | ['depth', 'path', 'uniform'] | False → True | 5 | 59136.000000 | 59136.000000 | 0.000000% | [0.000000%, 0.000000%] |
| dwb | ['depth', 'sde', 'hot90'] | False → True | 5 | 53367.855469 | 53369.920833 | -0.003876% | [-0.053776%, 0.046024%] |
| dwb | ['depth', 'sde', 'uniform'] | False → True | 5 | 53370.074479 | 53356.508854 | 0.025413% | [-0.015775%, 0.066601%] |

## 全部60行测量原始表

每行均测量6144个完成请求、49152个公共时隙。完整逐类字节、前端计数、spec、来源路径及SHA256保存在配套JSON，初始化/对齐/预热账单留在被绑定的原始收据中。

| ID | 总字节 | bytes/op | RPC | 前台回写 | DWB完成 | dummy槽 | dirty留存 |
|---|---:|---:|---:|---:|---:|---:|---:|
| IRPER_depth_path_dwb0_uniform_seed101 | 363331584 | 59136.000000 | 98304 | 3079 | 0 | 23607 | 10 |
| IRPER_depth_deferred_dwb0_uniform_seed101 | 405798912 | 66048.000000 | 131072 | 3079 | 0 | 23607 | 10 |
| IRPER_depth_sde_dwb0_uniform_seed101 | 327964248 | 53379.597656 | 131072 | 3079 | 0 | 23607 | 10 |
| IRPER_depth_path_dwb1_uniform_seed101 | 363331584 | 59136.000000 | 98304 | 0 | 3084 | 24556 | 6 |
| IRPER_depth_deferred_dwb1_uniform_seed101 | 405798912 | 66048.000000 | 131072 | 0 | 3084 | 24556 | 6 |
| IRPER_depth_sde_dwb1_uniform_seed101 | 327899832 | 53369.113281 | 131072 | 0 | 3084 | 24556 | 6 |
| IRPER_depth_path_dwb0_hot90_seed101 | 363331584 | 59136.000000 | 98304 | 2558 | 0 | 30292 | 10 |
| IRPER_depth_deferred_dwb0_hot90_seed101 | 405798912 | 66048.000000 | 131072 | 2558 | 0 | 30292 | 10 |
| IRPER_depth_sde_dwb0_hot90_seed101 | 327871224 | 53364.457031 | 131072 | 2558 | 0 | 30292 | 10 |
| IRPER_depth_path_dwb1_hot90_seed101 | 363331584 | 59136.000000 | 98304 | 0 | 2820 | 30426 | 4 |
| IRPER_depth_deferred_dwb1_hot90_seed101 | 405798912 | 66048.000000 | 131072 | 0 | 2820 | 30426 | 4 |
| IRPER_depth_sde_dwb1_hot90_seed101 | 327757408 | 53345.932292 | 131072 | 0 | 2820 | 30426 | 4 |
| IRPER_depth_path_dwb0_uniform_seed102 | 363331584 | 59136.000000 | 98304 | 3080 | 0 | 23592 | 8 |
| IRPER_depth_deferred_dwb0_uniform_seed102 | 405798912 | 66048.000000 | 131072 | 3080 | 0 | 23592 | 8 |
| IRPER_depth_sde_dwb0_uniform_seed102 | 327770840 | 53348.118490 | 131072 | 3080 | 0 | 23592 | 8 |
| IRPER_depth_path_dwb1_uniform_seed102 | 363331584 | 59136.000000 | 98304 | 0 | 3084 | 24554 | 4 |
| IRPER_depth_deferred_dwb1_uniform_seed102 | 405798912 | 66048.000000 | 131072 | 0 | 3084 | 24554 | 4 |
| IRPER_depth_sde_dwb1_uniform_seed102 | 327732672 | 53341.906250 | 131072 | 0 | 3084 | 24554 | 4 |
| IRPER_depth_path_dwb0_hot90_seed102 | 363331584 | 59136.000000 | 98304 | 2527 | 0 | 30375 | 10 |
| IRPER_depth_deferred_dwb0_hot90_seed102 | 405798912 | 66048.000000 | 131072 | 2527 | 0 | 30375 | 10 |
| IRPER_depth_sde_dwb0_hot90_seed102 | 327985016 | 53382.977865 | 131072 | 2527 | 0 | 30375 | 10 |
| IRPER_depth_path_dwb1_hot90_seed102 | 363331584 | 59136.000000 | 98304 | 0 | 2813 | 30360 | 5 |
| IRPER_depth_deferred_dwb1_hot90_seed102 | 405798912 | 66048.000000 | 131072 | 0 | 2813 | 30360 | 5 |
| IRPER_depth_sde_dwb1_hot90_seed102 | 327911456 | 53371.005208 | 131072 | 0 | 2813 | 30360 | 5 |
| IRPER_depth_path_dwb0_uniform_seed103 | 363331584 | 59136.000000 | 98304 | 3091 | 0 | 23673 | 6 |
| IRPER_depth_deferred_dwb0_uniform_seed103 | 405798912 | 66048.000000 | 131072 | 3091 | 0 | 23673 | 6 |
| IRPER_depth_sde_dwb0_uniform_seed103 | 327832344 | 53358.128906 | 131072 | 3091 | 0 | 23673 | 6 |
| IRPER_depth_path_dwb1_uniform_seed103 | 363331584 | 59136.000000 | 98304 | 0 | 3092 | 24676 | 3 |
| IRPER_depth_deferred_dwb1_uniform_seed103 | 405798912 | 66048.000000 | 131072 | 0 | 3092 | 24676 | 3 |
| IRPER_depth_sde_dwb1_uniform_seed103 | 327889376 | 53367.411458 | 131072 | 0 | 3092 | 24676 | 3 |
| IRPER_depth_path_dwb0_hot90_seed103 | 363331584 | 59136.000000 | 98304 | 2535 | 0 | 30368 | 8 |
| IRPER_depth_deferred_dwb0_hot90_seed103 | 405798912 | 66048.000000 | 131072 | 2535 | 0 | 30368 | 8 |
| IRPER_depth_sde_dwb0_hot90_seed103 | 327729312 | 53341.359375 | 131072 | 2535 | 0 | 30368 | 8 |
| IRPER_depth_path_dwb1_hot90_seed103 | 363331584 | 59136.000000 | 98304 | 0 | 2824 | 30292 | 6 |
| IRPER_depth_deferred_dwb1_hot90_seed103 | 405798912 | 66048.000000 | 131072 | 0 | 2824 | 30292 | 6 |
| IRPER_depth_sde_dwb1_hot90_seed103 | 327902104 | 53369.483073 | 131072 | 0 | 2824 | 30292 | 6 |
| IRPER_depth_path_dwb0_uniform_seed104 | 363331584 | 59136.000000 | 98304 | 3095 | 0 | 23572 | 9 |
| IRPER_depth_deferred_dwb0_uniform_seed104 | 405798912 | 66048.000000 | 131072 | 3095 | 0 | 23572 | 9 |
| IRPER_depth_sde_dwb0_uniform_seed104 | 327952344 | 53377.660156 | 131072 | 3095 | 0 | 23572 | 9 |
| IRPER_depth_path_dwb1_uniform_seed104 | 363331584 | 59136.000000 | 98304 | 0 | 3100 | 24545 | 6 |
| IRPER_depth_deferred_dwb1_uniform_seed104 | 405798912 | 66048.000000 | 131072 | 0 | 3100 | 24545 | 6 |
| IRPER_depth_sde_dwb1_uniform_seed104 | 327720256 | 53339.885417 | 131072 | 0 | 3100 | 24545 | 6 |
| IRPER_depth_path_dwb0_hot90_seed104 | 363331584 | 59136.000000 | 98304 | 2587 | 0 | 30236 | 10 |
| IRPER_depth_deferred_dwb0_hot90_seed104 | 405798912 | 66048.000000 | 131072 | 2587 | 0 | 30236 | 10 |
| IRPER_depth_sde_dwb0_hot90_seed104 | 327926640 | 53373.476562 | 131072 | 2587 | 0 | 30236 | 10 |
| IRPER_depth_path_dwb1_hot90_seed104 | 363331584 | 59136.000000 | 98304 | 0 | 2874 | 30237 | 5 |
| IRPER_depth_deferred_dwb1_hot90_seed104 | 405798912 | 66048.000000 | 131072 | 0 | 2874 | 30237 | 5 |
| IRPER_depth_sde_dwb1_hot90_seed104 | 328063056 | 53395.679688 | 131072 | 0 | 2874 | 30237 | 5 |
| IRPER_depth_path_dwb0_uniform_seed105 | 363331584 | 59136.000000 | 98304 | 3022 | 0 | 23842 | 11 |
| IRPER_depth_deferred_dwb0_uniform_seed105 | 405798912 | 66048.000000 | 131072 | 3022 | 0 | 23842 | 11 |
| IRPER_depth_sde_dwb0_uniform_seed105 | 328008912 | 53386.867188 | 131072 | 3022 | 0 | 23842 | 11 |
| IRPER_depth_path_dwb1_uniform_seed105 | 363331584 | 59136.000000 | 98304 | 0 | 3027 | 24729 | 5 |
| IRPER_depth_deferred_dwb1_uniform_seed105 | 405798912 | 66048.000000 | 131072 | 0 | 3027 | 24729 | 5 |
| IRPER_depth_sde_dwb1_uniform_seed105 | 327869816 | 53364.227865 | 131072 | 0 | 3027 | 24729 | 5 |
| IRPER_depth_path_dwb0_hot90_seed105 | 363331584 | 59136.000000 | 98304 | 2524 | 0 | 30552 | 9 |
| IRPER_depth_deferred_dwb0_hot90_seed105 | 405798912 | 66048.000000 | 131072 | 2524 | 0 | 30552 | 9 |
| IRPER_depth_sde_dwb0_hot90_seed105 | 327948328 | 53377.006510 | 131072 | 2524 | 0 | 30552 | 9 |
| IRPER_depth_path_dwb1_hot90_seed105 | 363331584 | 59136.000000 | 98304 | 0 | 2802 | 30539 | 6 |
| IRPER_depth_deferred_dwb1_hot90_seed105 | 405798912 | 66048.000000 | 131072 | 0 | 2802 | 30539 | 6 |
| IRPER_depth_sde_dwb1_hot90_seed105 | 327889944 | 53367.503906 | 131072 | 0 | 2802 | 30539 | 6 |

## 范围与审阅

实验包含异质桶、缓存前6层、raw递归位置表、PLB和LLC、DWB及填充流量。IR-Stash skip和压缩map未包含；不称完整原生IR、稳态、持久化屏障或网络延迟实验。
独立导出核验重新读取60份运行收据、重算14组均值/区间，检查图数据绑定及PDF矢量字体；版面审阅单独保存，不从数值检查自动推断。
