# 调优主比较与经典Path补充对照：独立账单审计

主比较已审计50/50，补充对照10/10。未满5个配对种子的组保留实际n，不报告95%最终区间。主比较双方参数分别按预声明有限候选选择；Z5/R258仅为补充，不替换Z4主基线。

逐行独立重放输入版本并重算答案摘要，复算分项字节/RPC连续序号、递归时钟、空间对象及trace配对。这里只计应用层序列化通信，未计TCP/TLS，不作延迟改善或完整同安全保证声明。

| 组别 | 后端 | 负载 | n | 平均bytes/op | 平均RPC/op |
|---|---|---|---:|---:|---:|
| supplement | path | hot90 | 5 | 657,456.00 | 4.0000 |
| supplement | path | uniform | 5 | 657,456.00 | 4.0000 |
| tuned | deferred | hot90 | 5 | 446,997.06 | 5.3330 |
| tuned | deferred | uniform | 5 | 446,997.06 | 5.3330 |
| tuned | path | hot90 | 5 | 527,664.00 | 4.0000 |
| tuned | path | uniform | 5 | 527,664.00 | 4.0000 |
| tuned | r0 | hot90 | 5 | 253,302.41 | 6.9998 |
| tuned | r0 | uniform | 5 | 253,539.89 | 6.9998 |
| tuned | ring | hot90 | 5 | 339,520.46 | 6.9998 |
| tuned | ring | uniform | 5 | 339,710.71 | 6.9998 |
| tuned | sde | hot90 | 5 | 338,824.32 | 5.3330 |
| tuned | sde | uniform | 5 | 338,932.57 | 5.3330 |

| 基线组别 | 比较 | 负载 | 配对n | 平均字节减少 | 95%区间 |
|---|---|---|---:|---:|---|
| tuned | path → sde | uniform | 5 | 35.767% | [35.658%, 35.877%] |
| tuned | deferred → sde | uniform | 5 | 24.176% | [24.046%, 24.305%] |
| tuned | ring → r0 | uniform | 5 | 25.366% | [25.186%, 25.546%] |
| supplement | path → sde | uniform | 5 | 48.448% | [48.360%, 48.536%] |
| tuned | path → sde | hot90 | 5 | 35.788% | [35.682%, 35.893%] |
| tuned | deferred → sde | hot90 | 5 | 24.200% | [24.075%, 24.324%] |
| tuned | ring → r0 | hot90 | 5 | 25.394% | [25.157%, 25.631%] |
| supplement | path → sde | hot90 | 5 | 48.464% | [48.380%, 48.549%] |

当前完整组是否触发预定追加重复门槛：False。剩余格仍须完成，不能据局部完整组结束全部任务。

机器可读逐行与逐种子表见 `results/tuned_reference_independent_audit.json`，每个来源有SHA256。容量/证明口径见45号文档；缓存、XOR及其他参数族尚未穷尽，不作全局最优比较。
