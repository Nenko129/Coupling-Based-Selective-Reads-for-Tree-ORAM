# 静态树顶缓存的实际通信适配

2026-09-16。此处实现公开固定前缀 `depth < cut` 的可信缓存，不改变逻辑访问、fresh remap、uid、GC放置或维护时钟。IR-Stash的“命中即取消访问/不remap”规则尚未被实现或证明。

## 数据究竟保存在哪里

缓存存放顶部桶的原有ciphertext/header/local authentication与对应global tags。远端对象表只保存 `depth ≥ cut` 的桶，没有指向可信缓存的引用。所有跨边界请求和回复重新序列化，由独立远端parser实际处理，计费使用这些帧的真实长度；没有事后从全路径通信表中减去一笔估算缓存收益。

初始化沿原算法从底向上进行。顶部INIT完全在客户端安装；其余INIT发送远端。OPEN只请求远端被选桶、远端未选桶承诺和必要的远端sibling tags；客户端加入自身缓存的片段，得到原协议完全相同的逻辑reply。READ_SLOTS对远端槽位真实发送请求，纯本地槽位读取没有外部RPC。WRITE只把远端变化和远端global tags发给服务器，本地变化在外部ACK通过之后安装。

## 完成态与认证的归约

将“可信缓存记录 + 远端记录”合并为虚拟完整服务器。归纳起点是原有物理初始化；每次OPEN/READ_SLOTS重建的逻辑reply与该虚拟服务器相同；每次WRITE把相同record/global tag分别装到两份互斥的对象表。因此客户端看到相同逻辑frame、生成相同nonce与随机样本、验证相同根，并得到相同完成态。

缓存决策只依赖公开depth/cut，实际跨边界transcript由原完整transcript按固定字段长度与公开mask删去顶部片段、重编号外部sequence即可得到。被删掉的物理请求不向服务器透露本地命中情况；本地命中不取消逻辑请求或fresh remap。该公开变换给出被动transcript模拟；对于主动远端修改，可以在原模型中构造一个维持顶部诚实状态、转发下部修改的完整服务器。收到的远端frame先检查opcode/tree/sequence/长度，再重建逻辑reply；原认证逻辑随后检查完整根和所有槽位证明，全部通过才解密。异常导致顶层客户端fail-stop，没有重试或nonce回滚。远端WRITE ACK错误时不提交本地缓存更新。

本推导只继承原协议已经适用的保证。缓存并未解决非均匀Z的新容量证书、原生IR-Stash命中取消、set conflict、DWB或AB的green/DeadQ机制。缓存根与删去根容量不同：缓存保持逻辑根容量，R0仍然为零根容量；计费时顶部本来就在本地，不能再宣称删根节省了同一笔远端payload。

## 验证范围

36组差分涵盖Path/Deferred/SDE/Ring/GC-Ring/R0、逐层Z或S、fusion开/关、cut=0/1/2/L。检查原始逻辑transcript、完成态、完整对象集合、nonce/PRF/sample/decrypt计数逐项一致；cut=0还要求实际跨边界transcript逐字节等于原版本。8组定向远端篡改检查认证拒绝、本地不提交与无重试I/O。结果见 `results/cached_transport_regression.json`。

缓存存储量是实际同时保存的序列化对象内容字节。该值不包括Python容器开销或所有瞬时认证工作区，不能当作真实峰值可信内存。当前需求只报告带宽，最终空间表会注明这一口径。
