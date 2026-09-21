# SOC3：前三项有限闭合审计包

2026-09-15。范围：**fusion 完成态/安全证明 → Z7/A6 reduction 与数值证书 → 整合证据可复核性**。本包保留收到的原始证据，并提供可搬迁的复核入口。未新增消融、baseline 搜索、真实峰值内存或网络延迟实验。

先读 [审计结论及逐项证据](AUDIT_REPORT.md)，然后读以下三个证明文件：

1. [neutral/read fusion：状态、随机带、虚拟消费、模拟器和 fail-stop](proofs/01_fusion.md)
2. [参数化 reduction、Z7/A6 offsets、递归与 lifetime](proofs/02_parameterized_reduction.md)
3. [完整 joint PMF、seed、cap-exit 和误差传播核验规则](proofs/03_numerical_audit.md)

数学证明是研究模型下的逐步证明，未做 proof-assistant 形式化；复核由本次工作执行，尚无外部审计者签署。文件哈希和测试 PASS 不单独承担数学证明。

## 一条入口复核

需要 Python 3.10+，仅标准库。完整数值重算另需 Linux/WSL、g++ 和 OpenMP；本次重算使用 g++ 9.5.0、Python 3.12.3。无网络下载或 Python 第三方依赖。

在**解压后的本目录**执行：

```sh
python3 -B audit/run.py --mode verify
python3 -B audit/run.py --mode quick --out ../soc3_quick_recheck
python3 -B audit/run.py --mode all --out ../soc3_full_recheck
```

Windows 的前两条可把 `python3` 换成已安装的 `python`。完整模式在 Linux/WSL 中运行。`--out` 必须是包外的新空目录；它收集新 receipts、原始 witnesses 和日志，交付包保持只读。

* `verify` 核对全包 manifest、SOC2 原 manifest、收到的 SOC3 原 contract/manifest/receipt、审计 contract，以及协议/融合/成本/数值 kernel 未改动的来源身份。
* `quick` 再做实际 U/F 耦合执行、exact finite slot 分布、主动篡改、递归/结构接口、完整配置预算和成本复算、物理证书篡改与高度边界测试。
* `all` 再从源码编译数值 kernel，两模式全量重算；独立 Fraction 枚举完整小域 joint PMF，检查每个 tuple 和所有误差量；运行五类错误 kernel 变异和线程一致性测试。

全量端点与交付网格必须一致，当前工具链实测通过。若其它编译器产生不同 hex endpoints，入口拒绝复用本版 receipt；需要重新审阅舍入/编译假设并发布新版本，不能只比较十进制摘要。

`audit/seal.py` 是维护者创建新版本身份的工具，**不是**验证入口；验证时不应重新 seal。`--building-release` 同样仅用于维护者出包，不能冒充对已冻结版本的验证。原包历史脚本和报告保留供对照；其中旧绝对链接/旧 seal 流程不作为本版重现入口。

## 原始材料在哪里

* [收到的 SOC3 原包](provenance/SOC3_received.zip)：原 proof note、融合代码、数值 source/grid/verifier、profile_comparison、variant contract、receipts 和原输出 manifest，逐字保留。
* [收到文件的哈希](provenance/received_manifest.json)：原 SOC2 与 SOC3 全部来源文件；[本版改动对照](provenance/changes.json) 标出可移植修正、gate 收紧和新增证明。
* [可执行 SOC3](research_20260914/optimization_v1/src/optimized_oram.py)、[融合实现](research_20260914/optimization_v1/src/fused_logical.py)、[新 variant contract](research_20260914/optimization_v1/variant_contract.json)。生产协议、fusion、cost 和数值 kernel 均与原包字节一致。
* [原 profile_comparison](research_20260914/optimization_v1/results/profile_comparison.json)：本次重新计算其中12个 variant 的精确成本与安全预算；历史性能、内存口径不升级。
* [SOC2 完整依赖](selective_oram_final_chain_2026-09-11/README.md)：原 reduction、认证证明、实现、外部 oracles、Z4 certificate 和19项 theorem contract；原77项 manifest 保持一致。
* [原论文/报告/index](sources/README.md)：随包附入两篇 baseline PDF、42页报告 PDF 和原 index.html 作为来源快照。index 内外链/原项目导航不保证离线可用；本次证据重现所需内容全部直接随包提供。
* [本次完整重现 receipts](receipts/final_run/run_receipt.json)：源文件身份、工具链、所有结果和中间 numerical witnesses；[搬迁复核记录](receipts/relocation.json) 记录独立解压目录的复核。

## 必须保留的边界

新 Z7/A6 非平凡数值证书只覆盖 **h≤24（L≤23）、0≤r≤280**；R≥N 是另行标注的 actual current-count 确定性例外。Z4 的 h≤31 网格不扩大 Z7 的域。

结论条件包括固定历史与 ORAM 随机性独立、单客户端串行、可信状态不回滚、失败后永久停止、给定规模上的 PRF 假设。没有并发、掉电恢复、本地时序/内存泄漏或部署安全定理。

性能表保留原有应用帧成本模型。tuned Ring 的约21–23%对比比旧 Ring 的52.88%更适合主文表述，但本轮没有补齐同失败概率的全局公平性证明；缓存/XOR/全部参数搜索、干净消融、真实内存峰值和网络 latency 均继续开放。
