# Φ7 / Poi(3) 数值证书的独立复核规则

可信计算对象是联合分布 `p_h(a,b,c)`，a+b+c≤C，而不是三个独立 marginal。生产 kernel 是随包原样保留的 `ghost_z7a6.cpp`，C=280、M=128、h≤24；它存储两个 simplex arrays，共 3,737,581 个状态/数组。两种浮点模式共享代码，不称作两套独立算法。

## 1. 种子的有理数依据

令 T=Σ_(k=0)^128 3^k/k!，u=3^129/129!。其后每项比不超过 3/130，因此 `T < exp(3) < T+u/(1−3/130)`，反转得到 exp(−3) 的严格有理区间。独立审计器从整数 3、128 重新计算两个 Fraction，而不是信任 seed JSON 的 numerator/denominator；再核对 JSON 与 header 中 binary64 下/上界包含该区间。seed 上界为 `0x1.97db0ccceb0afp-5`。Poi 概率上界递推 `p_k=p_(k−1)·3/k`，不使用 exp(−3/2)。

对截断 P>M：`τ≤p_(M+1)(M+2)/(M+2−3)`，`tP≤3 p_M (M+1)/(M+1−3)`。guard 要求 M≥7，从而分母正、pre[0..7] 有合法来源；测试 M=6 必须拒绝。

## 2. 未归一化联合 PMF 与 cap exit

p 是 good 子概率 PMF 的逐项上包络。上包络的总质量可以略大于1，不能归一化。令 f(s)=Σ_(a+b+c=s)p(a,b,c)，T 为独立右子树总量与截断 P 的 convolution。

左 tuple `(a,b,c)` 的输出为 `(max(T+c−7,0),a,b)`。保留所有输出 d+a+b≤C：d=0 时累加 T≤7−c，d>0 时使用 T[d+7−c]；所有 (a,b,c) 相关性均保留。只把**右** subtree 压成总量 marginal 合法，因为 Φ 只通过 sum(R) 使用它；不能把左侧压成总量后试图恢复 L0/L1/L2。

设左总量 s=a+b+c。由于输入 retained 时 a+b≤C，输出超过 C 必然处在正部分支，且精确等价于 `T≥C+7−s+1`；此时总输出 F=s+T−7。置 u=C+7−s+1，

`ep=Σ_s f(s) Pr_trunc[T≥u]`，
`em=Σ_s f(s) ((C+1)Pr_trunc[T≥u]+E_trunc[(T−u)+])`。

后缀和只有非负加法。这里减的是7、cap判定是输出三状态总和，不是单个 U0。

## 3. unknown probability / first moment

令 δ 为未记录事件的概率上界、m 为其 F first moment 上界，μ=Σ_s s f(s)+m 是完整总均值上界。输出总量≤F_left+F_right+P。

左子 bad 贡献至多 `m+(μ+3)δ`，右子同理；Poisson tail 贡献至多 `2μτ+tP`；双方 retained 且 arrival retained 的 cap exit 贡献 em。因此

`δ'=2δ+τ+ep`，
`m'=2m+2(μ+3)δ+2μτ+tP+em`。

右式 δ、m、μ 均来自**上一个** level；不能用更新后的 δ，也不能把 μ 中 m 漏掉。率 3 在此处和 tP 中同样必须修改。最终 `H_h(r)≤Σ p_h(u)(|u|−r)+ + m_h`，r≥0。不能以 `m_upper−r·δ_upper` 冒充更紧上界。

## 4. 算术与独立检查

FE_UPWARD 与 nearest+逐正运算 NextUp 都关闭 FTZ/DAZ、fast-math、FMA contraction，每个 OpenMP worker 设定舍入；检查 one+tiny 和最小 subnormal/2。输出以 hex binary64 用 Fraction 精确读取；decimal 仅展示。

新审计器不只读取 PASS 字段：

* 从 seed 源码/JSON 重算严格有理区间与 Poisson tail；读取并核对全部 h×r 点及 levels 的 ep/em/δ/m。
* 对 C=8,H=4,M=8，以 Python Fraction 对左 tuple×右 tuple×arrival 做独立直接枚举；保留并比较**每个三元 tuple**，以及 mass、mean、ep、em、δ、m、所有 known/total stop-loss。该域第4层存在非零 cap exit，且一开始已有非零 Poisson tail，因此同时检验两类误差传播。
* 仅为输出 small-domain joint witness，对生产 C++ 源添加写 CSV 的观察语句；机械还原后必须与原源字节对应，不改变递推。重新编译观察版本与原版本，在同参数下 stop-loss/level 数值 endpoints 必须一致。witness 包含 simplex 所有 tuple，包括零值，不以 positive-state cutoff 代替完整域。
* 对 λ=3/2、Z=4、first-moment 中率3误写、漏算/误算 cap-exit、只保留 marginal 等错误分别设置反例/变异检查。两浮点模式必须包住独立 Fraction oracle，不能用相互接近代替正确性。
* 全量重编译原 kernel，重新产生两模式 C280/H24/M128 网格；校验完整 domain、seed、metadata、有限性和逐点包络。记录与原网格的 byte equality，但只有同工具链重现才要求完全相同；另一工具链差异必须重新审阅其算术边界，不能以 decimal 摘要自洽放行。

## 5. 使用边界和 receipt 的含义

当前新 grid 的 domain 严格为 `{1..24}×{0..280}`；Z4 h≤31 证书单独保留。gate 以 `(Z,A)` 选 grid，以 h=L+1、r=R−(A−1+Z) 取 R0 点，用 exact dyadic Fractions 求 lifetime union bound。h=25 或 r=281 的非平凡 Z7 请求必须拒绝；R≥N 的 deterministic count 分支明确标注，无 grid 推广含义。

manifest/contract 只证明文件身份，receipt 证明指定源码/参数/工具链产生了指定输出；不独立证明 reduction、PRF 安全或编译器无缺陷。审计者需要阅读 01/02 的数学义务并运行 `../audit/run.py`，可以从包内重编译，完全不依赖原项目路径。签收包的 SHA256 应通过交付消息等可信渠道核对，不能只信可同时被替换的本地 manifest。
