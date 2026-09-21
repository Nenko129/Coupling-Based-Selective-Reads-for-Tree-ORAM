# 参数化 actual → shadow → field → ΦZ/Poi(A/2) → lifetime

本文件把原 `../selective_oram_final_chain_2026-09-11/proofs/01_reduction_complete.md` 的各步逐项参数化；该完整原文及其实现/oracles 随包提供，以下推导不是通过替换证书标题获得。

## 1. 范围和不变量

数学 reduction 固定整数 Z≥1、A≥1、L≥1、N≤A·2^(L−1)，gap 参数 m=2。请求历史与 ORAM 随机带独立；可先固定应用输入、应用随机带及参考 RAM 执行。不能把观察服务器 transcript 后选择地址的攻击者自动纳入 stash 量词。代码/证书契约只实例化 (4,3) 的 SDE/R0 与 (7,6) 的 R0。

uid 是不可变的版本 creation serial。每次请求使旧版本失效，产生独立均匀 fresh leaf 的新 uid。phase g 只随每 A 次 logical requests 的 scheduled eviction 前进，服务 endpoint 是 bitrev(g)。R0 维护全部非根层，根容量为 0；不涵盖 sparse service。neutral/fusion 由 `01_fusion.md` 保留粗投影 π，因而不产生 arrivals、不移动 token、不推进 gamma/g。

## 2. 任意 Z/A 下的协议支配链

**Locality。** record bits 为 `(g−1−bitrev(leaf)) mod 2^L`。设 z=LCP(leaf,e_g)，变化的 bits 深度不超过 z。从叶向根的 m=2 自动机只依赖当前及更深 bits，故 d>z 的 eligibility 不变。这与 Z/A 无关；pinned nonroot gamma 表示最后真实 service，故未再次服务前与当前 G_g 在该桶等价。

**Actual ≤ finite shadow。** 对每个 current uid 使用同 leaf 并保持 `depth_actual≥depth_shadow`；shadow 额外保留 stale，直到失效后第一次 mapped-leaf service。logical 失效不改 uid 优先级，fresh 入双方 stash。维护路径上 actual pool 中未放置 current 是 shadow 对应 pool 的子集；同一桶取最多 Z 个、按 uid 排序，若 shadow 选中了某 actual 候选，actual 中其 rank 只会更小，故 actual 也选中或已放到更深处。逐桶归纳保持偏序。actual 在路径外而 shadow 在路径内的 current，其 actual 深度>d=LCP，shadow 本轮最多放到 d，偏序仍保持。此论证只用“同一容量 Z”，不使用 Z=4。于是 `Sactual≤Sshadow`。

**Finite shadow = canonical packing。** exact home 是出生后所有 scheduled endpoints 的最大 LCP；尚未经服务的 fresh home 是 bottom。在维护路径之外，每个 hanging subtree 的 home 输入、eligibility 以及向路径输出的 overflow 多重集合保持不变。旧 global packing 把这些边界 tokens 放在路径或 stash，finite path read 恰好取回它们。路径上的新 home 与 ownership 限制给出同一最早可参与 bucket；以同一 uid 顺序、同一容量 Z 逐桶处理，留下的具体 uid 一致。由初始化归纳得 local service 与 global canonical packing 交换。这里保持的是 multiset，不能仅比较数量；证明对任意固定 Z 成立。

**独立标记 field。** 固定时刻和逻辑历史，第 i 个版本的 birth 和下一次同址访问时间确定；只有独立 leaf U_i 随机。它对 exact-home field 的贡献 X_i 是零或某一个 bucket 的单位点，且各 i 独立。各 bucket 的 Y_v=Σ_i X_iv 本身不独立。

叶桶在最近一次服务时最多有 N 个 current 候选，每个命中该叶概率 2^-L；之后出生者尚未到达该叶，stale 保留不增加候选数。因此 E Y_leaf≤N/2^L≤A/2。深度 d 的非叶，两个 child 最近服务相差 2^d 个 phases；只有这一窗口内至多 A·2^d 个 births 且落入较早 child 的 leaf，才可能 exact home 为该桶。每个概率 2^-(d+1)，故 E Y_v≤A/2；startup/删除只减少数量。因此 Z7/A6 的正确 Poisson rate 是 **3**，不是 3/2。

## 3. 三状态与 idcx 的参数化

按当前 phase 把 children 定向为 record 侧 R 和 nonrecord 侧 L。来自 R 的全部 overflow、来自 L 的 q=2 和 exact-home arrival p 可在本桶服务；其他 L0/L1 分别旁路到 q=1/2。服务后的未放下 token 的 q=0。因此计数等式为

`ΦZ(L,R,p)=((R0+R1+R2+L2+p−Z)+, L0, L1)`。

其中 x+ = max(x,0)。输出具体 uid 取决于排序，输出三类数量不取决于谁胜出。叶层是从零 child 开始的同一 Φ；故 h 是 **L+1**。Φ7 必须减 7；不能只改变 arrivals 的 rate。

所有输出坐标由非负和、复制和正部复合而成，均 increasing directionally convex（idcx）。同/混合二阶差分非负由结构归纳得到；外层 increasing convex 函数保持该性质。因此 `(F−r)+` 是 idcx。

一个单点标记 X 以概率 p_j 在坐标 j 放一个点，q=Σp_j≤1。令 J 为 p_j/q 的 iid marks，对任意 idcx f 和固定背景 x，`g(k)=E f(x+Σ_{a≤k} e_Ja)` 是离散凸。整数 K≥0 且 EK=q 满足 `E g(K)≥g(0)+q(g(1)−g(0))`；取 K~Poi(q)，Poisson marking 给出独立 Poi(p_j)。逐个替换独立版本，再补独立 Poi(A/2−EY_v)，得到

`E[(F_g(Y)−r)+] ≤ E[(F_h(P)−r)+] = H_h^(Z,A/2)(r)`。

没有声称 actual field 各桶独立，亦没有声称所有事件的坐标随机支配。固定 phase 的公开 child 交换对 iid Poisson field 分布不变，故统一 h 递推适用所有观察时刻。

## 4. 根修正、fresh 与所用点

在**同一个 field** 上把 root 容量 Z 改成 0，最终输出增加 `min(x,Z)≤Z`。completed boundary 已完成所需 maintenance，fresh 数最多 A−1。因此

`δSDE=A−1; δR0=A−1+Z; Pr[S(t)>R]≤H_(L+1)^(Z,A/2)(R−δ)`。

实际 Z4/A3 offsets 为 2/6，Z7/A6 R0 offset 是 **12**。整数 stop-loss 不等式 `1[u>r]≤(u−r)+` 只在整数阈值用；数值网格仅接收 r≥0。

本包新网格只覆盖 h=1..24、r=0..280，即 Z7 非平凡证书最多 L=23。h=25/31 的 Z4 网格绝不能借给 Z7。若 R≥N，则 actual current-copy 数 S≤N 给出 deterministic ε=0，此分支不使用 ghost 数值；允许更高 L 时必须明确标为 count bound，而不是扩展了新证书高度。

主 Z7 配置 data `(L,N,B,Z,A,S,R)=(22,12582912,4096,7,6,6,149)` 用 `(h,r)=(23,137)`；512-byte map `(15,98304,512,7,6,6,147)` 用 `(16,135)`。实际值由 JSON profile 和两模式网格逐项重新计算，不抄十进制摘要。

## 5. 递归、lifetime、密码条件

层 j+1 每块含 B_(j+1)/4 个 entries，N_(j+1)=ceil(4N_j/B_(j+1))。固定顶层地址流递归产生确定的 map 地址；其它层的随机 labels 是 payload，不影响本层 birth/priority。bottom-up 普通请求装载计入 `Q_j=Q_online+Σ_(i≤j)N_i`。

以无限 stash 参考过程做 first-failure coupling，在以前未失败处有限过程相同；不条件化改变分布，直接 union bound：`Bstash≤Σ_j Q_j ε_j`。时刻/层之间不要求独立。一次失败调用后永久停止；horizon guard 保证尝试预算不会在 I/O 后才发现超限。

认证使用 fixed-size SOC3 compact headers：60 public+16 nonce+32字节对齐的 `(8+30Z)` secret，故 Z4=204、Z7=300 bytes。角色/context/nonce 域分离。n≤13、Z≤7、B≤4096、L≤30 时，单个 full read/rewrite 的 payload pad 调用≤2·13·64=1664，header pad≤2·7，局部节点≤27、header/global path 各常数次重算；即使为每桶重复整条31层路径重算，仍小于2^13。每次 layer access 的 logical/neutral/scheduled 所有桶数≤3·31，以2^22覆盖；物理 dummy 初始化每桶≤2^13。保守界

`qF≤2^22 ΣQ_j + 2^13 Σ(2^(L_j+1)−1) + 2ΣN_j < 2^96`。

这同时保证 nonce/sample 空间未耗尽。若每个真实到理想 PRF hybrid 在此规模上的 εF≤2^-132，结合 `01_fusion.md` 公式和精确 Bstash，可判定 conditional advantage<2^-128。该密码假设、可信私有状态不回滚、单客户端、无本地时序/内存泄漏都是契约条件。

实现审计分别覆盖每条接口：coupled fusion 完成态；逐 uid actual/shadow 深度；local/global commutation；field 三状态等式；Z7 根移位；A6 时间窗口标记；数值 joint recurrence；递归 gate/lifetime。有限枚举是反例检测与实现对照，普遍性仍由本文件及原自包含归纳证明承担。
