"""Bind the complete rho table, independent checks and reviewed vector plot."""
from common import *


def main():
    source=PACKAGE/'results/rho_sensitivity_completed_snapshot.json';a=json.loads(source.read_text())
    check=PACKAGE/'results/rho_sensitivity_checks.json';c=json.loads(check.read_text())
    export=PACKAGE/'results/rho_sensitivity_exports_audit.json';e=json.loads(export.read_text())
    visual=PACKAGE/'results/rho_sensitivity_visual_review.json';v=json.loads(visual.read_text())
    assert a['completed']==180 and a['status']=='complete_receipts_audited'
    assert c['status']==e['status']=='passed' and c['source_sha256']==e['source_sha256']==sha(source)
    assert e['checker_sha256']==sha(Path(__file__).parent/'verify_rho_sensitivity_exports.py')
    assert v['status']=='visually_reviewed' and not v['unresolved_layout_defects']
    assert v['numerical_audit_sha256']==sha(export)
    assert v['svg_sha256']==e['svg_sha256']==sha(PACKAGE/'figures/completed_rho_sensitivity.svg')
    assert v['png_sha256']==e['png_sha256']==sha(PACKAGE/'figures/completed_rho_sensitivity.png')
    md=['# ρ敏感性完整结果与图表核验','',
        '预声明120次新敏感性运行全部完成，复用60次对照，共180份最终收据。九个配置×四后端×五种子，36格绝对成本、18组selective效应、24组参数效应；未触发追加重复门槛。Freecursive的100次新敏感性此前已完成，因此原220次前端敏感性计划已全部收齐。','',
        '## 整体通信收益','',
        'N4096/B64，后树Z4/A3/S4/R256；暖机2048、测量4096请求。n为每个后树Transfer对应的前树Transfer次数，默认LLC32、ρ缓存128、n3。下面都按完整双向应用协议字节统计，包含前树、后树、认证和维护；初始化和暖机单列。','',
        '| 负载与配置 | SDE相对Deferred | R0相对Ring |','|---|---:|---:|']
    order=[('uniform/ratio1','Uniform / n1'),('uniform/base','Uniform / n3'),('uniform/ratio5','Uniform / n5'),
        ('hot90/llc8','Hot90 / LLC8'),('hot90/base','Hot90 / LLC32'),('hot90/llc128','Hot90 / LLC128'),
        ('zipf09/rho32','Zipf0.9 / ρ32'),('zipf09/base','Zipf0.9 / ρ128'),('zipf09/rho512','Zipf0.9 / ρ512')]
    for key,label in order:
        cells=[]
        for base,new in (('deferred','sde'),('ring','r0')):
            effect=next(x for x in a['effects'] if x['name']==f'{key}: {base} -> {new}')
            x=effect['bytes_saving_pct'];lo,hi=x['ci95'];cells.append(f"{x['mean']:.3f}% [{lo:.3f}, {hi:.3f}]")
        md.append('| '+label+' | '+' | '.join(cells)+' |')
    md+=['','方括号是五种子配对95% Student-t区间。上述范围只涵盖预声明的这些配置，不是所有参数/负载的保证，也不代表稳态或延迟。','',
        '## 图与可解释性','',
        '已生成`figures/completed_rho_sensitivity.svg`（字形轮廓化矢量图）及同名PNG预览。左图列18组整体减少率，右图列36格四后端绝对KiB/request；各组使用相同前端设置，均显示95%区间。完整前后树分账和参数变化表保留在50号报告，未只挑收益大的配置。','',
        'Uniform中n1→n3→n5时，SDE整体节省为14.122%→8.290%→5.864%，R0为17.863%→11.647%→8.629%。后端自身节省仍约22%/24.5%，整体减少被不变前树流量摊薄；逐种子已用有理数验证“整体节省=基线后树占比×后树自身节省”。','',
        '扩大Hot90的LLC降低绝对成本，但前后树随帧数一起减少，因此selective整体比例变化很小。缩小Zipf的ρ缓存有时会提高相对减少率，却增加selective方案自身通信。论文需并列绝对成本与相对收益，不能用百分比大小替代总开销比较。','',
        '## 独立核验与范围','',
        '- 全部180份原始收据的输入、源码、返回摘要、RPC连续性、账单分项、几何和对象空间通过检查；独立重放45组缓存调度，核对每帧唯一驻留和前后树remove/admit摘要。',
        '- 36格与42组效应独立重算，六种损坏收据被拒绝。绘图进一步从原始运行重算54组均值及区间，并解析SVG的实际柱宽验证显示值。',
        '- 最终2526×1331 PNG已实际审阅；修正了初稿轴标签与图注的重叠，最终标签、图例、误差线和范围注释清晰。',
        '- 实现仍为地址LRU、公开帧长度、完整可信后树PosMap的ρ-inspired组合，不含原生ECC、set-associative标签或异步控制器。缓存容量变化改变资源；未测真实可信峰值，未声称原生系统复现或新安全归约。','',
        '证据入口：`results/rho_sensitivity_completed_snapshot.json`、`results/rho_sensitivity_checks.json`、`results/rho_sensitivity_exports_audit.json`及`results/rho_sensitivity_visual_review.json`。不要再次启动已完成的sensitivity队列。']
    report=PACKAGE/'55_rho敏感性完整图表.md';report.write_text('\n'.join(md)+'\n',encoding='utf-8')
    save(PACKAGE/'results/rho_sensitivity_completed_evidence.json',dict(status='passed',source_sha256=sha(source),
        checks_sha256=sha(check),exports_audit_sha256=sha(export),visual_review_sha256=sha(visual),report_sha256=sha(report),
        producer_sha256=sha(__file__),runs=180,cells=36,selective_effects=18,parameter_effects=24,svg_bar_widths_checked=54,native_full_system=False))
    print(json.dumps(dict(status='passed',runs=180,figure_series=54,report=report.name)))


if __name__=='__main__':main()
