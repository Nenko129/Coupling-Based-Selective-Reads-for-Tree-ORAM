"""Publish every CB/pressure pilot cell, with no CI or formal-system claim."""
from common import *
import csv
from audit_ab_cb import inputs,audit_record,matched


def main():
    rows=[];receipts=[];missing=[];plans=[]
    for name in ('pilot_ab_cb_plan.json','pilot_ab_pressure_plan.json'):
        plan,kwargs=inputs(name);plans.append(dict(path=name,sha256=sha(PACKAGE/name)))
        for s in plan['specs']:
            p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
            if not p.exists():missing.append(s['id']);continue
            r=json.loads(p.read_text());audit_record(r,s,**kwargs);rows.append(r)
            receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    byid={r['spec']['id']:r for r in rows};out=[]
    for item in receipts:
        r=byid[item['id']];s=r['spec'];p=r['phases']['measurement'];m=p['frontend_metrics'];hist={int(k):v for k,v in p['boundary_stash_histogram'].items()}
        out.append(dict(id=s['id'],kind=s['kind'],layout='uniform' if s['bottom_dummy'] is None else 'bottom_d0',
            pressure_high=s['pressure_high'],pressure_low=s['pressure_low'],N=s['N'],B=s['B'],L=s['L'],R=s['R'],
            requests=s['requests'],public_slots=p['public_slots'],bytes_per_request=r['bytes_per_request'],rpc_per_request=r['rpc_per_request'],
            measurement_background_slots=m.get('background_slots',0),warmup_background_slots=r['phases']['warmup']['frontend_metrics'].get('background_slots',0),
            measurement_green_promotions=p['cb_metrics'].get('green_promotions',0),measurement_background_green=m.get('background_green_promotions',0),
            measurement_boundary_stash_max=max(hist),measurement_boundary_stash_mean=sum(k*v for k,v in hist.items())/p['public_slots'],
            setup_boundary_stash_peak=r['setup_peak_boundary_stash'],all_phase_boundary_stash_peak=r['max_boundary_stash'],
            server_serialized_bytes=r['server_storage']['total_bytes'],cache_serialized_bytes=r['cache_representation']['bytes'],
            source_path=item['path'],source_sha256=item['sha256'],sample_class='single_seed_pilot'))
    table=PACKAGE/'tables/AB_CB_18_pilot_runs.csv'
    with table.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    pairs=[]
    for r in rows:
        s=r['spec']
        if s['kind']!='ring':
            base=next((a for a in rows if a['spec']['kind']=='ring' and a['spec']['bottom_dummy']==s['bottom_dummy'] and a['spec']['pressure_high']==s['pressure_high']),None)
            if base:
                matched(base,r,'backend');pairs.append(dict(axis='backend',baseline=base['spec']['id'],variant=s['id'],saving_pct=100*(1-r['bytes_per_request']/base['bytes_per_request'])))
        if s['pressure_high']==24:
            base=next((a for a in rows if a['spec']['kind']==s['kind'] and a['spec']['bottom_dummy']==s['bottom_dummy'] and a['spec']['pressure_high'] is None),None)
            if base:
                matched(base,r,'pressure');pairs.append(dict(axis='pressure',baseline=base['spec']['id'],variant=s['id'],saving_pct=100*(1-r['bytes_per_request']/base['bytes_per_request'])))
    save(PACKAGE/'results/ab_cb_pilot_summary.json',dict(status='complete_pilot_audited' if not missing else 'partial_pilot_audited',
        expected=18,completed=len(out),missing=missing,plans=plans,receipts=receipts,rows=out,pairs=pairs,table_sha256=sha(table),
        generator_sha256=sha(__file__),auditor_sha256=sha(Path(__file__).parent/'audit_ab_cb.py'),formal_estimate=False,security_admission=False))
    md=['# AB-CB递归集成与压力诊断（试运行）','',
        f'已审计 {len(out)}/18 个预先具名的试运行。均为单一种子，不给置信区间，不进入正式性能主表。',
        '', '## 执行契约','',
        'N512、64B、X16、547个数据与raw位置表记录、L8、装载率2.13671875；C5/A5/Y4，常规D3/τ7，底三层D0/τ4。前3层缓存、PLB4、LLC8×2、R500。64次暖机/1024时隙，128次测量/2048时隙；请求间隔8，末尾公共padding所有组相同。',
        '压力开启时采用私有high/low滞回，所有公开时隙均执行一次普通CB Transfer；后台可搬出green，不能称为原生严格只读dummy策略。',
        '', '第一批H48/L32在测量阶段没有后台维护，因此后续预先声明H24/L16及关闭压力两个诊断设置。该选择是在看到第一批行为后作出的，不能叫独立调优结果；全部后续单元均保留。',
        '', '| 布局 | 阈值high/low | 后端 | bytes/op | RPC/op | 后台时隙 warm/meas | 测量边界stash最大值 | 服务器对象字节 |',
        '|---|---|---|---:|---:|---:|---:|---:|']
    for x in out:
        threshold='关闭' if x['pressure_high'] is None else f"{x['pressure_high']}/{x['pressure_low']}"
        md.append(f"| {x['layout']} | {threshold} | {x['kind']} | {x['bytes_per_request']:,.3f} | {x['rpc_per_request']:.3f} | {x['warmup_background_slots']}/{x['measurement_background_slots']} | {x['measurement_boundary_stash_max']} | {x['server_serialized_bytes']:,} |")
    md+=['','## 解释边界','',
        '同一条件下，配对的有用remove/admit子序列、LLC和前台工作量保持相同。后台插入会改变有用操作在公共时隙中的位置，因此不强行要求包含所有dummy的全时序摘要相同。',
        '固定W/Q时，后台通常替换已有dummy时隙。出现后台维护不意味着总字节一定增加；不同随机路径与neutral次数可产生正负微小差异。当前压力诊断用于确认机制实际触发，不据此声称新带宽收益。',
        'H不是stash的硬容量上限：它在时隙边界检查，一次Transfer可使占用越过H；初始化也发生在控制器接入前。不能把测量边界最大值、H或者R当作真实可信峰值内存。',
        '缓存层数相同，Ring和GC-Ring缓存对象13972字节，R0缓存12104字节；相差1868字节是根只保留两个认证tag造成，未再利用省出的空间。PLB/LLC/stash预算相同。',
        '该CB协议仍无green容量证书或完整自适应安全证明；DeadQ未实现。少量经验零溢出不证明容量安全，旧Y0静态AB结果不能替代当前组合。',
        '', '## 证据与审计','',
        '`tables/AB_CB_18_pilot_runs.csv`提供全部行、原始文件和hash，`results/ab_cb_pilot_summary.json`提供所有可配对的后端/压力差分。',
        '`audit_ab_cb.py`重算答案、几何、时钟、分项账单和真实序列化存储；21个损坏证据拒绝检查见 `ab_cb_audit_checks.json`。这是收据审计，原型计量器在执行时独立核每个帧，不是保存完整线缆trace后的第三方重放。',
        '压力批次首次派发在第一条成功执行后被审计器拦下：驱动内存态的tuple与已落盘JSON的list表示不同。已改为始终审计落盘收据，原行通过；未改执行算法、参数、输入或结果，未重跑首行。失败记录保留为 `results/ab_pressure_pilot_failure.json`，属于审计连接错误，不是ORAM失败。',
        '', '下一阶段仍要完成目标规模与五次重复、原生后台策略/安全准入、DeadQ所有权与认证账单，再决定可进入论文主表的范围。']
    (PACKAGE/'24_AB_CB递归集成与压力诊断.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=len(out),expected=18,pairs=len(pairs))))


if __name__=='__main__':main()
