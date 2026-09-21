#!/usr/bin/env python3
from pathlib import Path
from decimal import Decimal,localcontext
import json,hashlib,math,sys
ROOT=Path(__file__).resolve().parent
load=lambda n:json.loads((ROOT/n).read_text())
final=load('results/final_chain_verification.json');bindings=load('results/certificate_bindings.json')
cost=load('results/unified_cost_table.json')['table'];red=load('results/reduction_checks.json')
integ=load('results/integrated.json');base=load('results/unified_measured_ledgers.json');gate=load('results/gate_tests.json')
scalar=load('legacy/scalar_validation_results.json');attacks=load('results/active_attacks.json')
N0,N1=12582912,12288;nodes=(1<<24)-1+(1<<14)-1
server_sde=nodes*(364+4*4112+2*64)
server_r0=(nodes-2)*(364+7*4112+(14+2)*64)+2*2*64

def f(x):return f'{Decimal(str(x)):,.2f}'
def b(c,keys):return sum((Decimal(c['components'][k]['upper']) for k in keys),Decimal())
labels={'path':'Path 同格式参照','deferred':'Deferred Full Read','sde':'SDE-GC-Path','ring':'Full-read Ring（lazy-neutral）','gc_ring':'Full-GC Ring','r0':'R0-GC-Ring'}
rows=[]
for k,c in cost.items():
 rows.append('| '+labels[k]+' | '+ ' | '.join(f(x) for x in [b(c,['data_download','data_upload']),b(c,['headers_download','headers_upload']),b(c,['authentication_download','authentication_upload']),b(c,['framing_and_control']),c['total']['upper']])+' |')
T=integ['totals'];billframes=sum(r['invoice']['events_checked'] for r in base['rows'])
text=f'''# 最终证据链报告：SDE-GC-Path / R0-GC-Ring

日期：2026-09-11；版本 SOC2 v2。契约 SHA-256：`{final['contract_sha256']}`。

## 0. 最终状态与一个必须修正的量词

在本报告明确的模型内，**旧 reduction → 新独立 scalar certificate → 实际 recursive driver → authentication → unified cost table** 已连接到同一实现、同一参数契约和逐帧账本。`results/final_chain_verification.json` 的全部阶段通过；两个完整scalar grid和测试均在本轮实际重新执行。阶段receipt将输入契约及输出hash绑定，不能把修改代码之前的旧测试混进来。

这里的“闭合”是研究级的补充数学证明、可复算浮点上包络和可运行参考实现的一致性，不是proof-assistant全栈形式化或部署安全认证。

**请求量词修正：**正式stash定理覆盖任意与ORAM随机性独立的固定请求流，以及根据正确逻辑RAM结果自适应的应用。它没有证明“请求选择器观察ORAM server transcript/内部随机状态后自适应选址”的更强stash定理。以前不加限制的online-adaptive文字应收紧；不能将固定序列证明通过条件于一个自适应产生的序列直接推广。此处没有声称更强模型下方案不安全，只是不虚构该证明。

## 1. 不再悬空引用旧 reduction

`proofs/01_reduction_complete.md` 给出当前冻结状态机的完整补充推导：

1. 每个current version的leaf相同，并维持 `depth_actual(uid)>=depth_shadow(uid)`（stash=-1）。实际maintenance pool包含于shadow pool；同一不可变uid顺序使subset关系在逐bucket写回后继续成立。因而actual stash中的每个current也在shadow stash。
2. 对每棵hanging subtree，phase-locality保证home输入、packing和向路径边界输出的**多重集合**不变。Finite path读回恰好取回这些输出；与global post-processing在相同边界汇合，得到真正的multiset等式。
3. 固定请求流的版本birth/expiry时间表是确定的，每个token位置只依赖自己的独立fresh label和公开schedule。Leaf回收时只保留至多N个current候选；非leaf使用相隔2^d的child-service窗口。两类bucket都满足mean<=A/2，但没有假设真实bucket loads独立。
4. Exact home自身是record，服务后所有可服务overflow都变成q=0；right-record/left-filler的分支结构精确给出三状态计数。这样将按uid的实际packing，接到数值程序真正计算的对象。

这份补充证明是本轮新增论证，不冒称原Path/Ring论文已直接证明新的GC方案。它也不依赖另外未上传的“完整闭合稿”才能理解关键接口。

### 完整数学链

对层j的completed logical-access检查点t：

```text
S_authenticated,j(t) = S_core,j(t)
                     <= S_shadow,j(t)
                      = F_gj^capacity(Y_j(t)) + fresh_j(t)
                     <= F_gj^Z(Y_j(t)) + delta_kind,

Y_j(t) = sum_i X_ji,     X_ji independent Bernoulli point vectors,
E[Y_jv] <= 3/2,

E[(F_gj^Z(Y_j)-r)_+] <= E[(F_(Lj+1)(P)-r)_+]
                      = H_(Lj+1)(r)
                     <= certified_upper[Lj+1,r].
```

SDE的delta=2；R0的delta=6，其中4来自单个virtual root的pointwise容量差。R0的authentication root不是这个virtual capacity，不能混淆。

## 2. Certificate 使用同一递推并实际重算

```text
U^0=(0,0,0)
Phi(L,R,P)=((sum(R)+L[2]+P-4)_+,L[0],L[1]), P~Poi(3/2)
h = L+1
```

C=280、M=128，两种算术模式各输出{final['certificate_points_per_mode']:,}个height/threshold端点。完整重算得到：

- FE_UPWARD：H24(186)<=1.3052161448694381e-61。
- 逐运算NextUp：H24(186)<=1.3052161665818413e-61。
- 两者共同通过H24(186)<=2^-194。

已知状态表为未归一化subprobability上包络；cap外probability/first moment显式传播；最终取known stop-loss加unknown first moment；没有FFT、没有忽略小概率正状态。Poisson起点由Fraction Taylor界产生。{scalar['exact_rational_inequalities']}个小域精确有理比较通过，线程数1/4输出逐位一致。两种模式共享递推代码，不称为两个完全独立算法。

## 3. 参数不是写在旁边：driver构造会检查

`CertifiedRecursiveORAM`构造前验证`theorem_contract.json`中的源代码/证书身份、Z4/A3/m2、不可变uid、neutral不从stash填充、offset、header/nonce/tag/frame格式。它只按`h=L+1,r=R-offset`取exact dyadic端点，并计算包含正常装载的Q_j。

10个负例检查故意改掉L+1、Poisson rate、tie-break、neutral性质、root offset、header尺寸、服务器生成MAC能力、代码文件、R或horizon，均被拒绝。两个小规模实例通过该**认证参数入口**执行，并在public horizon耗尽时于发出任何I/O之前拒绝后续调用。

## 4. 推荐的两树实例与lifetime

| 层 | Logical blocks | L | Payload | Persistent stash |
|---|---:|---:|---:|---:|
| Data | 12,582,912 | 23 | 4096B | 192 |
| Position-map ORAM | 12,288 | 13 | 4096B | 144 |

Terminal position map为49,152 bytes=48KiB。在线horizon取`2^64-N0-N1`，则Q0=`2^64-N1`、Q1=`2^64`，已经包含bottom-up map与data装载。

| 方案 | Ghost thresholds (data,map) | 两层lifetime overflow upper |
|---|---|---:|
| SDE | (190,142) | {bindings['sde']['total_stash_lifetime_upper']} |
| R0 | (186,138) | {bindings['r0']['total_stash_lifetime_upper']} |

不需要层间或时间独立性，使用first-overflow coupling和union bound即可。

仅计persistent payload和terminal map，reservation为1,425,408 bytes（1.359375MiB）；metadata、keys、hash scratch和Python对象开销另计。Conservative transient payload为SDE97 blocks、R093 blocks，另加认证/加密scratch。不能把这些逻辑reservation写成实际Python进程峰值。

按当前固定对象格式计算，两个外部服务器树的持久化**认证对象字节**约为SDE {server_sde/(1<<30):.3f}GiB、R0 {server_r0/(1<<30):.3f}GiB；不含文件系统/对象索引/allocator开销。这也说明48GiB是逻辑payload容量而非物理服务器内存。本容器没有执行该大实例。

## 5. Recursive driver 和authentication已经融合

`src/integrated_oram.py`的执行路径不保存完整非终端position map，也不从plaintext server mirror查询目标。Server只含公开config、ciphertext bytes与client-supplied tags。逻辑地址、fresh leaf、UID和live metadata只存在于可信stash/terminal map或加密header里。

每次顶层请求每层恰好一次atomic read-modify access；下层先返回旧map block并写入新entry，上层再使用旧leaf。所有层完成前不返回应用结果；失败永久fail-stop，不在混合map/data状态继续运行。不能将这解释成已实现掉电恢复或并发事务。

SDE读selected buckets全部Z ciphertexts，固定刷新selected headers、不改data；R0先认证headers再按秘密pointers选取slots，认证包括dummy在内的全部取回slots后才解密payload。Neutral多次发生时，逐次修补已认证path view；scheduled eviction另取当前认证path。三类generation/version分别更新。

PRF research profile中每个header=364B、data=B+16B、tag=64B、frame header=36B。所有改动的local/bucket/global tags由客户端上传，不假定服务器免费计算带密钥的MAC。

## 6. 统一成本表来自相同的serializer

每条RPC均记录真实request/response长度及hash；独立invoice仅依据公开shape重算data/header/auth/control数量，逐笔核对

```text
len(request)+len(response)
  = data_down+data_up+header_down+header_up+auth_down+auth_up+control.
```

对任意有限trace这是恒等式，不依赖随机工作负载。下表则是主两树配置的**完整service区间周期平均**，不是短初始化trace的逐时刻期望，更不是48GiB实测延迟。局部multiproof平均大小精确枚举，Binomial平均使用100位有向Decimal，并显式加入截断尾上界。

| 方案 | Data含nonce | Headers | Authentication | Framing/control | 合计 bytes/access，约 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

表内SDE相对同格式Path参照约省36.19%，相对Deferred约省24.66%；R0相对同格式Full-read Ring约省22.81%。这些只对本表profile成立，不覆盖tree-top caching/XOR或全局参数优化。Path Z4参照未从GC证书自动取得同一failure保证；Full-read Ring采用统一的lazy-neutral接口，不冒称原论文每个操作细节完全不变。

TCP/TLS/Ethernet、重传、设备块对齐和CPU不在该应用协议字节表中。和上一轮仅object-byte上界相比，新增了frame/control，同时把ceil(log n)/S局部proof上界换成精确subset平均，因此总数变化不是新的real-block优化。

## 7. 密码预算已接入，但PRF仍是明确假设

```text
Adv_ORAM <= 2 epsilon_F + q_F^2 / 2^511
            + 2 B_stash + q_F*9! / 2^513.
```

每层一次Access的粗上界<2^18次PRF，物理dummy初始化每bucket<2^11次，initial-label派生另外计数。主两树实例合计

```text
q_F <= {bindings['r0']['primitive_calls_upper_integer']} < 2^84.
```

在相应时间、query count和input-length范围内明确假设每个PRF hybrid的epsilon_F<=2^-132，得到：SDE完整上界{bindings['sde']['conditional_ORAM_advantage_upper']}，R0为{bindings['r0']['conditional_ORAM_advantage_upper']}，二者都<2^-128。

这不是把HMAC-SHA-512的名称或512-bit输出长度当作已证concrete advantage。测试使用确定性公开fixture keys便于复现，**不能部署这些测试key**。实际调用者必须提供独立秘密key。本包没有宣称自制profile是标准AEAD套件。

## 8. 最后一轮实际复跑的证据

- 双scalar grid各{final['certificate_points_per_mode']:,}个点；160个Fraction小域比较。
- 加密递归主回归{T['top_requests']:,}次顶层请求，其中小树差分oracle覆盖{T['layer_accesses']:,}次层访问（含该批setup）；另含4096B payload案例。
- {T['per_token_depth_comparisons']:,}项逐current-token深度关系，{T['canonical_comparisons']:,}项canonical packing对应，{T['field_recurrence_comparisons']:,}项shadow field到三状态递推等式。
- 主回归{T['frames_checked']:,}笔实际RPC账单逐项核对；另有六个同格式方案合计6,000次顶层请求的实执行账本（{billframes:,}笔RPC）。
- 静态field/class、priority count、commutation分别{red['static']['static_class_equalities']:,}项，root shift {red['static']['root_capacity_shifts']:,}项；固定历史marking检查{red['marking']['time_snapshots']:,}个时刻。
- 20个主动故障/重放/guaranteed-dummy用例；跨层部分执行失败保持committed anchor不变且后续零I/O。
- 987个局部subset openings；168个exact Binomial interval checks；10个参数或契约负例。

这些不是极小概率的实验估计。极小概率来自已证明的reduction和scalar上包络；执行回归用于对齐实际状态机、认证和计费。也不把带外debug oracle的运行时间当性能benchmark。

## 9. 可复现执行及scope结束点

```bash
python verify_chain.py --recompute
```

也可以分stage执行，最后`--stage assemble`；每个receipt绑定同一个contract hash及对应输出hash，缺少阶段、源版本不同或输出被改动都会拒绝。当前交付的最终gate记录`chain_consistency_passed=true`、`fresh_full_certificate_recomputation=true`、`fresh_test_execution=true`。

**本轮主线不再留下“认证容器与plaintext driver尚未融合”“成本表来自另一份未执行公式”“等待另外一份旧证明稿说明actual-to-ghost”的断点。**保留的是模型边界和通常的密码假设：更强server-trace-adaptive stash量词、crash recovery、并发、本地side channel、全尺寸公平性能优化、以及proof-assistant/部署审计均未被包含或冒充完成。

## 来源定位

- Ring ORAM《Constants Count: Practical Improvements to Oblivious RAM》，Appendix A的metadata/ReadBucket与Appendix B的mapped-leaf stale和timestamp/load。
- Path ORAM，JACM2018，§4 recursive atomic partial write，§5 fixed-order post-processing，§6.4 integrity with freshness。
- `gap_m2_uniform_time_theorem_draft_v2.md`，§1–6：leaf anchor、canonical、marked-Poisson idcx和三状态。
- 9月3日双路线报告，§2、§4：SDE/R0状态机；§9与附录B：原有证据边界。
- RFC2104：HMAC安全性依赖底层密码性质；RFC5116：AEAD接口不包含anti-replay。
- 本轮新增证明、实现和计算均在本包列出，不应反向归因给这些原始来源。
'''
(ROOT/'最终证据链报告.md').write_text(text)
# Human/machine evidence ledger uses current output identifiers; no guessed paths.
ledger={'contract_sha256':final['contract_sha256'],'primary_status':final,'protocol_instances':bindings,
        'source_inputs':{}}
for name in ['path.pdf','ring.pdf','gap_m2_uniform_time_theorem_draft_v2.md','Selective_ORAM_双路线完整研究报告_2026-09-03.pdf','Selective_ORAM_Closure_2026-09-11.zip']:
 p=Path('/mnt/data')/name
 ledger['source_inputs'][name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
(ROOT/'evidence_ledger.json').write_text(json.dumps(ledger,indent=2))
print('Report written:',len(text),'characters; base ledger frames:',billframes)
