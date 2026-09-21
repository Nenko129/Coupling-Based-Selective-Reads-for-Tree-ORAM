# 执行衔接更新：第七版

目标保持active。前一轮为实质进展（压缩控制器24/4检查），本轮继续实质进展：压缩IR独立驱动/审计/75格计划及两个目标pilot、新的终点未完成证据和保留失败的观察队列；完整B2 45格独立审计与PDF/SVG图、Markdown全表。没有用户阻塞，不标complete/blocked。

## 新的IR压缩管线

新增源：run_ir_compressed_periodic.py、audit_ir_compressed.py、check_ir_compressed_runner.py、prepare_ir_compressed.py、start_ir_compressed_validation.py、dispatch_ir_compressed.py。运行源码未修改旧raw/AB/core的锁定闭包。
- 六组小域完整周期检查通过；12类损坏收据拒绝通过，另保留一个故意拥塞的固定窗口失败。收据results/ir_compressed_runner_checks.json。阶段6/48/10和控制器24/4旧证据保持通过。
- formal_ir_compressed_plan.json在目标pilot之前写定：60格主比较（β14）+15格β4/DWBon/hot90压力，全部X32/N4096/B64/L12/population4229/cache6/PLB8/LLC8×2/R480。初始化4229+对齐8059到12288；暖1536请求/12288槽，测6144/49152，最终t73728。输入和相同公开后端phase对应raw60格；raw→compressed改变X和编码，不是纯selective。所有spec不变。
- target pilot β14通过，bytes/op53388.662760416664，仅单seed901；β4在measurement终点完成6143/6144，work pending1、queue0、level0 parent122/group10/cursor12，20个子项与后续数据仍未完成。不是overflow。partial bill和全部时隙保留。不能用6144假分母报告完成请求性能。
- 旧validation session31428/PID32812与旧dispatcher session2217/PID7592均已terminal exit1。前者因目标β4未完成，后者因预期成功门槛收据未生成。不得重启，原计划和失败保留。
- 新增audit_ir_compressed_failure.py，审计clock/t/全账单/队列/完成数/reset守恒；8类损坏失败收据拒绝通过。失败记录无可独立核验的部分答案摘要，明确不用于正确完成请求的性能主张。
- ir_compressed_observation_amendment.json明确pilot后、formal前的结果处理修订：不改75个spec、W/R/输入/协议；β14目标与小域门槛通过。全部15个β4压力点继续执行；仅审计确认的窗口未完成作为单列观察结果继续，任何其他错误及主60格错误仍停止。原始失败不改passed；不足五个完整配对时不声称n5带宽结论。是保留全部参数而非删除失败配置。
- 新的dispatch_ir_compressed_observations.py实际session64402/PID54408，已核验存活，等待raw IR PID6200结束并读取其成功完成收据。尚无正式75格结果，不能写已经跑完/开始正式测量。它通过原start_ir_compressed_validation.execute复用相同实际运行与逐行审计，因此新旧source/helpers仍锁定。
- 新analyze_ir_compressed.py已实际运行：0/75，审计已有raw比较源；生成33号文档和results/ir_compressed_statistics.json。支持后端/DWB/β/packing比较及独立列出所有未完成，不补虚拟n。后续有结果后还需检查真实配对路径和图表。

## 完整B2交付

analyze_ablation.py已收齐45/45观测。新audit_completed_ablation.py逐一复核源码/加速修订、spec、独立SHAKE初始与更新payload答案摘要、账单分项/RPC、递归几何与初始化后时钟、measurement窗口和，重新计算9格均值及四格效应/顺序链，和原统计核对。
- 注意递归树j的初始化时钟是sum(configs[:j+1].N)，不是每树同N；这是独立审计代码中已修正的错误假设，不是执行结果错误。
- results/ablation_complete_audit.json passed，45观测/9格/10效应/5链项（含起终点）；追加重复门槛未触发。
- Z4/A3/S3：compact开启后的fusion字节0.840650% CI[0.5670,1.1143]、RPC15.505019%；Z7/A6/S6字节0.4021% CI[0.0469,0.7574]。
- 顺序小map→compact→fusion→Z/A/S及几何的字节减少15.404857%、2.051955%、0.840650%、16.203127%；RPC分别−2.016643%、−0.027711%、15.505019%、12.505722%。起终点直接配对字节31.150980%、RPC24.561177%。不是纯selective或对tuned Ring的收益。
- 34_R0完整消融结果.md含9格绝对开销、所有45行、完整字节/RPC区间、交互项与范围。不要把RPC节省当延迟实测。
- 新图output/pdf/completed_r0_ablation.pdf、figures/completed_r0_ablation.svg/png及柱数据JSON。数值独立verifier从原始账单重算16根柱/CI并检查PDF单页、矢量与嵌入字体。最终Poppler版面已view_image目视审阅，compact开关标签明确，无转义残留或裁剪。
- results/ablation_exports.json、ablation_exports_audit.json、ablation_visual_review.json均绑定最终hash；最后目视是compact标签版本。
- PDF marker本轮create count1已成功。不要再次标记或无故重新导出；最终交付该PDF时按skill使用一次plain output citation。此前calibration PDF仍不要重复交付。

## 其他真实进度

本轮末实际核验旧主进程22128/core、47116/B3、15408/扩展、19648/B4、6200/rawIR、50656/ABDF及54408/新观察队列存活。按状态/独立审计快照：
- core resumed156/180（状态读数，末尾B1种子105三个后端实际运行）；B3等待其结束，独立结果0/50。
- raw IR已独立审计40/60；实际子46208正在depth/deferred/DWBon/uniform/seed104。完成后新75格观察队列接续。
- ABDF目标六组全部通过，旧27740/46020已结束。实际父50656已生成60格计划并真实执行；独立审计4/60、4效应、0失败。状态可能继续推进，需重读实际。
- 扩展analyze_extended_results已跑：calibration40/40，public65/80，sensitivity64/220，slices25/150，tuned0/50。
- frozen只读verify_frozen_inputs.py本轮再次通过7包514文件。不要运行旧会改写包的validator。
- Freecursive/ρ240次、IR有限前缀120次和已交付XLSX、IR两图、校准图保持完成，无需重跑。

## 后续工作

1. 原矩阵运行/逐行审计与失败复核，完成主Core/B3/B4/公开/敏感性/ABDF/rawIR/压缩IR图表。新观察队列保留整个75格，不因β4失败缩小。
2. IR-Stash位置相关命中/组冲突及其安全归约；AB green完整归约、后台语义、DeadQ远端槽生命周期/认证/实际空间；经典基线执行归约与同寿命参照。均仍是目标内容。
3. 真正公平tuned主文、全部CPU/内存范围准确标注、最终表图与章节、要求逐项完成审计；用户暂不需要网络实测加速比。
4. 新增文件分析、文档、图表可编辑；所有被live consumer使用的driver/runtime/审计/门槛收据锁定。尤其54408已import旧start validator、audit_ir_compressed、failure auditor及新observer，不可运行中改写。所有老锁延续。

