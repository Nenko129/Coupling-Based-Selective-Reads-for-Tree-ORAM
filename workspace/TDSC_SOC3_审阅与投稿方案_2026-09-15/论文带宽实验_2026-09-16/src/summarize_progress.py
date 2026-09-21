"""Only authoritative completed receipts enter tables; pilots stay separate."""
from common import *
from collections import defaultdict
import statistics,math,time

def read_runs(folder):
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((PACKAGE/'results'/folder).glob('*.json'))]

def main():
    pilot=read_runs('pilot');component=read_runs('pilot_components');core=read_runs('formal_core')
    composition=[r for r in read_runs('formal_composition') if r['spec']['family']!='rho']+read_runs('formal_rho_fixed')
    text=['# 实验进度与预试验表','',f'生成时间：{time.strftime("%Y-%m-%d %H:%M:%S")}。**进行中；以下预试验不用于最终论文主结论。**','',
          f'基础预试验已完成 {len(pilot)}/8，静态 IR/AB 预试验 {len(component)}/8；正式基础对比完成 {len(core)}/60，扩大组合批次完成 {len(composition)}/240。',
          '', 'ρ正式批次在扩大热点/Zipf测试中发现Path前树的stash替换检查错误，已用可达反例修复；全部80个ρ观察统一重跑。旧收据/失败保留为历史，不进入本表正式统计。',
          '', '正式基础批次为N16384/B4096，组合批次N4096/B64；均为warmup2048、measurement4096、五个独立运行。所有表中的bytes为实际应用帧总通信，包括认证和维护。','',
          '## 基础预试验（单次运行，64次warmup、128次measurement）','',
          '| 方案 | N | B | 实际 bytes/op | 周期模型 bytes/op | 实测相对模型差异 |','|---|---:|---:|---:|---:|---:|']
    for r in pilot:
        s=r['spec'];m=float(r['expected_periodic_cost']['total']['upper'])
        text.append(f"| {s['kind']} | {s['N']} | {s['B']} | {r['bytes_per_request']:,.2f} | {m:,.2f} | {100*(r['bytes_per_request']/m-1):+.3f}% |")
    text+=['','模型为完整服务区间期望，实际值为有限前缀；差异不是错误条或安全失败概率。N16384一行包含128块、512B的递归map及512B末级位置表。','',
           '## 静态 IR/AB 预试验（N1024/B64，单次运行）','',
           '| 组件 | 布局 | 后端 | 实际 bytes/op | 模型 bytes/op |','|---|---|---|---:|---:|']
    by={}
    for r in component:
        s=r['spec'];family='IR静态Z' if 'IR_static' in s['id'] else 'AB静态S';variant='逐层' if 'depth_profile' in s['id'] else '同质'
        by[family,variant,s['kind']]=r['bytes_per_request']
        text.append(f"| {family} | {variant} | {s['kind']} | {r['bytes_per_request']:,.2f} | {float(r['expected_periodic_cost']['total']['upper']):,.2f} |")
    effects=[]
    for family,pair in [('IR静态Z',('deferred','sde')),('AB静态S',('ring','r0'))]:
        for variant in ('同质','逐层'):
            if all((family,variant,k) in by for k in pair):
                base,new=(by[family,variant,k] for k in pair);gain=100*(1-new/base)
                effects.append(dict(family=family,layout=variant,baseline=pair[0],selective=pair[1],saving_pct=gain))
                text.append(f'\n{family}、{variant}布局：{pair[1]} 相对 {pair[0]} 的总通信下降 {gain:.2f}%。')
    text+=['','IR此处缩放原论文25层静态Z轮廓；AB仅Z7/A6下S6→底三层S4。两者均无顶部缓存，未实现原生IR-Stash/DWB、CB/DeadQ，不可替代原论文完整系统结果。',
           '', '## 尚未完成的论文证据','',
           '- 正式批次全部运行、五次配对区间、原始trace一致性与前端remove/admit schedule一致性检查。',
           '- compact×fusion两族消融、小map、族重调；双方有限候选调优与规模/块长切片。',
           '- IR/AB的顶部缓存和原生机制逐层集成、新容量/认证准入；不能把本次静态实现标成完整组合闭合。',
           '- 两个公开trace的数据适配已有，但尚未执行；目前适配是command-start-key时间局部性重放，不是完整块设备回放。',
           '- 全部主图、附表、章节文字、最终复现与完整性审计。',
           '', '主目标保持进行中，不能由本文件或某个passed收据推断论文实验已经齐备。']
    (PACKAGE/'02_当前进度与预试验表.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    save(PACKAGE/'results/progress_snapshot.json',dict(pilot_completed=len(pilot),static_component_pilots=len(component),formal_core_completed=len(core),
         formal_core_planned=60,formal_composition_completed=len(composition),formal_composition_planned=240,pilot_component_effects=effects,
         goal_complete=False,scope='snapshot from completed receipts; does not establish liveness of outstanding processes'))
    print(json.dumps(dict(pilot=len(pilot),component_pilot=len(component),formal_core=len(core),formal_composition=len(composition))))
if __name__=='__main__':main()
