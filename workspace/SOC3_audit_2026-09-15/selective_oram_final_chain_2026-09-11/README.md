# Selective ORAM 最终证据链（SOC2 v2）

本包把 **reduction → scalar certificate → recursive driver → authentication → framed cost table** 接在同一公开参数契约上。

## 一条命令重现

环境：Python标准库、支持IEEE-754/OpenMP的g++。本轮实际测试Python3.13与g++14.2。

```bash
python verify_chain.py --recompute
```

该命令编译并重算两个31-level scalar grids，随后执行精确小域检查、reduction接口、加密递归访问、主动篡改、成本逐帧核对及参数gate。无需NumPy、BLAS、FFT或第三方密码包。测试用HMAC-SHA-512来自标准库；这不是对真实HMAC优势的数值认证。

有单次执行时限时，可使用 `--stage certificates --recompute`、`--stage scalar_validation`、`--stage reduction`、`--stage integrated`、`--stage authentication_cost`、`--stage gate`、`--stage cost_table`、`--stage parameters` 分段执行，最后 `--stage assemble`。每个阶段的receipt绑定同一源版本及输出hash，不能混用旧阶段。

只复核已交付的证书和结果身份、不重跑测试：

```bash
python verify_chain.py --stage assemble
```

## 文件导航

- `最终证据链报告.md`：本轮结果、定理量词、统一成本表与证据边界。
- `proofs/01_reduction_complete.md`：逐版本深度支配、commutation、timestamp/marked field、idcx、三状态及root shift的完整补充证明。
- `proofs/02_certificate_recursion_authentication.md`：数值截断上包络、初始化/递归计数、交易边界、认证投影与PRF预算。
- `proofs/03_unified_cost_identity.md`：准确frame grammar、逐trace成本恒等式及周期平均区间计费。
- `src/integrated_oram.py`：实际加密服务器存储、frame parsing、认证path/subset、SDE/R0 core和recursive driver；不使用plaintext server mirror。
- `src/certified_driver.py`：公开配置必须通过同一scalar表与code/profile身份gate；按`L+1,R-offset`取点，运行期限制horizon。
- `src/unified_cost.py`：独立按public shape核对每个帧，生成有向Decimal成本区间。
- `src/chain_tests.py`：外部plaintext/shadow differential oracle与真实加密执行的组合回归。Oracle不向实现提供路径或状态。
- `src/reduction_checks.py`：独立静态/动态/marking接口检查。
- `certificates/`：本轮重算的两个完整CSV及metadata；十六进制binary64是端点依据。
- `results/`：实际运行日志、测试、证书绑定和成本结果。
- `theorem_contract.json`：模型、偏移、算法和证据artifact的SHA-256身份。哈希是复现标识，不是proof-assistant证明或远程attestation。
- `legacy/`：用于复核和外部对照的原代码；它不是集成driver的服务器内存或position map。

## 定理模型必须保留

单个串行可信客户端，不可回滚private state/root/nonce，认证失败或overflow后fail-stop；应用请求不读取ORAM内部随机状态/server-trace来选择地址。覆盖任意独立固定请求流及只适应正确RAM结果的应用。未证明更强server-trace-adaptive stash量词；未实现掉电恢复、并发、多客户端或本地side-channel防护。

完整密码优势是明示PRF假设下的组合结论。`R=(192,144)`、两外部树`L=(23,13),N=(12,582,912,12,288)`、两层4096-byte payload与48KiB terminal map通过主预算。**48GiB表是容量定理和分析成本，不是本容器真的运行了48GiB数据集。**

客户端内存的payload reservation、认证workspace与Python对象开销不是同一口径。成本统计为SOC2应用帧；TCP/TLS、磁盘扇区、重传和CPU时间不在该表中。基线没有tree-top cache/XOR，不宣称全面调优最优性。

`src/seal_contract.py`仅用于审阅修改后重新建立版本身份。不要在没有重新审查证明接口时自动reseal一份修改过的算法；`verify_chain.py`不会静默更新契约来掩盖差异。
