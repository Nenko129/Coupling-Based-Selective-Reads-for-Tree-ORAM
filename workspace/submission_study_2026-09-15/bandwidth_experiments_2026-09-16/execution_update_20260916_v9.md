# 执行衔接更新：第九版

目标保持active。本轮为实质进展：两张核心/静态组件最终矢量图、全raw-map IR-Stash接口24组功能检查，以及**新的安全反例**。不是阻塞轮；没有缩小完整实验目标。

## 优先事项：新增skip适配未获安全准入

新 `check_ir_stash_transcript_projection.py` 已实际跑完384次精确小域加密执行，输出 `results/ir_stash_transcript_counterexample.json`，状态 **counterexample_confirmed**，不是安全passed。

L1/N2/Z1/A2/R16、根缓存、无组冲突、两块按UID贪心放置、公开初始化路径0、相同公共Transfer数。在“本地命中不remap＋独立均匀dummy”的当前适配中，请求0和1的下一OPEN叶分布分别(3/4,1/4)/(5/8,3/8)，TV=1/8。关闭skip的对照二者均均匀。观察者解析**真实远端帧**的叶字段，不读取私有metadata。两初始叶、dummy叶和fresh leaf穷举，三后端、两开关、两目标、两crypto keys共384执行。

39号文档给出四状态推导、代码绑定、限定及修复方向。**这针对当前适配，不是原生IR论文攻击，也不证明N4096目标配置具有相同TV。** 原文已重新在线核对§II-B/IV-C/IV-E，原文Path回填明确排除本次目标；本Transfer接纳/回填和UID排序不等价于原系统，必须继续对齐。

新IR-Stash所有功能checks保留但不提供安全准入；尚无正式性能worker导入这些新模块，因此原数据不用撤回。不得直接将这些原型的性能加入论文。需要修复命中/路径分布/fresh remap的联合过程，不能只增加R或样本、不能删掉检查来“闭合”；恢复全逻辑访问只能作控制，不能替代原生行为完成目标。既有无skip IRPER、压缩IR、Free/ρ/core等按原范围继续。

## 新全raw-map接口及检查

- `ir_stash_raw_maps.py` 的 StashRawMapsFront 扩展所有raw map层。F/S命中保留backend唯一canonical owner，临时LocalMap句柄直接读写；仅远端map进入PLB。父项更新和Transfer之间无yield，父PLB项pin保护；本地句柄不能在后续Transfer之后使用，不保存到PLB。
- `check_ir_stash_raw_maps.py` session57073已terminal exit0：24组（浅/深递归 × dedicated/indexed × Path/Deferred/SDE × DWB开关）。浅N64/X16/3层记录类型，深N96/X2/8层，PLB4；每组48请求/384或576时隙。全部raw map叶指向、唯一owner、LLC与答案oracle、账单及公共时钟通过。24组实际使用local map句柄，6个远端map认证失败和1过期句柄检查通过。
- 输出 `results/ir_stash_raw_maps_checks.json` 与38号文档。新模块未导入旧性能worker。压缩reset尚未接入；上述反例要求优先处理安全再考虑目标实测。新文件修改后须重新绑定相关checks，不能沿用旧source hash。

## 两张已完成图表

PDF skill已读；本轮marker create count2成功一次，**不要再次标记或重导既有PDF**。

- `output/pdf/completed_core_bandwidth.pdf`：60次B1，左侧6后端两负载绝对KiB/请求，右侧5种明示分母的配对收益。fixed Z4/A3/S3，不是调优结论。
- `output/pdf/completed_static_components.pdf`：80次静态IR/AB，64B/4KiB与均匀/逐层布局分开，不冒称原生完整机制。
- 各有SVG/PNG；`figures/completed_core_components_data.json`逐柱绑定30组数值/CI/原始run IDs。
- `render_completed_core.py`、`verify_core_exports.py`：从140个原始收据重算30柱及95%区间；2份PDF各1页、无栅格图、字体嵌入通过。37号说明和results/core_components_exports*.json等证据已保存。
- 初版柱数字相接、静态图legend较近，已错开数值标签并提高静态图上界。最终Poppler140dpi两张PNG已实际view_image审阅，无重叠/裁剪；`results/core_components_visual_review.json`绑定最终PDF/PNG和数值审计。
- 最终需按skill对两份PDF各给一次plain output citation；完成交付后下一轮不得无故再交付。

## 已确认的运行状态与审计快照

本轮实际进程清单确认：B3父47116、扩展15408、B4等待父19648、rawIR6200、ABDF50656、新压缩观察54408均live。没有重启任何旧失败队列。

- 最新一次分析：IRPER **53/60**；ABDF **12/60**、18效应、0失败；extended calibration40/40、public72/80、sensitivity71/220、slices25/150、tuned6/50。此为已审计快照，末次实际进程已有更多推进，需重新审计读取。
- 末次实际B3子15124/55900/41044在uniform seed102；AB子5248在bottomD0 Ring uniform seed102；IR子48612在Deferred DWBon hot90 seed105；扩展子45728在free_raw B4096 Ring seed104。
- 54408的实际状态waiting_for_live_raw_IR_batch dependency6200；75格压缩正式观测尚未启动。旧β4失败/观察修订仍按第七版，不可改spec或丢失败。
- B4父19648仍等47116结束。core22128此前已退出并有180/180completion，不重跑。

README、18号草稿生成器已更新：核心/静态图完成；全raw接口功能；skip反例和安全hold。草稿绑定反例文件并检查其checker hash。完整周期、B3/B4、前端敏感性、AB green/后台/DeadQ、经典基线执行归约、真实空间口径及最终全要求审计仍未完成。活跃worker的旧source锁按第七/八版继续，不因新增反例修改旧实现。
