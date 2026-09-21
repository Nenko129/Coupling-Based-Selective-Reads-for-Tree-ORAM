from pathlib import Path
import sys,json,datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minimal_runtime import *

def main():
    a=json.loads((HOME/'results/analysis.json').read_text(encoding='utf-8'))
    count=sum(1 for p in (HOME/'results/formal').glob('*.json'))
    state=json.loads((HOME/'results/queue_state.json').read_text(encoding='utf-8'))
    formal=[r for r in a['comparisons'] if r['suite']=='formal' and r['baseline']=='base']
    now=datetime.datetime.now().isoformat(timespec='seconds')
    text=f'''# Selective read 通用组合：重新选型与投稿实验准备

更新时间：{now}。正式新批已完成 **{count}/120** 条，状态：{state.get('stage')}。本报告与旧截止快照分开保存；实时进度在 results/queue_state.json。

## 结论

采用你的新目标：证明 coupling-based selective read 可以与有代表性的宿主机制组合，而不要求把整套 SOC3 搬过去。重新核对候选后，继续以 **Freecursive、ρ、IR-Alloc、AB静态桶配置** 为四类代表，优先把 IR/AB 做成安全边界直接、归因干净的组合证据。没有发现更值得现在替换的候选。

Palermo 已自带 ER 后 ReadPath bypass，不能将其重新包装成新增省读；Hitchhiker、Shadow、EP 等保留原生特征后会引入新的调度/副本/维护证明义务。并非不能研究，而是目前没有显示出比 IR/AB 更低成本、更清楚的组合证明优势。

组合主张限定到“代表性机制与受限宿主适配”，不写成四个完整原系统全部复现，也不写成优于所有先进 ORAM。Freecursive/ρ还须明确前端允许公开的长度/时隙信息，不能把后端相对安全直接升级成无条件端到端强ORAM安全。

## 本轮已完成

- 新的候选审阅、四类机制选择、最小协议、投影耦合与转录模拟条件，以及正式论文的表述边界。
- 最小执行适配：**关闭 compact header、fusion、省根、small-map 和 Z7/A6 重调**。共同复用已有认证/序列化基础；IR/AB增加 full_probe 归因对照。
- 772个完成边界投影检查、8个认证破坏与无重试I/O检查、87,380组公开phase/leaf局部覆盖检查。
- Freecursive两臂各完成15次强制group reset、578个后端时隙；调度与答案一致。
- IR正式深度配置重新绑定原异质证书：两种舍入网格共12,506个点、Poisson种子和阈值精确算术复核通过。它是证据重绑定，不冒充新一轮第三方独立DP审计。
- **16/16预实验通过**；136条输入（16预实验+120正式）预检通过，正式队列已启动。
- 绘图、配对分析、停止/追加重复规则、源码和证据审阅包已准备。旧7个冻结证据包514文件核对通过。

## 新性能判断

下表分清模型与观测，所有百分比都是相应宿主全读对照到选择读的总应用层通信减少。

| 对象 | 新最小配置的现有依据 | 判断 |
|---|---|---|
| IR-Alloc | N4096模型：64B约20.51%，4KiB约21.58%；正式重复正在完成 | 有明确收益空间，不需要R0/fusion；不是任意IR端到端系统都超过20%。 |
| AB静态按层dummy | N4096模型：64B约25.03%，4KiB约23.27% | 有明确收益空间；新主比较是Ring→GC-Ring，物理根保留。 |
| Freecursive-style | N128、64B单种子预实验23.63% | 组合执行已跑通；正式N4096结果未齐，不作为最终幅度。 |
| ρ-style | N128、64B单种子预实验8.49% | 总收益受前端开销稀释，不能只报后端省幅。 |

小规模IR/AB预实验分别约20.32–21.95%、24.26–25.14%，与同放置full_probe对照也有减少；这些n=1数字只检查可执行性和量级。完整数值见05，理论口径见06。

'''
    if formal:
        text+='当前正式配对（n<5仅过程记录）：\n\n| 对象 | B | n | 节省 | 95%区间 |\n|---|---:|---:|---:|---|\n'
        for r in formal:
            ci='未达到5对，不生成' if r['ci95'] is None else f"[{r['ci95'][0]:.3f}%, {r['ci95'][1]:.3f}%]"
            text+=f"| {r['family']}/{r['layout']} | {r['B']} | {r['n']} | {r['mean_saving_pct']:.3f}% | {ci} |\n"
    text+='''
## 旧集成研究的变化

IR公开尾部补充批已完成30/30、0个具名失败。计入全部固定尾部后，β14/β4对Deferred分别减少19.2013%/19.1859%，对Path分别9.7573%/9.7401%。这些是较复杂的旧共同配置及DWB/压缩位置表口径，不与本轮纯selective样本混并。

AB+CB、DeadQ以及IR-Stash修复不再是本轮受限组合论文的前置要求。旧原型、失败和反例全部保留；CB容量义务未闭合，不能因为把它移出主线就写成已经解决。

## 阅读顺序与复现

1. [01 候选重评与最终选型](01_候选重评与最终选型.md)：为何保留这四类、其他候选卡在哪里。
2. [02 最小组合协议与证明](02_最小组合协议与证明.md)：核心条件、三臂、耦合、模拟、容量与宿主接口。
3. [03 投稿实验方案与公平比较](03_投稿实验方案与公平比较.md)：8个主配对单元、归因/2×2、计费和图表。
4. [04 论文写法与提交前门槛](04_论文写法与提交前门槛.md)：可写主张、不能写的全称结论和未完成门槛。
5. [05 新最小组合实测](05_最小组合实验结果.md) 与 [06 理论性能预测](06_理论性能预测.md)：严格分开实测、单种子预试验和模型。
6. formal_plan.json / specs / source_lock.json / results：全部运行参数、原始收据和源码绑定。
7. Selective_最小组合审阅包.zip：保留工作区相对结构的源码/证明依赖/预试验/当前正式结果快照；清单可逐文件验证。原论文PDF只索引哈希，不重复分发。

当前figure中的PILOT图明确标明N128、单种子。正式图生成器只有在8个主配对单元均满足5种子及精度规则后才生成主图。

**准备工作已经落实到可运行的实验与审阅材料；新正式实验尚未全部完成，不能今天就宣布投稿数据全部收齐。** 剩余是正式重复、必要的追加重复与最终图表/收据核验。本文若只主张带宽，不需要先攻克完整SOC3移植、并发硬件或真实网络延迟；若再加latency/可信峰值主张，必须补相应独立实测。
'''
    if count==120 and all(r['headline_eligible'] for r in formal):
        text=text.replace('新正式实验尚未全部完成，不能今天就宣布投稿数据全部收齐','新正式实验120/120完成且当前配对精度门槛通过；仍需完成最终正文与图表一致性审阅')
    (HOME/'00_重新评估与实验准备总报告.md').write_text(text,encoding='utf-8')
    print(json.dumps(dict(formal_receipts=count,overview_updated=True)))
if __name__=='__main__':main()
