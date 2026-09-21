# SOC3 neutral/read fusion：完成态等价与 transcript 模拟

审计版本：2026-09-15。这里的“正式证明”是有明确状态、量词和归纳接口的数学证明，不是 proof-assistant 机器形式化。实现定位于 `../research_20260914/optimization_v1/src/{optimized_oram,fused_logical}.py`。旧原包保存在 `../provenance/SOC3_received.zip`。

## 1. 定理与比较对象

固定一个合法 Ring 类配置、同一 compact 格式、单个串行客户端和与 ORAM 随机性独立的逻辑历史。用 U 表示 `fused=False` 的“逐桶 neutral，然后一次 logical read/write”，用 F 表示 `fused=True` 的融合程序。两者使用同一 scheduled service、排序、根容量和 remap 规则。比较对象不是 SOC2 的不同 header 格式。

完成态投影 Π 保留：(i) 每桶的 `(gamma,w,v,count,used)`；(ii) 每个 current record 的 uid、地址、leaf、payload 和物理 slot；(iii) stash、终端 position map、uid/t/g；(iv) nonce 与 sample 已消耗的总数量。Π 忽略 ciphertext、认证节点、PRF 调用次数以及中间网络状态。另一粗投影 π 再忽略物理 slot、w/v/count/used，用来连接 stash reduction。

**定理 F1（诚实完成核等价）。** 在理想独立随机带、无计数器溢出和无 stash 溢出的执行中，存在保持各程序随机带边缘分布的耦合，使相同初始抽象状态和相同操作的 U、F 返回相同旧值，且完成后的 Π 相同。因此 π 完全相同，fusion 不改变 stash 随机过程。在真实固定 512-bit modulo 抽样中，结论带上第 6 节的统计误差；不声称同一 HMAC key 下两个程序的 ciphertext/物理排列逐字相同。

**定理 F2（主动服务器）。** 在第 6 节认证/PRF bad 之外，F 的成功响应满足参考 RAM 语义；拒绝后永久 fail-stop。存在只依赖公开配置、操作数及允许的 abort 的在线 transcript simulator。F2 直接针对融合消息接口证明，不能把“删除 U 的若干消息”当作主动安全证明。U、F 的 RPC 数不同，不要求恶意服务器在两种不同接口上选择同一拒绝时刻。

## 2. 单桶不变量与虚拟消费

令 `n=Z+S`。成功验证的桶 header 满足 `count=popcount(used)<=S`，current live slots 与 used 不相交，live 数不超过 Z。令 U_b 为未消费 slots，r 为 live 数。

本轮 selected 集合 D 由公开 `(g,oldleaf)` 决定。令 E 为其中 `count=S` 的桶。因为此时 `|U_b|=n-S=Z`，neutral 的 Z-slot subset **恰好是整个 U_b**；它不依赖 r 或目标位置。`subset` 仍固定消耗一个抽样事件，包括补集只有一种的情形。所有 live payload 都已在该 opening 中。

对于 b∈E：以同一随机排列把原 live records 按 uid 顺序放入 n 个新 slots，填满 dummy，得到中间 h*。它满足

`gamma*=gamma, w*=w+1, v*=v+1, count*=0, used*=0`。

在 h* 上选择 j：目标在此桶时为该目标的新 slot，否则从新 dummy slots 中均匀选择。F 不向服务器再读取 j，但必须执行这个选择并将其写入最终状态；它不是省略的抽样或没有实际语义的记账。目标 payload 来自已经认证的旧 opening，经 uid 关联到新 slot。若 j 是 dummy，其 payload 没有被程序使用。

最后删除目标 descriptor（若存在），并设置

`gamma'=gamma, w'=w+1, v'=v+2, count'=1, used'={j}`。

全部 n 个新 ciphertext（包括已虚拟消费的目标 ciphertext）仍上传；final header 中该 descriptor 已删除，因而服务器留存的旧目标副本不再是 current。局部 data root 绑定这些 n 个 ciphertext，final header 与此 root 一起重新认证。

对于 b∉E：两程序都在旧 h 上选择一个未消费 slot j，认证并读取，按同一规则删除目标，保持 gamma/w 和 data ciphertext，令 `v'=v+1,count'=count+1,used'=used∪{j}`。dummy 总能选到：count<S 时至少 `S-count>=1` 个未消费 dummy；neutral 后至少 S 个。每桶至多一个目标，全局 current 地址唯一；stash 命中与桶命中不能同时发生。

## 3. F1 的事件带耦合与多桶归纳

为每个树、桶及事件种类给独立随机带，按该种类的发生次数编号：`RMW_SUBSET(b,k)`、`PERMUTE(b,k)`、`LOGICAL_SLOT(b,k)`；另有每层 `REMAP(k)`。排列、subset 和 dummy rank 都固定消耗一次 draw，目标命中也不跳过 LOGICAL_SLOT。用相同事件标签耦合两程序。

U 按深度逐桶执行 neutral，再逐桶选 logical slot；F 先收集所有 opening，再完成 E 中的重建。两程序只是重排了一组相互独立的事件，各程序中每一事件的独立均匀边缘分布不变。选 slot 依赖的本桶 h，在相应事件发生时相同；跨桶没有 payload 或状态写入依赖。第 2 节的逐桶等式于是给出所有桶的同一最终 headers、live records、slots 和相同旧目标。

这种事件带不是修改生产随机数发生器。实际 `PRF.draw` 的全局 sample counter 在两程序中的事件分配顺序不同；理想随机函数在不同、唯一且域分离的输入上给出独立值，允许上述分布耦合。对照测试单独安装 event tape，验证程序转移等式，不把测试 PRF 当成生产实现。

两个程序每个 neutral 都 seal n 个 payload 和一个中间 header；随后对每个 selected 桶 seal 一个 final header。F 虽不上传中间 header，仍实际生成它并消耗 nonce。因此每层完成时 nonce 总消耗 `|E|(n+1)+|D|` 相同，sample 总消耗 `2|E|+|D|` 相同。seal 的全局顺序不同，某个对象得到的具体整数 nonce 可以不同；这正是 Π 不比较 ciphertext 的原因。不同 role/slot/context/nonce 的 pad 不复用，nonce 不回退。PRF 调用次数通常不同，因为 F 省掉了中间认证树计算和重读解密；此值只受预算上界控制。

目标移除后，两程序使用同一 transform，产生同一新 uid、同一 fresh leaf 和相同 stash。若到 scheduled 时刻，对相同状态执行同一全路径维护；再按相同 uid 顺序和新 phase legality 放置，完成态仍相同。初始化通过普通 logical accesses 装载，故同一归纳涵盖初始化及任意长度的合法完成前缀。

`gamma_b` 只在 scheduled service 中推进。neutral 的重加密、虚拟消费和 header v 推进都不是 service；F 显式把 old gamma 传给 prepare。不能用 w 或 v 的增加冒充 gamma 推进。

## 4. 目标位置分布与剩余排列不变量

在理想密文世界中，条件于已公开的 used slots 和历史 opening，未消费位置上的语义 live records 保持均匀注入；真实 record 的 uid/地址/leaf/内容没有以明文泄漏。以下概率均条件于任意固定剩余语义集合，故不要求 live 数 r 公共。

若未消费位置有 u 个，目标在其中，其位置均匀，`Pr[j=x]=1/u`。目标不在本桶时，先有均匀 r-subset 的 live 位置，再在其补集均匀选 dummy：

`Pr[j=x] = (u-r)/u × 1/(u-r) = 1/u`。

给定公开 j，删除命中的 real 或消费一个 dummy 后，剩余 live 记录仍均匀注入剩余 u−1 个位置。两种情况剩余 r 可能不同，但其条件不变量分别成立；后续观察仍由同一公式模拟。目标在另一桶、stash、或尚不存在时，本桶都走同一 dummy 规则。target 在 E 中时，使用重建后的 n 个位置，故其虚拟 j 和 target 在外/stash 时一样均匀于 n；最终公开 used={j} 不泄露三种情形。

一般 scheduled Z-subset opening 的均匀性也要保留。在 u 个未消费 slots 中，读全 r 个 live 再均匀补 Z−r 个 dummy，对任意 Z-subset V：

`Pr[V]=C(Z,r)/(C(u,r) C(u-r,Z-r))=1/C(u,Z)`。

其 bitmap 按物理位置公开，不把 real 放在请求开头。neutral 触发时 u=Z 是上述分布的退化情形。重写的排列使用独立新事件带，与旧 subset 独立。

跨桶 fresh permutation 独立。条件于任何固定的目标所在桶，各桶 slot/subset 观察都有上述相同均匀核，因此其乘积也不依赖该目标所在桶；再对隐藏的目标位置混合仍同分布。这处理一次调用中多个 neutral 以及 neutral/nonneutral 混合，不把各桶的真实占用量错误地假设成独立。

## 5. 可运行的 transcript simulator 说明

公开输入是配置、逻辑操作/装载次数、固定块长、序列化格式和 fail-stop 规则；不包含地址或 hit/stash 标志。固定请求历史模型下，每次旧 leaf 是先前秘密 fresh remap 的均匀值（允许与上次相同），不同层的 domains 分离。递归层的访问地址由固定上层地址整除得到；其中存储的上层 leaf 值是 payload，不决定本层访问模式。

Simulator 保存公开 `(g,t,gamma,w,v,count,used)`、服务器的持久密文字节/认证标签表以及 nonce allocator。按均匀 oldleaf 与公开 GC 产生 D；按 count 得到 E；对 E 请求全部旧 unused Z 个 slots，对 D\E 请求均匀未消费 slot。它抽取 E 的均匀虚拟 j，执行第 2 节 public header 转移，并按程序顺序分配全部 n 个 slot nonce、中间 header nonce、final header nonce。没有上传的中间 header 留下的 nonce 间隔完全由 D/E 决定，无 target 分支。所有 fresh pads 用独立均匀字节；未被重写的 ciphertext 保持原字节，不能每次读取都重新抽样。

认证用按域分离输入索引的随机函数表处理：相同已发出输入保持同 tag，新的输入分配新 512-bit tag；对象的 nonce、AAD、身份及相等关系也保留。Simulator 不需要解密私有 descriptor；其分布正确性来自第 4 节条件不变量。对主动服务器，模拟器解析相同帧并按其维护的当前已认证对象/标签表验证；坏 opening 导致同一层级的拒绝。服务器使两个不同认证输入碰撞或猜中新有效 tag 的事件计入 bad。允许其拒绝服务，不能保证完成或恢复。

此构造解释了完整消息的长度、bitmap、nonce、持久字节相等关系和认证顺序，超出了只模拟摘要 RPC/bytes 的结论。它不覆盖本地内存访问/CPU时间/网络计时侧信道。

## 6. 认证顺序、remap 和 fail-stop

1. `open_path` 先把全部 headers/data roots/跳过桶/global siblings 绑定到当前可信 root，成功后才解密任何 header 或依据其秘密 descriptor 选 slot；随后检查 gamma。
2. `read_slots` 对 **所有桶、所有取回 slot，包括 dummy** 的 opening 和完整 body 长度验证完毕，才解密第一个 payload。F 不会在后面的 bucket 认证前消费前面的 plaintext。
3. 此后才在本地重建 E、移除目标并形成 final-write。中间 h* 是本地工作态，不发布为可接受服务器 root；旧 view root 检查一直使用旧 path_tags。最后以 final header 和新 data root 同时计算 bucket/global tags，一次 WRITE 后验证 ack，再推进 working root。
4. `RecursiveORAM._access` 在读取下层 map 前已抽取 fresh remap，并可能先更新下层 working map/terminal map。它不是在完成后才采样。成功返回的提交边界位于所有层 logical 和 scheduled maintenance 之后；此时新 map、新 current record 和各 root 一致。
5. 若 header/slot/body/ack/transform/stash 等任一步失败，外层 `access` 捕获异常并置 dead。旧 committed anchor 不变，但服务器和 working state 可能部分推进；不承诺回滚。任何后续请求在产生 I/O 前拒绝，nonce 不重置。公共 horizon 的预先拒绝可以不置 dead，因为尚未进入任何新操作。

在无认证 bad 的成功前缀，以上顺序把 payload/descriptor 绑定到当前状态；结合 F1 给出参考 RAM 完整性。固定 512-bit 取模相对理想均匀 rank 的变差至多 `M/(4·2^512)`；所有抽样事件数不超过 qF，且 M≤13!。同原认证混合的保守合并：

`Adv ≤ 2 εF + qF²/2^511 + 2 Bstash + qF·13!/2^513`。

εF≤2^-132 是对指定调用规模和输入长度的 PRF 假设，不由测试或 HMAC 名称证明。计数器边界和 qF 的具体条件见 `02_parameterized_reduction.md`。有限测试检验实现是否满足上述接口，不能替代任意深度、历史上的归纳证明。
