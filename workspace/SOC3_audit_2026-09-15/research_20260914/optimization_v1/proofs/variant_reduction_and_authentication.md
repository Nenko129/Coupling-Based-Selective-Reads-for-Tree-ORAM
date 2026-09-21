SOC3 优化变体：容量归约、融合认证与数值接口

本文件是 2026-09-11 冻结证明的显式扩展说明，不覆盖原文件。它保持原请求模型：固定且独立于 ORAM 随机性的逻辑历史，以及只根据正确 RAM 输出作适应选择的应用；单可信客户端串行执行，私有状态不可回滚，任何拒绝后 fail-stop。没有形式化证明助手验证，也不增加并发、崩溃恢复或本地计时安全承诺。

**容量参数的推广。** 原证明的 max-gap 始终为 m=2。本变体只接受 (Z,A)=(4,3)，或 R0 的 (7,6)。GC mask、bit-reversal eviction、immutable UID、leaf-retained stale shadow、leaf-to-root canonical placement 均保留。对后一组，scheduled eviction 每六次请求执行，仍服务每个 nonroot depth。

逐版本 actual/shadow depth 比较在同一组 Z,A 的两个系统之间进行。其归纳使用相同容量、UID 顺序及 eligibility；Z 的数值不必为 4。phase-local commutation 依赖 off-path hanging subtrees 的合法性不变和路径 pool 多重集合相等，同样不使用 Z=4 或 A=3 的特殊常数。服务间隔从三次改为六次，只改变公开 birth 时间表和 fresh 上界。

固定历史下，各版本独立 leaf marks 的定义不变。对叶桶，最近一次叶服务时每个逻辑地址至多有一个 current version，因此均值 ≤N/2^L≤A/2。对内部深度 d，两个 child 最近服务相隔 2^d 个 scheduled phases，相关 birth 数 ≤A·2^d，每个 mark 落入指定 child 的概率为 2^−(d+1)，故均值仍 ≤A/2。初始化通过普通请求执行并计入 Q，不假定免费稳态初始化。

exact-home field 到三类 overflow 的计数算子变为

    Phi_Z(L,R,p) = ((R0+R1+R2+L2+p−Z)_+, L0, L1).

每个坐标仍由非负和、坐标复制及 positive-part 构成；idcx 及 stop-loss 复合论证保留。独立 Poisson envelope 的 rate 为 A/2。于是 Z7/A6 所需的对象是三维联合 Phi_7、Poi(3)，不是把旧 Z4/Poi(1.5) 表重新标记。

root capacity 从 Z 改成 0 的同 field 差仍为 min(x,Z)≤Z。一次完成的请求边界，fresh births 至多 A−1。因此

    Pr[S(t)>R] ≤ H_(L+1)(R−delta),
    delta_SDE=A−1,   delta_R0=(A−1)+Z.

Z7/A6/R0 的 delta=12，Z4/A3 的两个 offsets 仍为 2、6。此式没有声称实际 R0 与实际 unrestricted Ring 的 stash 只差 Z。

递归层的地址由上一层逻辑地址和固定的 entries-per-block 决定，placement 的 leaf draws 使用 tree-separated PRF domains。各层可使用不同 B、Z、A；每层的公开 schedule、初始化计数和 failure bound 分别计算，最后作 union bound。值中存放的上层 leaf 不改变该层由地址历史确定的 birth/invalidation 时间表。这里沿用原报告的递归组合论证，不推广到读取服务器 transcript 后自适应选择下一逻辑查询的更强模型。

**新数值证书。** 数值代码保留原非负标量运算和三维 simplex 存储算法，仅将 Z、rate 和 Poisson seed 明确改为 7、3 和 exp(−3) 的有理数包围；同时要求 cutoff≥Z，以保证卷积索引合法。本轮计算 cap=280、height=24、cutoff=128。两个模式分别为 FE_UPWARD 与 nearest-plus-NextUp，保持 subnormal、禁止 fast-math/收缩，未归一化 PMF、未删除正概率状态。

exp(−3) 的种子来自 exp(3) 的 128 项正 Taylor 和及几何余项上界，再取倒数并向外转成 dyadics。保留部分的每个概率项向上包围；逸出质量及一阶矩仍按原未知预算递推。其推导只依赖非负性、F_new≤F_left+F_right+P 和指定 Poisson tail，适用于当前 Z、rate。每个 H(h,r) 取两个模式的 total upper 的较大者，并以 Fraction 进行配置预算比较。

两模式每份 6744 个端点。本轮另外以独立 Fraction 的 left triple × right triple × arrival 枚举验证 C=8、H=4、M=8 的全部 stop-loss 和未知预算，共 160 条不等式；1/4 线程输出逐位相同。两个浮点模式共享递归实现，有理数枚举只覆盖小域，数值证书的数学依据仍是非负上包围和未知矩预算论证。

**紧凑 header。** 每条 descriptor 保留 UID16、address8、leaf4、slot2，共 30 bytes。仅移除原来的 34-byte reserved padding；live bitmap 保持 8 bytes，secret 区仍按 32 bytes 对齐，公共字段保持 60 bytes，nonce16、tag64、frame36 不变。故 H_Z4=204，H_Z7=300。字段长度固定，不随 real 数或访问角色变化。

采用独立 SOC3 frame/version 和 PRF context，包括公开 compact/fused flags、tree 与全部配置参数；旧 SOC2 对象不能跨上下文使用。所有 header 仍先通过当前全局 root opening 验证，再解密并使用 descriptor。没有缩短 UID、版本计数或认证 tag。

**融合 neutral 和 logical read。** 对已经认证的 path view，以公共 count==S 决定 neutral 集合 E。每个 E 内桶请求 Z 个 unused slots，其他 selected 桶请求正常的一个 unused slot；请求按公开深度及物理 slot bitmap 编码。一个 READ_SLOTS frame 中可有不同的 subset 大小。所有局部 openings，包括 cover/padding slots，均验证成功后才开始 payload 解密。

E 内桶在本地执行原 neutral：保留完全相同的 current real 多重集合，不从 stash 填块，不推进 gamma；生成 fresh permutation、所有 Z+S 个 ciphertexts、local tags 和中间 header。随后执行原 logical target invalidation/cover consumption，count=1，used 标记所选新 slot，header v 再加一。中间 header seal 的 nonce 仍被消耗，但中间密文及 root 不上传。最终只作一次 selected-path WRITE，E 内桶携带 full data/local tags，其他桶仅写 header。

因此在 round boundary 上，去掉密文、slots 的随机排列和网络中间状态后，真实版本、UID、mapped leaf、所在深度及 stash 的转移等于原 neutral(s)+logical。不同桶的 neutral 互不搬运 real records；只要按正常逻辑失效移除目标，重排它们的本地顺序不影响该核心投影。每次事务随后执行相同的必要 scheduled eviction。

安全模拟在理想随机域中可以使用按语义事件索引的独立 random tapes。改变 draws 的调用顺序不会改变这些 tapes 的联合分布；回到实现时对所有有限空间 sampling 统一计入 modulo bias。E 由已公开 count 决定。旧 unused slots 的 Z-subset 与原 neutral 相同，fresh permutation 后的 consumed slot 对目标/cover 角色均有相同的均匀分布；它通过最终 used bitmap 公开。新 header 的固定长度加密隐藏剩余 real 集合。stash hit 也执行同样的 mixed request 和 full-write shape，不能因目标在哪里省略 E 内桶。

客户端读取时仍以旧 committed/working root 验证旧 data roots；本地中间 header 不被视作服务器已提交的 root。唯一写回的 bucket/global tags 由客户端以最终 header 和 data root 计算。服务器丢写、重放、损坏任一 required opening，分别沿用当前 root 检查及 fail-stop 处理；错误 acknowledgement 不允许安全重试或恢复旧状态。这说明批处理没有取消 pre-use validation，也没有引入服务器计算 keyed tags 的假设。

**密码学调用预算。** Gate 限制 B≤4096、L≤30、Z≤7、n≤13；最多 31 个桶/路径。一次 logical operation 至多对每个 selected 桶做一次 neutral，再做一次 scheduled path（为上界，即使实际间隔为 A）。每个桶最多读取 7 个 payload、重写 13 个 payload、生成不超过 27 个 local tags；每个 4096 B payload 的 stream 使用 64 次 PRF，header 使用至多 9 次，全球重建与更新各至多 31 个 nodes。

用每个桶 4096 次 PRF 包围全部读取、准备、两次 header seal、局部/global tags 和采样；两条各 31 桶的阶段再加递归 remap，远小于每层请求 2^22 次的 gate 预算。物理初始化每桶按 2^13 次包围。于是公开总调用上界为

    qF = 2^22 Σ_j Q_j + 2^13 Σ_j (2^(L_j+1)−1) + 2 Σ_j N_j < 2^96.

过量预算也覆盖 malformed response 在拒绝前的有界处理：字段数/长度来自客户端 Config 与 requested subset，surplus bytes 被拒绝，且无重试。nonce 分配及采样调用数小于该包围，nonce128、UID128、sequence128 不会在此 horizon 内耗尽。认证前的投机 I/O 未被引入。

沿用原模型的 variable-input 512-bit PRF 假设，但在以上新调用预算下明确要求每次 hybrid advantage≤2^−132。最终预算采用

    Adv ≤ 2·2^−132 + qF²/2^511 + 2·B_stash + qF·(max_j n_j)!/2^513.

对 n≤13 的配置使用至多 13!，不继续沿用旧的 9!。模型未将 HMAC-SHA-512 的研究性假设升级为经审计生产密码套件的承诺。

**计费接口。** 原 invoice_event 已按每桶 requested slot subset 的实际大小计费，也支持同一次 WRITE 中混合 full/header-only buckets，因此其字段恒等式不必改变。融合的期望公式从原计费中删除每次 neutral 的一个逻辑 data read、其 local witness、一个中间 header/bucket tag、depth+1 个中间 global tags，以及两笔 RPC 的 framing/control。

若 depth=d 的 neutral rate 为 eta_d，w1=E[one-slot witnesses]，则相对同 header 格式的原流程，每次顶层请求中的单层节省为

    Σ_d eta_d [W+H+(w1+d+2)·64+192].

程序使用各分项的有向 Decimal 加减，减法下端减上端、上端减下端。预期表包含全部 data/header/auth/control；认证成本没有被归入不可见的常数。额外执行了 2250 个不同 witness 形状的融合前后逐帧恒等式检查。

所有证明与数值结论只对应本变体目录的独立契约。原证据包的 hash/contract 不用于声称新实现已被旧契约认证。
