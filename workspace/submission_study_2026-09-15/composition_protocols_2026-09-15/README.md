# Selective × Freecursive / ρ：迁移协议研究工件

先读 `02_实验结果与研究结论.md`，再读 `01_迁移接口与参数化证明.md`。所有结果的适用范围是受限研究变体，未完整复现原论文系统；实验使用公开固定测试密钥。

## 文件

| 文件 | 用途 |
|---|---|
| 01_迁移接口与参数化证明.md | 新Transfer契约与相对SOC3的证明连接 |
| 02_实验结果与研究结论.md | 本轮研究结论、比较分母和未闭合事项 |
| 03_可复核数据表.md | 从原始JSON生成的实验明细表 |
| src/transfer_backend.py | 对冻结SOC3原语增加单接纳迁移接口 |
| src/frontends.py | PLB/unified/compressed map与ρ-inspired前端 |
| src/check_prototypes.py | 功能、组重映射、所有权、篡改与fail-stop |
| src/check_transfer_reduction.py | 独立小树exact-home/UID枚举 |
| src/run_experiments.py | 216组配对实验；默认从现有rows恢复 |
| src/long_confirm.py | 8组独立长轨迹暖机敏感性实验 |
| src/certificate_gate.py | 读取冻结网格的条件容量查验 |
| src/summarize_evidence.py | 生成可复核数据表与派生比较 |
| src/validate_package.py | 只读核对结果、来源与已有包；生成本包回执/清单 |

## 运行

需要Python 3.10或以上，计算与验证只使用标准库。工作目录为项目根 `D:\projects\SDE-R0`，依赖同项目下冻结的 `SOC3_audit_2026-09-15`。脚本通过所在位置解析依赖，不能只把src孤立拷到其他深度。推荐用 `-B` 避免向冻结代码目录写入pycache；不要使用会禁用断言的 `-O`。

本次使用的解释器为：

```text
C:/Users/12038/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
```

执行顺序：`check_prototypes.py` → `check_transfer_reduction.py` → `certificate_gate.py` → `run_experiments.py` → `long_confirm.py` → `summarize_evidence.py` → `validate_package.py`。例如：

```powershell
& 'C:/Users/12038/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 'TDSC_SOC3_审阅与投稿方案_2026-09-15/组合协议推进_2026-09-15/src/validate_package.py'
```

`run_experiments.py`检测到已存在的216行后会复用它们并重算summary，**这不构成重新执行216个协议实验**。要从头复现，先在同一父目录复制本文件夹为新名字，在新副本中将results目录改名留存，再按上述顺序执行；原文件夹的证据保留不动。`check_prototypes.py`会创建新的results目录。验证脚本按复制后的目录位置解析本包。

主实验与长实验的JSON记录harness elapsed seconds，仅用于了解运行过程；它不是CPU周期、可信峰值内存或网络延迟。前端PRF等成本尚未形成完整密码调用预算。完整字节账单包含固定认证开销，不能直接替代移植PMMAC后的账单。

本包清单保证文件绑定关系，不表示独立第三方已认可新的普遍性证明。原SOC3的冻结审计和本轮条件复用应分别引用。
