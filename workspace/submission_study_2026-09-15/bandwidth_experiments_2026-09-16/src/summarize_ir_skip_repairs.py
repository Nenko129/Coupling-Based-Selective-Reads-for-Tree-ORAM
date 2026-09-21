"""Bind the exact repair diagnostics and completed encrypted cross-check."""
from common import *
from fractions import Fraction as F
import ir_stash_runtime as rt


def distance(a,b):return sum(abs(a.get(k,F(0))-b.get(k,F(0))) for k in a.keys()|b.keys())/2


def main():
    mp=PACKAGE/'results/ir_skip_repair_exact_model.json';cp=PACKAGE/'results/ir_skip_repair_model_crosscheck.json'
    model=json.loads(mp.read_text());cross=json.loads(cp.read_text());src=Path(__file__).parent
    assert model['model_sha256']==cross['model_sha256']==sha(src/'ir_skip_exact_process.py')
    assert model['gc_source_sha256']==sha(src/'heterogeneous_oram.py')
    assert cross['model_receipt_sha256']==sha(mp) and cross['checker_sha256']==sha(src/'check_ir_skip_exact_process.py')
    assert cross['source_hashes']==rt.identity()
    assert model['status']=='exact_model_evaluated' and cross['status']=='projection_model_crosschecked'
    assert not model['security_admission'] and not cross['security_admission'] and not cross['native_paper_attack_claim']
    assert len(model['rows'])==96 and len(cross['cases'])==42 and cross['executions']==5376
    assert sum(c['executions'] for c in cross['cases'])==5376
    for c in cross['cases']:assert sum(map(F,c['pmf'].values()))==1
    for row in model['rows']:
        if F(row['max_tv']):
            a={k:F(v) for k,v in row['left_pmf'].items()};b={k:F(v) for k,v in row['right_pmf'].items()}
            assert sum(a.values())==sum(b.values())==1 and distance(a,b)==F(row['max_tv'])
    conditionals=[]
    for kind in ('path','deferred','sde'):
        cases=[c for c in cross['cases'] if c['kind']==kind and c['tie']=='uniform']
        assert len(cases)==2 and distance(*[{k:F(v) for k,v in c['pmf'].items()} for c in cases])==F(3,16)
        cases.sort(key=lambda c:c['queries']);pmfs=[{k:F(v) for k,v in c['pmf'].items()} for c in cases]
        assert [c['queries'] for c in cases]==[[0,0],[0,1]]
        weighted=F(0)
        for prefix in ('0','1'):
            masses=[sum(v for k,v in p.items() if k.startswith(prefix)) for p in pmfs]
            assert masses[0]==masses[1]>0
            conditional=[{k[1:]:v/mass for k,v in p.items() if k.startswith(prefix)} for p,mass in zip(pmfs,masses)]
            d=distance(*conditional);weighted+=masses[0]*d
            conditionals.append(dict(kind=kind,first_leaf=prefix,probability=str(masses[0]),
                next_zero_00=str(conditional[0].get('0',F(0))),next_zero_01=str(conditional[1].get('0',F(0))),tv=str(d)))
        assert weighted==F(3,16)
    md=['# IR本地跳过：连续访问反例与修正候选诊断','',
        '结论：目前尝试的随机放置顺序、旧叶dummy和排除本次目标回填，均不足以为本项目IR-Stash跳过适配提供安全修复。它们不进入正式带宽样本。现有无skip IR流水线继续按既定范围运行。',
        '', '## 模型与实际执行分别覆盖什么','',
        '- 精确模型：L1/N2/Z1/A2，根缓存，两个地址，无索引组冲突；按地址保存(uid,leaf,位置)、uid计数、t和gamma。初始两个块依次通过公开路径0接纳。每个叶和放置随机选择均用有理数完全积分，枚举长度1至4的全部请求串。',
        '- 转录投影：每个公共时隙第一个真实远端OPEN帧的叶字段。不利用私有索引或内部日志，转录投影有差异已足以否定相应完整转录同分布主张。投影相等不证明完整安全。',
        '- 加密交叉核对：UID放置下，3后端×3模式×4个两请求序列×64个叶随机带，共2304次；随机平局放置的00/01见证另3072次，总5376次、42个PMF全部与模型一致。每次核对正确payload和公共时钟。',
        '- 其中hold_target仅存在于精确模型：排除本次远端取回/接纳目标的立即Path回填。该局部候选不是原论文完整复现，尚未在加密执行中交叉核对。模型长度3和4也不冒称已经过加密交叉核对。',
        '- 模型回执保留生成时的crosscheck_pending字段；后来完成的交叉核对由独立回执绑定该模型哈希，不改写历史回执。',
        '', '## 具体反例：随机放置顺序仍泄漏重复关系','',
        '随机平局选择使本模型的一请求差异消失，但请求串00和01的两请求路径分布仍不同。Path候选的精确PMF为：','',
        '| 请求串 | 路径00 | 路径01 | 路径10 | 路径11 |','|---|---:|---:|---:|---:|',
        '| 00 | 7/16 | 1/4 | 1/16 | 1/4 |','| 01 | 15/32 | 7/32 | 7/32 | 3/32 |','',
        '二者总变差TV=3/16。事件“路径10”的概率分别为1/16和7/32，事件“路径11”分别为1/4和3/32。Deferred/SDE有不同PMF，但同一请求串对的TV也是3/16。上述三项均由真实加密帧复核。',
        '', '仅把本地命中的dummy改为旧叶，同时不fresh remap，也只是消除单步差异：UID放置下从长度2起TV达到3/8。这里改变的是候选协议，不是原有性能批次。',
        '', '## 全部精确模型结果','',
        '表中数值为该长度全部等长请求串之间的最大TV；零只说明此有限投影未发现区别。no_skip控制使用旧叶读取和fresh remap，不能冒充完成了原生IR的本地跳过优化。','',
        '| 后端 | 排除本次目标回填 | 放置平局 | 本地命中处理 | n=1 | n=2 | n=3 | n=4 |',
        '|---|---|---|---|---:|---:|---:|---:|']
    groups={}
    for r in model['rows']:groups.setdefault((r['kind'],r['hold_target'],r['tie'],r['mode']),{})[r['requests']]=r['max_tv']
    assert len(groups)==24
    for key,vals in groups.items():
        assert set(vals)=={1,2,3,4}
        md.append('| '+' | '.join(map(str,key))+' | '+' | '.join(vals[n] for n in range(1,5))+' |')
    md+=['','## 条件混合分布：修复必须满足的必要条件','',
        '给定公开历史h和下一个逻辑目标a，设H_a表示该目标本地命中，X_a为其当前旧叶，p_a=Pr[H_a|h]，叶数为M。若命中时发独立均匀dummy、未命中时发X_a，那么下一个公开叶L的分布严格为：','',
        '`Pr[L=l | h,a] = p_a/M + Pr[H_a=0, X_a=l | h]`','',
        '证明直接按H_a全概率分解。不可区分要求右式对所有允许目标a相同；仅证明dummy均匀不够，也不能假定stash命中与旧叶独立。若还声称公开叶独立均匀，则额外需要 `Pr[H_a=0,X_a=l|h]=(1-p_a)/M`。后一式是更强的均匀性条件，并不是一般安全定义本身。',
        '因此，在当前第一次OPEN叶已按上述规则选定后才进行的本地fresh remap或回填顺序调整，不能逆向修复该时隙的既有边际差异。改变此前状态分布的策略则必须重新证明整个条件过程；随机平局放置恰好说明单步边际相等仍不充分。',
        '', '对已加密复核的随机平局候选，先执行相同请求0，服务器观察第一条公开路径；随后请求0或1的条件分布如下。两个请求串的第一路径分布相同，每个条件事件具有正概率：','',
        '| 后端 | 已见第一叶 | 该事件概率 | 下一叶为0：请求串00 | 下一叶为0：请求串01 | 条件TV |',
        '|---|---|---:|---:|---:|---:|']
    for c in conditionals:md.append('| '+' | '.join(c[k] for k in ('kind','first_leaf','probability','next_zero_00','next_zero_01','tv'))+' |')
    md+=['', '各后端按第一叶事件概率加权后的TV均为3/16；这说明缺口来自公开历史下的连续相关性，而非仅仅一个初始UID偏置。条件概率在汇总脚本中从42个原始PMF独立计算并校验。',
        '', '## 对下一步协议设计的约束','',
        '需要证明给定完整公开历史后，本地命中分支和远端访问分支的混合转录分布不依赖逻辑请求；不能只证明每个dummy叶本身均匀，也不能只验证单请求边际。stash命中由过去随机叶与放置产生，因此不同于仅按逻辑地址历史替换的PLB/LLC缓存。',
        '后续应对齐原文目标排除、置换和命中处理的完整状态机，再设计fresh remap、父map更新与本地owner保持的联合过程；对每个候选保留连续请求串检查，并审查模拟、stash容量和主动认证。公开时隙必须包含所有填充，避免将减少逻辑工作直接解释为减少通信。',
        '当前反例针对本项目适配，既不是原生IR-ORAM攻击，也不证明N4096配置具有同样TV；它阻止的是未经证明地推广当前适配安全性。原有无skip、CB、Freecursive、ρ或SOC3的性能记录没有因此自动被否定。',
        '', '## 可复核入口','',
        '- `results/ir_skip_repair_exact_model.json`：96行精确模型结果及最大差异见证。',
        '- `results/ir_skip_repair_model_crosscheck.json`：5376次加密执行，42个PMF、源码与模型绑定。',
        '- `results/ir_skip_repair_evidence_audit.json`：当前源码一致性、概率质量及见证TV的独立复核；不是安全准入回执。']
    doc=PACKAGE/'40_IR连续访问与修正候选诊断.md';doc.write_text('\n'.join(md)+'\n',encoding='utf-8')
    save(PACKAGE/'results/ir_skip_repair_evidence_audit.json',dict(status='evidence_consistent',model_sha256=sha(mp),
        crosscheck_sha256=sha(cp),checker_sha256=sha(__file__),document_sha256=sha(doc),model_rows=96,encrypted_cases=42,
        executions=5376,conditional_witnesses=conditionals,security_admission=False,native_paper_attack_claim=False))
    print(json.dumps(dict(status='evidence_consistent',model_rows=96,encrypted_cases=42,executions=5376,security_admission=False)))


if __name__=='__main__':main()
