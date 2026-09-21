# 当前续跑入口（第五版，完整目标仍未完成）

上一目标回合为实质进展（完整模型校准和AB受控验证），当前回合也为实质进展：确认AB受控检查真实失败，复现请求饥饿，依据原文隔离实现dummy-first策略，完成新协议检查与目标诊断，搭建带前置门槛的新60格队列；另完成经典基线界的精确算术核对。没有用户依赖阻塞。不能把组件结果或新诊断当成全目标完成。

## 经真实进程核验的运行入口

| 任务 | session | 父PID | 本轮末最近快照 |
|---|---|---:|---|
| 核心/B2/静态组件 | 42094 | 22128 | 至少131/180，仍有实际worker |
| B3有限双方调优 | 90409 | 47116 | 等22128后启动50次 |
| 校准/公开trace/敏感性 | 82050 | 15408 | 小队列至少150/340；最新审计校准40/40、公开56/80、敏感性55/220 |
| B4规模bulk | 93513 | 19648 | 等47116；最新审计20/150（含B1引用） |
| IR周期复核 | 29903 | 6200 | 已审计27/60；可因内存门槛暂等 |
| **dummy-first六组目标验证** | **26227** | **27740** | 已越过诊断门槛；实际检查子进程46020，uniform/Ring与GC-Ring两组通过 |
| **dummy-first后续60格队列** | **98224** | **50656** | 等实际27740结束，再严格核验证据并生成计划/派发 |

以上是快照，下一轮必须重查真实进程或session。内存1.5GiB门槛等待不是失败，不能因一次观察超时重跑。源文件及检查收据在活跃进程期间锁定。

## 明确已终止的旧AB运行

1. 原ABPER60格的session59000：首组连续admit初始化溢出；全部旧计划/源/日志/失败保留，0个正式测量。
2. 无控制器的paced读取检查session94948/PID41532：uniform三组通过，bottomD0/Ring在直接连续读取中溢出。`ab_paced_uncontrolled_failure_observation.json`保留具体阶段，不改写成加载失败。
3. paced受控检查session16972/PID49784：uniform Ring/GC-Ring/R0通过，峰值108/35/45；bottomD0/Ring在固定65536槽未完成4096个请求。失败是完成条件拒绝，不是stash溢出。`ab_paced_controlled_failure.json`保存记录。
4. 旧依赖启动器session9280/PID44212已失败终止；没有生成/启动ABPACED正式60格，不能把它写成仍在等待。

## 已完成的选择策略诊断

`diagnose_ab_selection.py` session85818/PID51452已成功完成两种策略诊断。固定N4096/B64/L11/pop4369/C5/A5/Y4/R500/底三层D0/cache6/PLB8/LLC8×2/H48/L32，种子5101。加载每A槽一个admit，21845槽；请求间隔8，读取所有4096条，固定65536槽。没有改大R、减小负载或延长窗口。

| 策略 | 加载后stash | 加载/全程边界峰值 | 完成请求 | 后台时隙 | 后台green搬出 |
|---|---:|---:|---:|---:|---:|
| 原全未读槽均匀选择 | 180 | 236/236 | 0/4096 | 65536 | 316796 |
| 新dummy-first | 0 | 7/11 | 4096/4096 | 0 | 0 |

两者固定窗口总通信分别643.302/643.103MiB；旧组分母为零，不能拿4096当已完成请求计算bytes/op。新组在第32768槽前已完成全部读回，仍补齐公开65536槽。此为一个种子的协议诊断，不是正式性能比较，也不是容量尾界。

新选择规则优先目标，其次未读dummy，最后才在G<Y时允许green。AB §III-C描述dummy耗尽后green；String §IV-A允许选择dummy或green，因此修订是显式选择策略，不是作者代码。满真实D0桶仍可能需要green，不称strict-dummy-only。局部可交换条件下取样仍均匀；完整自适应模拟尚缺。

新源独立于旧CB：`ab_dummy_first_policy.py`、生成的`ab_dummy_first_fusion.py`、`ab_dummy_first_runtime.py`。后者的加密上下文显式加入策略标识，沿用原配置大小/认证/融合/nonce/ACK后提交。所有对比后端都用同一新策略。

已通过：

- `ab_dummy_first_checks.json`：24功能配置、2658精确局部分布（80零cover）、3主动失败点。
- `ab_dummy_first_frontend_checks.json`：12组raw递归/LLC/压力检查，H2/L1测试实际触发后台；正确答案与有用迁移序列一致。它不声明新策略压缩map/DWB已实现。
- `ab_dummy_first_periodic_checks.json`：6小域完整周期执行+7损坏证据拒绝，含策略身份篡改。所有记录已落盘，审计器增加plan→frontend检查hash绑定后只重新审计已有行，没有重跑ORAM。
- `ab_selection_diagnostic_audit.json`：两条诊断的来源/账单/时钟/工作量核对。诊断没有独立返回值摘要，不能写成外部答案摘要复算；执行器内部逐项比对真实返回值。

`30_AB_CB选择策略与完成率诊断.md`是可读表。生成器检查收据绑定新规则、源与检查文件。

## 新ABDF正式队列的门槛与文件

实际46020执行`check_ab_dummy_first_controlled.py`，uniform/D0×Ring/GC-Ring/R0六组，每组4096读回/65536槽；全部通过才生成`ab_dummy_first_controlled_checks.json`。uniform/Ring已通过，加载峰5、全程峰6、后台0；uniform/GC-Ring也已通过，全程峰4。其余必须以实际输出为准。

实际50656执行`start_ab_dummy_first_batch.py --dependency-pid 27740`。六组验证父进程结束后，`prepare_ab_dummy_first_periodic.py`逐项检查目标规模结果、6+7驱动检查、诊断和源身份，才生成`ab_dummy_first_periodic_plan.json`。新60格使用ABDF_及独立结果目录。当前尚未声称计划已生成/主批次已开始。

随后`dispatch_ab_dummy_first_periodic.py`单worker、1.5GiB可用内存门槛，逐行经过`audit_ab_dummy_first.py`审计；该审计器另绑定策略、前端proof及原公共审计器的配置/时钟/答案摘要/账单检查。原audit_ab_cb.py未再改变。任何错误停止并保留日志，不静默重试。

周期驱动为`run_ab_dummy_first_periodic.py`，与旧paced相比只改运行绑定、proof来源、策略标签及范围描述。所有后端初始化21845槽，对齐8875至30720，暖机10240，测量40960，最终81920；应用Q和输入、C/A/Y/D/R及H48/L32不变。

新分析入口`analyze_ab_dummy_first_periodic.py`只能在新计划存在后运行，生成31号文档/新统计/表；不要调用旧--paced模式代替。`ab_dummy_first_batch_build.json`的4组base/output hash本轮末已逐个核对一致。旧25号文档只保留原计划；后续状态以27/30为准。

## 已完成的校准及本轮统计更新

`completed_model_calibration.pdf/svg/png`、40行原始CSV、8组汇总CSV、26号文档均已完成。8组×5、N256/B64；模型平均偏差最大绝对值0.15648%，八组95%区间覆盖零。数值和最终PDF渲染审阅均通过；本轮再检查PDF/数值审计/visual收据hash一致。PDF marker此前已成功create count1，**不要再次调用或重生成该PDF**。若交付，用PDF skill规定的plain output citation。

本轮末独立分析：IR完整周期27/60；公开56/80、敏感性55/220、B4引用/运行20/150、B3 0/50。B2共44/45观察，Z7/A6四格已n5，fusion在compact开启后的均值约0.4021%，95%区间[0.0469%,0.7574%]；Z4族尚缺最后alias，不能说全部B2完成。13号文档动态保存实际n。

Freecursive/ρ240次及IR有限前缀120次、已有XLSX/两张IR图保持完成，不需要再跑。完整方法、证明边界、来源记录已汇入18号章节草稿。原七个冻结包514文件本轮只读核对通过。

## 新增经典基线精确算术

`29_基线容量定理与参数核对.md`、`baseline_capacity_arithmetic.json`与独立audit已完成。读取并渲染原Path PDF第11页定理5.1、Ring第10页§4.3；原PDF和页图hash绑定。

Ring设rho=A/(2Z)，beta=4*exp(Z-A/2)*rho^Z。用64阶有理Taylor+几何余项得上界，独立核验用96阶。Z4/A3与Z7/A6在经典定理几何前提下R256满足每树2^96次、stash预算2^-128；Z5/A5不满足该界q>0。

Path经典界14*(3/5)^R只覆盖Z5、L=ceil(log2N)，不能套当前Z4。R256不足以用该界达到上述寿命预算；单树至少R310，16树保守示例R315。后者不是实际递归层数，也不含认证/PRF失败预算。

**这只是经典界的精确参数核对，不是当前执行协议的安全准入。** 尚须绑定初始化、维护时刻/中间边界、放置顺序、递归及cache自适应、fusion占用投影。不能直接给Deferred/CB/异质IR套Ring界。应保留较强经验Z4基线，并补有证明的Z5参照/更强适用界，不能宣称全部同安全强度已闭合。

## 活跃执行闭包锁定

沿用第四版所有core/IR执行源及冻结来源的锁定；不要重写`ir_dwb_controller_checks.json`和原`ab_cb_frontend_checks.json`。

新增锁定：`ab_dummy_first_runtime.py`、policy/fusion、`ab_paced_frontend.py`、原ab_cb_runtime/controller/cb_oram/cb_transfer及它们引用的全部源；`check_ab_dummy_first_controlled.py`及其验证计划；新frontend/engine/periodic检查收据；新周期驱动、prepare/dispatch/audit与两级启动器。当前50656已import prepare/dispatch，**不要修改它们或重新执行生成器**。

独立报告/章节/基线算术可以继续处理，但任何源码或检查证据变化都必须先确认对应进程终止及其结果绑定。

## 全目标仍需推进

1. 完成真实队列及新ABDF门槛；若失败，保留并分析实际原因，不能缩小目标或只留成功后端。
2. IR-Stash位置相关命中/冲突与压缩map跨时隙DWB；AB完整green归约、后台安全语义和DeadQ远端槽生命周期/认证/实际空间。这些仍需真正研究和实现。
3. 补经典基线执行归约和同寿命参照；完成全部核心/调优/消融/规模/公开trace统计、追加重复门槛及最终图表。
4. 最终全要求逐项审计、独立复现与完整章节；用户未要求网络实测加速比，不以延迟实验为前置条件。目标保持active。
