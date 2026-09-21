# 运行衔接（2026-09-16）

最新任务范围以用户重新澄清为准：选择读思想的有限组合，不再要求把SOC3所有机制或原生IR-Stash、CB/DeadQ全部实现。无Codex goal；不要根据旧检查点的“active goal”文字重新创建目标。

## 当前后台执行

- 新最小组合正式dispatcher PID 52544，计划120条。完成9条后的快照已打包；后续查看 results/queue_state.json 和 results/formal，以实际收据为准。
- 新批尾部分析/出图/打包进程 PID 42464，等待同一实验流水线结束；失败或dispatcher退出时写 results/finalization.json，不自动换种子或丢掉失败。
- 原B4尺度dispatcher PID 19648继续运行；其状态在上级论文带宽实验的 results/extended_scale_queue_bulk_state.json。不要重复启动、跳过内存门槛或修改其源码。
- 原IR guard PID55976的30条已完成，分析器审计30/30、0失败；61号报告已更新，不再当作未完成批重启。

这是正在执行的本地实验程序，不是创建了应用里的定时任务。不要重复启动formal dispatcher，否则会产生重复写入/资源竞争。

## 已锁定的内容

新 source_lock.json 绑定六个执行/检查/计划文件以及复用引擎；其中 src/minimal_runtime.py、run_minimal.py、run_frontend_minimal.py、check_minimal_contract.py、prepare_matrix.py、dispatch.py 在正式批运行期间不能改。复用的旧引擎、前端和冻结包同样不能改。分析器/文档在tools及编号报告中独立维护，不会使运行中的源码身份失效。

Freecursive/ρ本轮只运行Deferred/SDE两种后端；已有Transfer的Ring分支要求fusion，不能在这些前端上凭当前命令行声明支持unfused Ring。AB的unfused Ring/GC-Ring使用另外的静态树实现，已经实测。未来增加前端Ring时需另建受检版本和新计划，不修改正在跑的源文件。

## 后续必要工作

1. 完成120条正式收据；只有配对两侧都完成才进入统计。精度触发追加规则时另冻结增补计划，不替换原5种子。
2. 查看自动尾部阶段的 finalization.json、figure_status.json；检查8个主配对单元均完整，以及IR/AB的同放置/布局对照。
3. 复查正式图的可读性，核对图、正文、收据数值一致。预实验PILOT图不能改标签当成正式图。
4. 如果报告/工具发生改变后重新打包，需要保留zip哈希与审阅记录对应关系。portable_bundle_check.json目前绑定具体快照的zip哈希；未来新增数据后的zip不能冒称是同一个已复跑归档。
5. Freecursive/ρ公开长度/时隙泄漏范围、IR-Alloc/AB-static的受限宿主命名要保留在论文正文。若改成端到端强隐私、完整原生系统、网络延迟或真实可信峰值主张，重新增加对应证明/测量义务。

旧的研究进展完整报告保持原截止时刻，不覆盖。新材料在本目录；没有更改旧证书、失败记录或SOC3已冻结源文件。
