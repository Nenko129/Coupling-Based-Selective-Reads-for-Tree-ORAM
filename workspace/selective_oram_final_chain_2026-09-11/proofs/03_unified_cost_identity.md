# 从同一套执行得到统一成本表

## 1. 计费对象和序列化

计费单位是SOC2**应用协议请求/响应帧**。它包含data、header、认证proof、客户端上传tags及控制字段，不包含TCP/TLS/Ethernet封装、重传、系统调用、存储设备block rounding或CPU时间。实际transport在进程内执行，但双方都序列化/解析同一bytes；没有用对象大小或估算blocks替代帧长度。

共同frame header为36 bytes：magic4、version1、opcode1、flags2、tree-id4、request-sequence16、body-length8。响应也有36 bytes。Body grammar：

- OPEN_FULL/OPEN_HEAD request：leaf8+depth-mask8。
- READ_SLOTS request：leaf8+depth-mask8，每个selected bucket再有8-byte slot bitmap。
- WRITE request：leaf8+depth-mask8+full-write-mask8，随后按公开顺序发送headers、可选data/local tags、bucket tags和改变的global ancestors。
- INIT request：bucket id8及该bucket的固定初始化对象；初始化费用单列，不作为在线零成本。

Z4配置：secret header288，public header60，nonce16，因此H=364；data W=B+16；authentication tag h=64。

## 2. 每条实际trace的恒等式

对每个已执行RPC e，定义公开shape包含op、leaf、depth mask、slot bitmap、full-write mask。`invoice_event`不读取请求/响应bytes，也不读取秘密状态，只按该shape与Config重算各字段的字节数。

    actual request_length(e)+actual response_length(e)
      = data_down + data_up + headers_down + headers_up
        + auth_down + auth_up + framing_and_control.

`Transport.rpc`记录实际len(bytes)和帧哈希；`invoice`逐项核对上述独立计算与实际长度及component计数。于是对任意成功有限执行，整个run的bill就是逐帧恒等式之和。它不依赖工作负载分布或stationarity。

这种定义把成本表接到了认证过的recursive driver，而非独立编写一个没有执行的公式表。

## 3. 局部proof不能简单按ceil(log n)或S永久上界计费

局部树以power-of-two补齐，完全padding子树为已知常量。给定slot subset，其canonical multiproof形状由这个公开subset唯一确定；无须发送proof-node IDs。

令

    w(n,k)= average_(uniform k-subsets) |canonical witness nodes|,
    c_n= number of nonconstant local nodes
       = n + sum_(i=1)^ceil(log2 n) ceil(n/2^i).

代码对n<=9枚举所有subsets，获得精确有理数w。因为ReadBucket的完整物理subset为均匀Z-subset（证明见认证文件），这些均值与秘密real数量无关。不同used histories条件下subset来自未消费位置；对隐藏随机排列平均后，整体仍为uniform subset。因此logical单slot使用w(n,1)，RMW/neutral使用w(n,Z)。

这相对于旧表的ceil(log n)、S常数上界更紧。**增加framing后总数仍可能下降**，因为另一项从保守上界改成了精确平均；不能把两次表格的差误当成新的data-block优化。

## 4. Path-family表达式

令n=L+1，k=|mask|。SDE融合logical read+header refresh：

    k*(Z*W+2H) + (3L+2)*h + 184.

Scheduled full-path RMW：

    2n*(Z*W+H) + (3L+2)*h + 184.

184=两次RPC的四个36-byte frame headers，加16+24字节request control。Deferred Full Read令k=n；Standard Path同格式参照每次直接执行一次完整old-path read/write，不再另加logical-only项。

## 5. Ring-family表达式

令q为维护层数（R0为L，rootful为L+1），nslot=Z+S，w1=w(nslot,1)，wZ=w(nslot,Z)。不计neutral时的logical三阶段：

    k*(W+2H)
      + [L+q+k*w1 + k+(L+1)]*h
      + (272+8k).

第一组认证项为header-first的data roots、skipped commitments、off-path siblings和slot witnesses；第二组为刷新后bucket/global tags。272=六个36-byte frame headers及16+16+24控制字段。

Scheduled RMW：

    q*((2Z+S)*W+2H)
      + [2L+1+q*(wZ+c_n+2)]*h
      + (272+8q).

Selected data roots明确包含在header-first部分。没有沿用此前漏掉这一项的(S+1)Lh写法。

在depth d发生neutral，复用已认证的当前path skeleton，但不省略之后的logical one-slot read：

    (2Z+S)*W + H + (wZ+c_n+d+2)*h + 192.

192=两个RPC的四个36-byte frame headers及(16+8)+24控制字段。多个neutral逐次修补同一已认证view；每次上传它改变的真实tags。

## 6. 服务区间平均与有限trace必须分开

对非根完整service间隔，p_d为深度d的GC inclusion probability。由pinned/current等价，某bucket在其两次service之间的eligible leaf subset固定。均匀old leaves命中该bucket且入选的概率为2^-d*p_d。间隔有A*2^d次logical accesses，所以

    X_d ~ Binomial(A*2^d, 2^-d*p_d).

Lazy neutral在第S+1次touch前触发，因此区间内次数为max(0,floor((X_d-1)/S))。该层所有buckets的per-access rate是此期望除以A。

这是**完整service区间的周期平均**，不是任意刚初始化短trace每一步的精确期望。任意有限trace使用第2节的逐帧恒等式，初始化和部分区间均不会丢账。48GiB表为周期平均模型，小实例账本为真实执行；不得把前者写成运行过48GiB的benchmark。

## 7. 平均成本也有明确数值边界

`unified_cost.py`不使用普通float做最终平均：p_d由Fraction automaton递推；(1-p)^n使用100位Decimal、显式向下/向上的二进制幂；Binomial PMF仅正数乘除和求和，分别向外舍入。

截到K=160时，利用整数下降阶乘：x>K意味着x<=(x)_(K+1)/K!，所以

    E[X;X>K] <= (np)^(K+1)/K!.

因为区间reshuffle次数<=X，该式也是遗漏正尾的一阶矩上界。将其向上加入upper endpoint；lower只用已知非负部分。所有最终bytes/access表达式都是这些区间的非负线性组合。程序另外对小n用Fraction完整枚举校验上下端。

## 8. 比较口径

所有表格使用同一SOC2 serializer和PRF profile。主两方案使用同一公开几何、R=(192,144)、B=4096及48KiB terminal map。参照项包含Path/deferred/full-read Ring/full-GC Ring，但：

- Path Z4没有从本GC证书自动获得Path论文Z5的理论参数；本表不声称该参照具有同一已认证overflow风险。
- Full-read Ring参照使用统一的lazy-neutral维护接口，不冒称与原论文所有EarlyReshuffle细节逐状态相同。
- 没有tree-top caching、XOR或全局Z/A/R联合调参，不声称相对全面优化基线的最优性。
- 表中data字节已含nonce；header与authentication分开；control含应用帧而不含传输层。

这使成本证据链完整，而不靠扩张benchmark或基线结论。
