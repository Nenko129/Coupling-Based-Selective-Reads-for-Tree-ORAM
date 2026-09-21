# SOC3 有限闭合：审计结论与证据索引

本轮只处理用户指定的前三项。结论针对当前研究模型，证据分为数学论证、代码接口和可复现计算；不能以摘要数值一致替代其中任一层。

## 1. Fusion

现有生产 `fused_logical.py` 无需改算法。补齐了 [完成态等价与模拟证明](proofs/01_fusion.md)：

* 触发 neutral 时旧 unused 集合大小正好 Z，取回全部 live；新排列中仍虚拟消费 target slot 或 dummy slot。
* neutral 桶最终为 gamma 不变、w+1、v+2、count=1、used={j}；普通 selected 桶 w 不变、v+1、count+1。新 full-write 仍包含已被虚拟消费的 ciphertext，而 descriptor 已失效。
* 保留中间 header 的 nonce 消耗；事件带重排耦合保证完成态分布等价，不误称同一 key 下密文和排列逐字相同。
* 对 target 在桶内、其它桶、stash 和不存在分别证明公开 j 的均匀性及剩余 live 注入不变量；处理多个 neutral、混合 opening、持久 ciphertext 相等关系和公开 nonce 间隔。
* 完整 global opening 先于 header 解密，全部 local openings 先于任何 payload 解密；fresh remap 在递归访问前采样，失败不回滚 working state，提交边界后才成功返回，失败后禁止再发 I/O。

[Fusion receipt](receipts/final_run/fusion.json) 包含12个定向局部状态对照、4组共720次在线递归 U/F 配对请求（另计装载），逐操作比较 headers/records/stash/position map/nonce/sample 完成态；42种保留 record 身份的有限配置给出7,345条 exact rational 分布等式；12类主动/错误前缀检查包括多桶末端坏 opening、dummy、ack、递归 map 已推进后的父层拒绝、stash overflow。

测试事件带只用于对照；实际协议 PRF 未修改。定向 fixtures 检验满足局部不变量的状态；任意可达历史的结论来自证明及完整初始化/在线配对执行。

## 2. Z7/A6 reduction 和新证书

[参数化证明](proofs/02_parameterized_reduction.md) 将每一接口显式提升为 Z/A：actual/current 深度支配、同 uid canonical packing、独立版本单点标记、A/2 均值、idcx、ΦZ、root shift 和 fresh tokens。实例化得到 **Φ7、Poi(3)、δR0=12、h=L+1**。

[数值审计](proofs/03_numerical_audit.md) 和 [数值 receipt](receipts/final_run/numerical/receipt.json) 不依赖原 summary 的 PASS：

* 从整数有理数重新证明 exp(−3) seed 的区间并核对 C++ header/JSON。
* C8/H4/M8 独立 Fraction tuple×tuple×arrival 枚举，对两模式各660个完整 joint tuples 检查上包络；连同 mass/mean/ep/em/δ/m/stop-loss 共1,512项包络与紧致性检查。第4层 cap-exit 非零，Poisson tail 也非零。
* 五类故障 kernel 均被拒绝：rate=1.5、Φ4、first-moment rate=1.5、cap-exit Z4、联合状态坐标错误。M=6 guard 和1/4线程一致性也核验。
* 原 kernel 从源码重编译，两种算术模式各6,744个全量点重新计算，与原包 hex endpoints 一致；再用 exact dyadics 检查每模式24层的 unknown probability / first-moment 传播使用 rate3。
* gate 的完整点域、seed/model 元数据、各非负分量得到收紧；h25/h31、r281、负阈值等非平凡 Z7 请求被拒绝。h25 且 R≥N 的例外明确标为 deterministic count bound。

主 Z7 512-map 的 data 点为 `(23,137)`，map 点为 `(16,135)`；两者均在 h≤24 的实际证书中。精确 lifetime 预算与 qF、PRF 假设均在 [整合 receipt 的 profiles](receipts/final_run/integrated/receipt.json) 重新计算，不由展示用 decimal 决定。

## 3. 原包取得、整合和可独立审计性

原 SOC3 proof note、code、grid/verifier、profile_comparison、contract、receipts 已逐一读取并核验，完整存放于 [received ZIP](provenance/SOC3_received.zip)。原 SOC2 的77项 manifest 与 SOC3 的24项原 contract 保持可核对；未用新合同追认旧文件的未经声明修改。

发现并修正的问题是：测试中存在 D 盘绝对路径；gate 对新证书域/seed 的表达不够明确；fusion 旧证明过粗。审计版本修改测试的依赖定位与 gate 的输入校验/结果标注，并添加详细证明及独立检查器。协议、fusion、cost、生产数值 kernel 均原样保留。[逐文件差异清单](provenance/changes.json) 记录所有修改。

新 contract 绑定研究范围、28项代码/证明/数值/配置资料；全包 manifest 再绑定原材料、新审计器、完整 receipts 和 sources。复核入口不会自动重新 seal。12个 variant 的完整成本分项和精确容量计划已重新计算；有限实际执行再次对照原 current/shadow/field 外部 oracles。

最终包在另一个解压路径重新进行 verify/完整复核，且研究模块导入位置全部检查在解压目录内。重现无需原 D 盘项目或摘要作者的未提供附件。传输时应同时核对交付消息中的 ZIP SHA256；只验证一个可被同时替换的本地 manifest 不能鉴别来源。

## 4. 可以写与不能写

可写：“SOC3 在已声明的固定历史、串行非回滚 fail-stop 模型及 PRF 假设下，具有展开的 fusion/reduction 证明、经独立有理枚举复核的 Z7/A6 数值上包络，以及可从源码重现的整合证据包；新 Z7 数值域止于 h=24。”

不能写：“已经获得外部第三方审计签署”“proof-assistant 全栈形式化”“h>24 的 Z7 新证书”“已实测 latency/峰值可信内存提升”或“全局最优的公平 baseline”。这轮补的是前三项有限闭合依据；论文 evaluation 的后续义务仍保留。
