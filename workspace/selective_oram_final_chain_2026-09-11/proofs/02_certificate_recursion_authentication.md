# 数值、递归和认证组合定理

## 1. Scalar certificate 的确切对象

设 U^0=(0,0,0)，左右独立拷贝 L,R，以及独立 P~Poi(3/2)。令

    U^(h+1) = ((sum(R)+L2+P-4)_+, L0, L1),
    F_h = sum(U^h), H_h(r)=E[(F_h-r)_+].

`ghost_scalar.cpp` 精确对应这一递推；不是实际 ORAM 的 Monte Carlo。数值 good event 要求各 Poisson input<=M=128、所有中间 total overflow<=C=280。已知表为 subprobability 的 entrywise upper enclosure，不能重归一化。数值 cap 不是协议 stash 容量。

Poi(3/2) 的起点通过 `Fraction` Taylor 夹逼得到 exp(-3/2) 的有理区间，再产生可检查的 binary64 上端；其后只有正数乘除。截断尾概率与一阶矩分别取

    tau <= pbar[M+1]*(M+2)/(M+2-3/2),
    tP  <= (3/2)*pbar[M]*(M+1)/(M+1-3/2).

维护 bad-event probability delta、bad-event first moment m、总均值 upper mu=known moment+m。因为 F_new<=F_left+F_right+P，将 bad-left、bad-right、P>M 和 good inputs 的 cap exit 作 union bound，得到

    delta_new <= 2*delta + tau + delta_exit,
    m_new <= 2*m + 2*(mu+3/2)*delta + 2*mu*tau + tP + m_exit.

例如左子树 bad 的贡献为 m+(mu+3/2)*delta，利用的是右子树/P 与左 bad 独立，不是假设真实 ORAM bucket loads 独立。重复计数只是变松。

固定左总量 s，若右总量加 P 为 T，则输出超过 C 当且仅当 T>=C+4-s+1；这时 F=s+T-4。使用非负 suffix mass/excess 累加 cap-exit contribution。最后

    H_h(r) <= known_stop_loss_h(r)+m_h, r>=0.

不存在用 m_upper-r*p_upper 相减而破坏上界的问题。FE_UPWARD 与逐运算 NextUp 均处理正数 underflow；关闭 FTZ/DAZ、fast-math 和 FMA contraction。每个 worker 设置舍入模式。十六进制 binary64 endpoints 是判定依据；打印的十进制 bits 不是判定依据。

本轮两种算术模式实际完整重算 h=1..31、r=0..280。它们共享递推代码，不称为两个完全独立算法；与旧摘要里的未提供源码的 verifier 无依赖。另用 Python Fraction 枚举小域并检查上包络。

## 2. 从单层到 lifetime

无限 stash 参考执行与有限配置使用同一随机带，直到第一次 overflow 为止相同。对 Q 个 completed-checkpoints，

    Pr[first overflow by Q] <= sum_(t=1)^Q Pr[S_ref(t)>R]
                            <= Q*Hbar_(L+1)(R-delta).

不要求各时间独立，不先条件于此前未 overflow。若认证失败，客户端 fail-stop；恶意拒绝服务不纳入 honest-completion 概率。有限 stash overflow 也只返回拒绝，而不是返回错误值。

## 3. 递归 driver 的精确接口

层 j 的 entry 宽度为 4 bytes，装在层 j+1 的固定大小 map block 中。访问 a_j 时，客户端先采样层 j 新 label，然后对层 j+1 调用**一次** read-modify Access：得到整个旧 map block，并在同一新版本内覆盖该 entry。递归返回后，用旧 entry 访问层 j。最深层的 position map 留在客户端。

对固定顶层地址流，各 map 地址由 floor(a_j/chi_j) 决定，不依赖其 ORAM 随机带。Map block 内容可以包含另一个层的随机 labels，但这种 payload 不影响本层 birth times、请求地址或 placement priority。因此每层满足前一文件的 reduction，且不必假设不同层的 overflow 独立。

Bottom-up 正常装载后，若顶层在线请求数最多 Q_online，则

    Q_j = Q_online + sum_(i=0)^j N_i.

本轮主配置：data tree N0=12,582,912,L0=23；map tree N1=12,288,L1=13；B0=B1=4096；客户端 terminal map=4*N1=49,152 bytes。固定 R=(192,144) 两方案通用。

令 Q_online=2^64-N0-N1，则 Q0=2^64-N1、Q1=2^64。`CertificateBank.plan` 用 exact Fraction.from_float(float.fromhex(...)) 读取证书，计算

    B_stash = sum_j Q_j * Hbar_(L_j+1)(R_j-delta_kind).

当 R_j>=N_j 时，还可直接用实际 current-copy 数量界 S_j<=N_j 把该层 failure 设为0。这个 N 界不能套给含额外 stale 的 shadow。

## 4. Transaction boundary

所有层的内部访问均先推进同一顶层调用的 working state。只有所有层的认证、logical transition 和 scheduled maintenance 成功，才返回用户值并发布新的 committed anchor。认证或 overflow 失败后，客户端永久 fail-stop，后续请求不产生网络 I/O。

服务端可发生部分写入；working roots 和 map 也可能已推进。这种情况下不声称恢复旧事务、回滚或继续执行。本模型只保证没有错误的成功返回和没有在混合版本状态上继续运行。`committed` 中的 payload hashes 是提交边界的诊断摘要，不是用一个 hash 替代实际可信 stash 的持久化方案。

Nonce allocation 不回退；初始化失败也 fail-stop。完整掉电恢复、可用性和并发事务属于另一个系统模型，未被偷偷放进本定理。

## 5. 认证编译的状态投影

实现使用唯一128-bit nonce和 domain-separated 512-bit-output PRF 的 stream pad。数据 plaintext 为固定 B bytes；header secret 部分 Z4时288 bytes，公共部分60 bytes，nonce16 bytes，header wire总计364 bytes。没有独立 AEAD tag；仅在外层认证 opening 通过后解密。

- STREAM input 绑定 context、object type、tree/bucket/slot、data generation w 或 header public fields、nonce、pad index。
- 所有 encrypted headers、data ciphertexts、局部与全局节点的认证输入域分离，编码使用长度前缀。
- SDE 的 data commitment 覆盖 selected bucket 的全部 ciphertexts；logical header refresh 不改变 data generation 或 data ciphertexts。
- R0 的局部认证树允许 one-slot/Z-slot opening；padding-subtrees 是公开固定常量。读取 ordered set 以 slot bitmap 表达，实际顺序为物理 slot 升序。
- Rootless 没有 payload root，但全局 authentication root 仍存在并计费。
- Header-first：认证 selected header roots及全局 path后才解释秘密 pointers；认证全部取回 slot（包括dummy）之后才解密 payload。
- 每个 selected header 都重加密，不因真实 target 或 stash hit 改变刷新集合。
- 服务器没有 PRF key，只存储 client-supplied tags。客户端上传修改后的 bucket/local/global tags；不能免费让服务器重算。

令 pi 忽略 ciphertext、authentication nodes、version/nonces，但保留 current records、stash、g/t 和位置映射。对每个认证成功的状态转移，直接按 `Tree.access/evict/neutral` 归纳有

    pi(State_authenticated,j(t)) = State_core,j(t).

认证辅助 I/O 不推进 ORAM logical clock，不生成 real-block arrivals，不减少 service。因而认证层没有引入一个新的 stash 随机过程。

## 6. Access-pattern simulation

在理想 PRF 世界中，新 nonce 的 STREAM pads 独立均匀；不同 role/domain不复用pad。Header/data ciphertexts的长度及重写集合为公开 I/O 程序的函数。

SDE old leaf 在上次 remap 后未作为新 current leaf 向服务器公开；所暴露的 G_g(oldleaf) 是公开函数。R0 的未消费 slot 排列，在观察过去触达集合后仍对剩余语义 records 交换对称。

在 n 个未读 slots 中剩余 r 个 real 时，ReadBucket 读取所有 r 个 real，再从 dummy 中均匀补 Z-r 个。对任意固定 Z-subset，其概率为

    C(Z,r) / [C(n,r)*C(n-r,Z-r)] = 1/C(n,Z).

必须对整个 subset 按公开物理顺序请求，不能先请求真实块再请求 dummy；后者会把私有 r 编码进顺序。实现使用 bitmap/升序，测试按精确有理数枚举了该分布。

在未发生认证 bad 或 overflow 的两条等长参考请求流上，simulator只需维护公开g、count/used、mask和固定格式。所有主体步骤都与 baseline 的标准等长流定义对齐。

## 7. 主动完整性和密码预算

在不回滚可信 root 的前提下，若不同 header/ciphertext opening 被接受，则沿认证路径必有两个不同认证输入产生相同 tag，或发生 PRF 区分事件。只重放合法旧 ciphertext/旧 header 仍不能通过当前 root。跨位置、跨层移植通过context绑定被排除。未认证信息不得先进入 slot selection 或私有状态更新。

对每个实到理想 PRF hybrid，令其优势最多 epsilon_F；每个执行的全部 PRF calls至多q_F，所有 bucket slots数<=9。固定512-bit modulo抽样的 total variation 对模数M至多 M/(4*2^512)，M<=9!，且每个公开抽样事件固定消耗一个draw。

两个世界的保守组合为

    Adv_ORAM <= 2*epsilon_F + q_F^2/2^511
                + 2*B_stash + q_F*9!/2^513.

这是密码假设下的定理，不是对真实 HMAC 的 concrete cryptanalysis。测试中 HMAC-SHA-512 只是该 PRF 的功能实例。标准 RFC 对 HMAC 的描述同样把安全性建立在底层密码性质上；AEAD接口也不提供独立 anti-replay 服务。

### 7.1 q_F 不再只是一个没有计费的符号

对 B<=4096、L<=30、Z4、slots<=9：每个 full-bucket read/rewrite（包括其局部认证、header和最坏global path重算）少于2^11次PRF calls；logical阶段每selected bucket少于2^10次。每个Access最多一次scheduled path及每个selected bucket一次neutral reshuffle。因此

    calls_per_layer_access <= (2*2^11 + 2^10)*(L+1) < 2^18.

初始物理dummy树每bucket少于2^11次；初始化label派生合计不超过2*sum N_j。于是

    q_F <= 2^18*sum Q_j + 2^11*sum(2^(L_j+1)-1) + 2*sum N_j.

Q_j可作为最多的层调用尝试数：至多一次未完成失败调用，之后fail-stop；horizon guard在发出任何新调用前检查剩余预算。对本轮两层主配置右边<2^84，远小于nonce/counter空间和程序的2^96总PRF guard。

若明确假设在该时间/调用规模及input lengths下 epsilon_F<=2^-132，并选择 B_stash<=2^-130，则上式严格小于2^-128。`certificate_bindings.json`记录实际更强的数值，而不把此PRF优势误写成机器证书。

## 8. 可执行证据边界

`CertifiedRecursiveORAM` 在构造前核验代码/证书身份和参数契约，用相同L+1、R-offset选择点，并拒绝超出lifetime预算的配置。运行期各层horizon guard执行同一装载计数。密码对象经序列化 transport 到仅保存bytes/tags的server，真实返回的bytes先验证再使用。

整条链是研究级的数学证明+数值上包络+实际可运行参考代码及有限回归；不是对Python/GCC/操作系统的proof-assistant全栈形式化，也不是部署安全认证。
