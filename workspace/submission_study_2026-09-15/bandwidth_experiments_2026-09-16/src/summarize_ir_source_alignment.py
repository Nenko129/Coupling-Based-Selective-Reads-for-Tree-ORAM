"""Summarize source-alignment diagnostics without claiming a native IR attack."""
from common import *
from fractions import Fraction as F
from collections import defaultdict
import ast
import ir_stash_runtime as rt


def tv(a,b):return sum(abs(a.get(k,F(0))-b.get(k,F(0))) for k in a.keys()|b.keys())/2


def main():
    src=Path(__file__).parent
    names=['ir_initialization_alignment_model.json','ir_initialization_alignment_crosscheck.json','ir_z4_skip_projection.json']
    model,cross,z4=[json.loads((PACKAGE/'results'/n).read_text()) for n in names]
    assert model['model_sha256']==cross['model_sha256']==sha(src/'ir_initialization_alignment.py')
    assert model['base_model_sha256']==sha(src/'ir_skip_exact_process.py')
    assert model['prior_receipt_sha256']==sha(PACKAGE/'results/ir_skip_repair_exact_model.json')
    assert cross['model_receipt_sha256']==sha(PACKAGE/'results'/names[0])
    assert cross['checker_sha256']==sha(src/'check_ir_initialization_alignment.py')
    assert z4['checker_sha256']==sha(src/'check_ir_z4_skip_projection.py')
    assert z4['paper_pdf_sha256']==sha(PACKAGE.parent/'细化准备_2026-09-15/literature/pdf/R12_ir_oram_path_access_type_based_memory_intensity.pdf')
    assert cross['source_hashes']==z4['source_hashes']==rt.identity()
    assert cross['executions']==2176 and z4['executions']==2048
    assert not any(r['security_admission'] for r in (model,cross,z4))
    for r in cross['results']:
        pmfs=[{k:F(v) for k,v in c['pmf'].items()} for c in r['cases']]
        assert all(sum(p.values())==1 for p in pmfs) and tv(*pmfs)==F(r['tv'])
    coarse=[];events=[]
    for c in z4['encrypted']:
        p={ast.literal_eval(k):F(v) for k,v in c['pmf'].items()};assert sum(p.values())==1
        if not c['skip']:continue
        q=defaultdict(F)
        for (x,y),v in p.items():q[f'{x>>1}{y>>1}']+=v
        coarse.append(dict(queries=c['queries'],pmf={k:str(v) for k,v in sorted(q.items())}))
        events.append(sum(v for (x,y),v in p.items() if y>=2))
    assert events==[F(9,16),F(3,8)] and tv(*[{k:F(v) for k,v in c['pmf'].items()} for c in coarse])==F(3,16)
    md=['# IR源机制对齐与Z4连续访问诊断','',
        '在不修改任何正式实验worker的情况下，继续检验本项目IR-Stash跳过适配。加入秘密随机初始化顺序、排除本次目标的Path回填后，单请求目标差异消失，但连续请求差异仍存在。另在Z4桶、L2的无容量争用实例中得到可复核见证。当前仍不签发skip安全准入；这些结果不是原生IR论文攻击声明。',
        '', '## 与原文对齐的部分及保留边界','',
        '重新核对[IR-ORAM原文](https://mehrnoosh.net/research/IR-ORAM-HPCA%2722.pdf)：§III-B的装载使用随机块顺序，§II-B的Path回填排除本次目标，§IV-C的本地命中不产生路径访问或重新映射。本轮分别实现前两项，并保留本项目固定时隙下本地命中由独立均匀dummy填充的适配。',
        '这仍未完整复现原文的初始化状态机、递归map、LLC、CPU时序及DWB组合。初始化采用空树接纳，条件于已见两条路径都是0；若初始化打开路径独立均匀，L1事件概率为1/4，L2为1/16。对初始化顺序作秘密均匀混合后，仍在该相同公开前缀下比较两个用户请求串。不能把这一条件实验自动改称原生论文或目标N4096实现的攻击。',
        '', '## 六个Path候选：L1/Z1诊断','',
        '各行n列是该长度全部二地址请求串之间的最大路径投影TV；n1至n4为精确有理数模型。每行n2见证另用真实加密帧交叉核对，共2176次执行。hold-local是额外研究候选，不是原文要求。','',
        '| 策略 | n1 | n2 | n3 | n4 |','|---|---:|---:|---:|---:|']
    grouped={}
    for r in model['rows']:grouped.setdefault(r['policy']['name'],{})[r['requests']]=r['max_tv']
    for name,vals in grouped.items():md.append('| '+name+' | '+' | '.join(vals[n] for n in range(1,5))+' |')
    md+=['', '## Z4实例：差异不依赖单槽争用','',
        '新增独立模型与加密执行采用Path、N2、Z4、A3、R16，项目记号L=2（根深度0、叶深度2，共3层），缓存根一层；两地址初始化顺序秘密均匀，初始化和远端请求均将本次目标保留在stash而不立即回填。全树四叶，每个节点四槽；仅有两个真实块，没有容量争用、组索引溢出或stash溢出。初始公开打开路径为[0,0]。',
        '每一步只需要一个独立均匀四值叶：本地命中时用于dummy，远端命中时用于fresh remap。另一未使用的随机坐标已积分掉，与预先分配两个独立随机数后只使用相应分支同分布。',
        '0/1表示两个逻辑块；定义公开路径区域0为叶{0,1}、区域1为叶{2,3}。从真实远端OPEN帧提取两个叶并投影到区域，得到：','',
        '| 用户请求串 | 区域00 | 区域01 | 区域10 | 区域11 |','|---|---:|---:|---:|---:|']
    for row in coarse:md.append('| '+''.join(map(str,row['queries']))+' | '+' | '.join(row['pmf'].get(k,'0') for k in ('00','01','10','11'))+' |')
    md+=['', '因此，只观察第二条公开路径是否进入区域1，即可区分：请求串00时概率9/16，01时概率3/8，差值3/16。整个两路径分布的TV也为3/16。两串第一条公开路径的区域分布都为(5/8,3/8)，说明只检查第一请求的边际会漏掉差异。',
        '这四个PMF（skip开/关×00/01）各由512次实际加密执行完全枚举，合计2048次；每次返回值和公开时钟正确，并与另一个独立的无密码树模型逐项一致。观察字段来自序列化远端请求，而非客户端命中日志。',
        '', '| Z4模型 | n1最大TV | n2 | n3 | n4 |','|---|---:|---:|---:|---:|']
    for skip in (False,True):
        vals={r['requests']:r['max_tv'] for r in z4['rows'] if r['skip']==skip}
        md.append('| '+('当前skip适配' if skip else '完整访问/remap控制')+' | '+' | '.join(vals[n] for n in range(1,5))+' |')
    md+=['', '完整访问控制在这些有限投影中TV为零，只作对照，不将其重新命名为已修复的本地跳过优化。长度3/4是精确模型结果，未声称已逐一进行加密交叉核对。',
        '', '## 对后续研究的影响','',
        '这些检查排除了“仅隐藏初始化顺序”“仅排除立即回填”“仅随机化放置平局”足以为本适配闭合的解释。Z4实例不需要桶容量不足，因此仅增大stash或避开Z1不能作为该分布问题的修复证明。',
        '后续仍需建立40号文档中的公开历史条件下混合分布不变量，并联合处理fresh remap、父map更新、canonical owner与服务时钟；现有功能正确性和数值容量证书不能替代这个模拟义务。正式无skip IR、压缩map队列以及其他组合仍按各自范围继续，当前新skip不进入论文带宽主张。',
        '', '## 证据','',
        '- `results/ir_initialization_alignment_model.json`：六策略、24行精确模型及见证。',
        '- `results/ir_initialization_alignment_crosscheck.json`：2176次加密执行，模型/实现hash绑定。',
        '- `results/ir_z4_skip_projection.json`：Z4八行精确模型、2048次加密执行及原PDF hash。',
        '- `results/ir_source_alignment_evidence_audit.json`：概率质量、见证TV及区域事件的复算。',
        '', '本轮合计4224次新加密执行。两个实现的交叉检查可供独立复核，不等于已由第三方完成密码审计。']
    doc=PACKAGE/'43_IR源机制对齐与Z4转录诊断.md';doc.write_text('\n'.join(md)+'\n',encoding='utf-8')
    save(PACKAGE/'results/ir_source_alignment_evidence_audit.json',dict(status='evidence_consistent',executions=4224,
        input_hashes={n:sha(PACKAGE/'results'/n) for n in names},checker_sha256=sha(__file__),document_sha256=sha(doc),
        coarse_z4_witness=coarse,z4_second_region1_probabilities=list(map(str,events)),security_admission=False,native_paper_attack_claim=False))
    print(json.dumps(dict(status='evidence_consistent',executions=4224,z4_tv='3/16',security_admission=False)))


if __name__=='__main__':main()
