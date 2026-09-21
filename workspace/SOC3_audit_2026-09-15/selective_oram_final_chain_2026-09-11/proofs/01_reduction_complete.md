# 从实际状态到同一个三状态 ghost：补充证明

版本：2026-09-11，GC-SERIAL-LEAF-RETAINED-SOC2-v2。

**来源与新增内容。** Ring 原论文 Appendix B 给出 mapped-leaf stale 回收和 timestamp/load 几何；`gap_m2_uniform_time_theorem_draft_v2.md` 给出 leaf-anchor、phase-local commutation、idcx 与三状态递推。原 9 月 3 日报告将这些列为主 reduction。本文件不是声称取得了它另行引用而未上传的完整证明稿，而是将当前材料中的跳步重新展开为一份自包含的补充证明。特别新增逐 current-version 的深度偏序、明确的 hanging-subtree 接口、固定地址历史下的独立标记表示，以及该表示到代码三状态的对应。

## 1. 定理量词和状态

固定高度 L>=1，Z=4,A=3,m=2，N<=A*2^(L-1)。主 stash 结论对**与 ORAM 随机性独立的任意固定逻辑请求流**成立；对这样的流取随机混合仍成立。应用根据正确的逻辑 RAM 返回值决定下一请求也可以先固定应用随机带、输入和参考 RAM 执行，再使用下面的证明。

本证明**不把“外部请求选择器读取 ORAM server transcript 后再自适应选择下一逻辑地址”自动包括进来**。固定序列上的独立标记证明不能通过条件于这种已选序列来推广。旧文字中没有限制的 online-adaptive stash 量词应收紧到本段，而不是让数值证书替它承担。服务器可以主动修改响应；认证层证明在第一次认证 bad 之前，或拒绝，或返回同一参考 RAM 的值。这不赋予应用读取内部 ORAM 随机状态的权限。

每棵树的 phase g 是已完成 scheduled evictions 的数量，e_g=bitrev_L(g mod 2^L)。请求每次产生一个唯一版本 uid，按递增 creation serial 排序；uid 在整个版本存续期间不变，尤其 real->stale 不改变优先级。树中每个 current version 的 leaf 与 position map 一致。stash 深度记为 -1。

以下 primitive 全部精确定义：

- `G_g(ell)`：叶层恒选；从叶到根扫描 record bits，连续两个 non-record 跳过后，下一个 non-record 作为 filler 选中。record/filler 均将 miss counter 重置到 0。
- record bits：x=(g-1-bitrev_L(ell)) mod 2^L，d<L 时 bit_d(x)=1 是 record。
- canonical packing：每个 token 从它的 exact home 开始沿祖先链向上；在每个合法 bucket 按不可变 uid 留下至多 capacity 个，其他 token 继续上移，不合法的 bucket 旁路；最终未放置者进入 stash。
- virtual exact home：birth 时为 bottom；每次 scheduled endpoint e 对存活 token 执行 H'=max(H,LCP(ell,e))。
- shadow 回收：旧版本被重新请求后标为 stale，但保留到该次失效之后第一次 e_g=ell 的 scheduled eviction。实际实现不存储这些额外版本。

初始化从只有 dummy 的树和空 stash 开始；所有真实装载均作为普通 logical operations 计数。

## 2. Locality、home 和 pinned/current 接口

令 z=LCP(ell,e_g)。reverse-lex record 的更新删除的 depths 均不超过 z，并加入 z；d>z 的 record bits 不变。Leaf-anchored automaton 在 depth d 作决定时只用 d 及更深的 bits，所以从 L 向 z+1 归纳得到

    G_(g+1)(ell) intersect {z+1,...,L}
    = G_g(ell) intersect {z+1,...,L}.

真实树中不在当前 path 上的 token 位于深度 d>z，因此 phase 更新不会让它静默失去合法性。路径内重写必须检查新 phase 的 G_(g+1)。这给出 retrievability 的归纳：当前版本要么在 stash，要么位于目标读取的合法 bucket；逻辑读只移除该目标，fresh remap 后加入唯一新版本。

一个建立了 home 的版本，其 H 是出生以来公开 endpoint 的最大 LCP，即一个后缀最大值，因此 H 自身是当前 record（叶层也是 record）。写回某 token 到当前 endpoint e 的深度 d，path ownership 已经强制 d<=LCP(ell,e)<=H'，所以实际代码不用额外存储 H。

对于非根 bucket b，令 gamma_b 为最后一次真实 scheduled service 完成后的 phase。其后直到当前 g，没有 scheduled endpoint 经过 b；对 b 下的任意 ell，每步 z<depth(b)。由 locality，b 的 membership 未变，故

    d in G_(gamma_b)(ell) <=> d in G_g(ell).

因此完整 nonroot service 下 R0 的 pinned mask 恰等于 G_g(ell)\{0}。这不适用于省略了中间层 service 的 sparse-RMW。

## 3. 实际 current versions 到 finite shadow 的逐版本支配

**关系 D。** 对每个 current uid，两边采用同一个 mapped leaf，并且

    depth_actual(uid) >= depth_shadow(uid).

shadow 还可包含任意数量的额外 stale versions。两者都用同一个 uid 顺序、同一个 phase 和同一 capacity profile；R0 的 profile 只把根容量改为 0。

初始化关系成立。一次 logical request 将实际旧 current 删除；shadow 将该 uid 改标 stale，不更改位置和优先级。双方把相同的新 uid/leaf 放入 stash，其他 current 不动，因此 D 保持。实际 neutral reshuffle 只重排当前 bucket，不改变版本集合，D 也保持。

现在考虑 scheduled path P(e)。如果一个 actual current uid 位于 P(e) 或 stash，则由于其 shadow 位置是同 leaf 上不更深的祖先，它也在 shadow 的 P(e) 或 stash。故 actual 的待放置 uid 集合包含于 shadow 待放置集合。删除 mapped-leaf stale 只会删除额外 token，不会删除任何 matched current。

双方从叶到根处理相同的 bucket。在处理某 bucket 前，保持“actual 尚未放置的 uid 集合包含于 shadow 尚未放置的集合”。若某个共同 uid 被 shadow 在该 bucket 选中，而 actual 尚未将它放到更深处，则它在 actual 的 eligible candidates 中的 rank 不超过在 shadow 中的 rank，因而也会被 actual 选中。于是处理后仍保持集合包含。这个逐 bucket 归纳与 eligibility 变化无冲突：两边在本次写回都使用相同的新 phase，candidate uid 的 leaf 也相同。

剩下一类 current uid：actual 在路径外更深处，而 shadow 被本次路径取入 pool。对它，任何 shadow 新位置深度都不超过 z=LCP(ell,e)，而 actual 路径外深度严格大于 z，所以 D 仍成立。

因此 D 对全部 completed operations 成立。特别地，actual 中位于 stash 的每个 current uid 在 shadow 中也位于 stash，于是

    S_actual(t) <= S_shadow(t).

这比“额外 stale 看起来只会更坏”的直觉更强，并明确说明固定 uid 顺序为什么必要。

## 4. Finite shadow 与 infinite-home canonical packing 相等

令 X_g 是相应无限桶 token state，P_g(X_g) 是上述 canonical packing。归纳假设 finite shadow 等于 P_g(X_g)。Logical request 仅改变不参与排序的 stale flag，加入 home=bottom 的新 token，所以二者在该操作下保持相等。

对一次 scheduled endpoint e，分解整棵树为 path P(e) 和挂在路径上的 hanging subtrees。

1. 对一个 home 位于 hanging subtree 中的 token，其 H>z。H'=H，且所有位于 hanging subtree 的合法性由 locality 保持。没有 mapped-leaf stale 删除发生在这棵 hanging subtree 内，因为 ell=e 的路径不进入它。
2. 因此每棵 hanging subtree 的 home 输入、内部 canonical packing 和向 path 边界输出的 overflow **多重集合**均不变，而不只是它们的数量不变。
3. 这些边界 overflow 已在旧 global packing 的 path buckets 或 stash 中。Finite EvictPath 读取路径和 stash，恰好取回所有这些 tokens；不会要求它重新读取 hanging subtree。
4. Home 原本在路径或 bottom 的 token，新 home 为 z，仍在路径。其余边界 token 的 home 位于 hanging subtree 深处，但它在这条路径上的最深公共位置也是 z。
5. 因此 global post-processing 在 path 上的输入，与 finite EvictPath 收集的 pool 是同一多重集合。某 token 在 global 版本仅到达深度 z 才加入边界队列，而在 local 版本虽提前存在于 pool，却被 path ownership 禁止使用 d>z。两个过程实际可参与的最早 bucket 相同。
6. 按叶到根、相同 eligibility 和 uid 顺序处理，逐 bucket 留下的 uid 完全相同。

所以对可达、home 表示合法的 tokenized states，

    E_g^capacity(P_g(X)) = P_(g+1)(E_g^infty(X)).

这里不再把定义域不加说明地扩大为任意不合法 home/state。实际 driver 的 reachable states 均由初始化及上述转移归纳进入此定义域。

## 5. 无限 field 的独立标记与 A/2 mean

固定逻辑地址序列和观察时刻 t。第 i 个版本的出生请求编号 i、下一次访问同地址的编号 eta_i（或 infinity）均已确定。它的 leaf U_i 是独立均匀标记；home 是出生后的 scheduled endpoints 与 U_i 的最大 LCP；是否已被删除由 eta_i、U_i 和公开 service schedule 决定。

因此，在排除 birth 后尚未经历 scheduled service 的 fresh tokens 后，

    Y = sum_i X_i,

其中每个 X_i 要么为零，要么只在一个 exact-home bucket 取 1，且不同 i 的 X_i 相互独立。这一结论是由固定版本时间表和独立 U_i 得到，**不是仅由每桶均值推断独立性**。同一 Y 的各个 bucket 坐标通常不独立。

### 5.1 叶桶

固定叶桶 v，令 k 为不晚于 t 的最近一次服务 v 的 scheduled index。如果尚未服务，Y_v=0。在该次服务中，所有此前已经 stale 且 mapped leaf 为 v 的版本都被删除。服务后位于 v 的版本，只可能是每个逻辑 ID 在该服务时刻的 current version，并且它的 leaf 等于 v。服务之后出生的版本还没有机会到达 v。

对固定地址序列，每个 ID 在这个公开时刻的 current-version 编号是确定的，候选至多 N 个；每个候选命中 v 的概率为 2^-L。之后即使被标 stale，在下次 v service 前仍被保留，不增加候选集合。所以

    E[Y_v] <= N/2^L <= A/2.

### 5.2 非叶桶

固定深度 d 的非叶桶 v，令 k0<k1 为两棵 child subtrees 最近的 scheduled service indices；在 startup 可以向过去延伸 reverse-lex 时序并截断尚不存在的 births。交替服务几何给出 k1-k0=2^d。

home 恰为 v 的 token 必须生于 phases k0+1,...,k1，并且其 leaf 落在较早服务的 child subtree：更老的 token 已有机会进入某 child，更晚的 token 未被 v 服务，落入较新 child 的 token 会进入更深处。这至多涉及 A*2^d 次 birth，每次落入指定 child subtree 的概率为 2^-(d+1)。删除只减少该集合。因此

    E[Y_v] <= A*2^d*2^-(d+1) = A/2.

这正是 Ring Appendix B 的 timestamp 几何在当前明确 leaf-retained shadow 上的实例化。访问 stash 中的地址同样生成一个新 uid，并将旧 uid 标 stale，故没有被此计数遗漏。

## 6. 从按 UID packing 到三状态 count functional

对当前 phase g，任一内部 bucket 的两个 children 中，一个 child 下所有 leaf 在当前 depth 的 record bit 为 1，称为 R；另一 child 的该 bit 为 0，称为 L。这个重新定向由公开 g 和 bucket prefix 决定。

每个 exact-home arrival 的 home 自身是 record，故在 home 上可服务，剩余 token 的 miss state 归零。来自 R 的所有 overflow 都可在当前 bucket 服务；来自 L 的 q=2 类触发 filler 服务，而 q=0,1 只能分别旁路成为 q=1,2。

所有可服务但未放下的 tokens 的新 q 都是 0。因此留下具体哪些 uid 不影响三类 overflow **数量**，得

    Phi(L,R,p) = ((R0+R1+R2+L2+p-Z)_+, L0, L1).

基例为 ((p-Z)_+,0,0)。这个 F_g(Y) 是按 uid packing 的精确总 overflow，不是忽略了 all-different 或 competition 的独立近似。

对 iid Poisson field，公开交换左右 children 不改变分布，因此 F_g(P) 的分布与 g 无关，并恰等于 `ghost_scalar.cpp` 计算的 U^(0)=0、连续 h=L+1 次 Phi 所定义的 F_h。

## 7. idcx Poisson envelope

函数 f 在非负整数向量上 increasing directionally convex，指单调且所有同坐标/混合二阶差分非负。

若 X 以概率 p_j 在坐标 j 放一个点，q=sum p_j<=1，取 iid marks J 的分布 p_j/q。对固定背景 x，g(k)=E[f(x+sum_(a<=k)e_Ja)] 是离散凸函数。均值为 q 的非负整数 K 满足

    E[g(K)] >= g(0)+q*(g(1)-g(0)).

取 K~Poi(q)，右边即 Bernoulli point 的期望；Poisson marking 后各坐标为独立 Poi(p_j)。逐个替换独立 X_i、再补充独立 Poi(A/2-mu_v)，得

    E[f(Y)] <= E[f(P)],  P_v iid~Poi(A/2).

三状态坐标和总和均为非负和、坐标复制及 increasing convex positive-part 的复合，因此由结构归纳是 idcx。若 H increasing idcx，则 phi(H) 对 increasing convex phi 仍为 idcx：写 H(x+e_i+e_j)=H(x)+b+c+d，其中 b,c,d>=0，直接使用 phi 的凸性及单调性。故 (F-r)_+ 也是 idcx。

这得到的是上述 functional 的期望比较，**不是任意事件意义的独立 Poisson 随机支配**。

## 8. Root shift、fresh tokens 与最终单层不等式

固定同一个 Y，root profile 从 Z 改为 0 只改变最后一个容量算子。令可服务量为 x：

    F_Z = (x-Z)_+ + L0 + L1,
    F_0 = x + L0 + L1,
    0 <= F_0-F_Z = min(x,Z) <= Z.

每个 completed logical operation 的 round boundary 已包含该轮必要的 scheduled eviction，因此还未经历 eviction 的 fresh births 至多 A-1=2 个。令 delta_sde=2，delta_r0=Z+2=6。整数变量满足 1[u>r]<=(u-r)_+，所以

    Pr[S_kind(t)>R]
      <= E[(F_g(Y)-(R-delta_kind))_+]
      <= H_(L+1)(R-delta_kind)
      <= certified_upper[L+1,R-delta_kind].

**本轮精确的闭合接口：** actual-to-shadow 是第 3 节的逐版本偏序；shadow-to-field 是第 4 节的 multiset 等式；field-to-Poisson 是第 5–7 节的固定历史标记和 idcx 不等式；Poisson-to-scalar 是第 6 节的逐节点 count recurrence。没有把独立数值验证器当成这些步骤的替代品。

## 9. 与实际程序逐项对应

- `Tree.access`：目标失效、每次产生新 uid、fresh remap 入 stash、每个 selected header 固定刷新。
- `Tree.evict` / `placement`：固定 A 时钟、public bit-reversal、全部维护层、UID 顺序和新 phase legality。
- `Tree.neutral`：只读取并重排当前 bucket，绝不从 stash 取块；gamma 不变。
- `Differential.observe`（仅外部测试）：逐版本 actual/shadow depth；shadow/local-global packing；实际 shadow field 到三状态 F 的等式；fresh<=A-1。
- `reduction_checks.py`（独立有限检查）：field/count recurrence、priority-independent counts、phase-local commutation、root shift、timestamp mean。

测试用于发现实现/定义错误；任意深度和任意固定请求历史的依据是上面的归纳与标记证明，而非测试次数。本文件不是 proof-assistant 机器形式化。
