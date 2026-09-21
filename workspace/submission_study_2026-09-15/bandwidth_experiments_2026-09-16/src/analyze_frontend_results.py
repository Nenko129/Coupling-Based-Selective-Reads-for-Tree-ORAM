"""Separate selective, map compression and rho backend-share effects."""
from common import *
from fractions import Fraction as F
from analyze_ablation import summary
import statistics

def main():
    audit=json.loads((PACKAGE/'results/frontend_batch_audit.json').read_text());available={};bindings=[]
    for report in audit['reports']:
        folder='formal_composition' if report['family_group']=='free' else 'formal_rho_fixed'
        for entry in report['rows']:
            p=PACKAGE/'results'/folder/f"{entry['id']}.json";assert sha(p)==entry['sha256']
            r=json.loads(p.read_text());s=r['spec'];available[s['family'],s['workload'],s['kind'],s['trace_seed']]=r
            bindings.append(dict(file=str(p.relative_to(PACKAGE)),sha256=sha(p)))
    compression=[];rho=[];costs=[]
    for workload in ('uniform','hot90','zipf09','scan'):
        for kind in ('deferred','sde','ring','r0'):
            values=[];seeds=[]
            for seed in range(101,106):
                a=available.get(('free_raw',workload,kind,seed));b=available.get(('free_compressed',workload,kind,seed))
                if a and b:
                    assert a['trace']==b['trace'];seeds.append(seed);values.append(100*(1-b['bytes_per_request']/a['bytes_per_request']))
            if values:compression.append(dict(workload=workload,kind=kind,seeds=seeds,**summary(values)))
        for base,new in (('deferred','sde'),('ring','r0')):
            joint=[];decomposition=[]
            for seed in range(101,106):
                a=available.get(('free_raw',workload,base,seed));b=available.get(('free_raw',workload,new,seed));c=available.get(('free_compressed',workload,new,seed))
                if not all((a,b,c)):continue
                assert a['trace']==b['trace']==c['trace']
                x=1-b['bytes_per_request']/a['bytes_per_request'];y=1-c['bytes_per_request']/b['bytes_per_request'];z=1-c['bytes_per_request']/a['bytes_per_request']
                assert abs(z-(1-(1-x)*(1-y)))<1e-12
                joint.append(100*z);decomposition.append(dict(seed=seed,selective_on_raw_pct=100*x,compression_after_selective_pct=100*y,joint_pct=100*z))
            if joint:compression.append(dict(workload=workload,kind=f'raw_{base}_to_compressed_{new}',**summary(joint),decomposition=decomposition))
            breakdown=[]
            for seed in range(101,106):
                a=available.get(('rho',workload,base,seed));b=available.get(('rho',workload,new,seed))
                if not a or not b:continue
                assert a['trace']==b['trace']
                aa=a['phases']['measurement']['bills'];bb=b['phases']['measurement']['bills']
                assert aa[0]['total_bytes']==bb[0]['total_bytes'] and aa[0]['transcript_sha256']==bb[0]['transcript_sha256']
                ta=sum(x['total_bytes'] for x in aa);tb=sum(x['total_bytes'] for x in bb)
                back=F(aa[1]['total_bytes'],ta);gain=1-F(bb[1]['total_bytes'],aa[1]['total_bytes']);overall=1-F(tb,ta)
                assert overall==back*gain
                breakdown.append(dict(seed=seed,backend_share_pct=100*float(back),backend_saving_pct=100*float(gain),overall_saving_pct=100*float(overall),
                                      front_bytes_per_request=aa[0]['total_bytes']/a['spec']['requests']))
            if breakdown:rho.append(dict(workload=workload,baseline=base,selective=new,n=len(breakdown),per_seed=breakdown,
                backend_share_pct=statistics.mean(r['backend_share_pct'] for r in breakdown),backend_saving_pct=statistics.mean(r['backend_saving_pct'] for r in breakdown),
                overall=summary([r['overall_saving_pct'] for r in breakdown])))
    for family in ('free_raw','free_compressed','rho'):
        for workload in ('uniform','hot90','zipf09','scan'):
            for kind in ('deferred','sde','ring','r0'):
                rows=[available[family,workload,kind,seed] for seed in range(101,106) if (family,workload,kind,seed) in available]
                if not rows:continue
                parts=[]
                for r in rows:
                    s=r['spec'];bills=r['phases']['measurement']['bills'];c={k:sum(b['components'].get(k,0) for b in bills) for k in bills[0]['components']}
                    data=c['data_download']+c['data_upload'];assert data%(s['B']+16)==0
                    slots=data//(s['B']+16);parts.append(dict(data_slots_excluding_nonce=slots*s['B']/s['requests'],
                        data_nonce=slots*16/s['requests'],headers=(c['headers_download']+c['headers_upload'])/s['requests'],
                        authentication=(c['authentication_download']+c['authentication_upload'])/s['requests'],
                        framing=c['framing_and_control']/s['requests']))
                mean={k:statistics.mean(x[k] for x in parts) for k in parts[0]}
                assert abs(sum(mean.values())-statistics.mean(r['bytes_per_request'] for r in rows))<1e-8
                costs.append(dict(family=family,workload=workload,kind=kind,n=len(rows),components_bytes_per_request=mean))
    save(PACKAGE/'results/frontend_effects.json',dict(compression=compression,rho_backend_effects=rho,cost_breakdown=costs,
        receipt_bindings=bindings,audit_sha256=sha(PACKAGE/'results/frontend_batch_audit.json'),
        note='data slots include real and dummy slots; data nonce separated; header nonce remains in headers'))
    md=['# 前端压缩及ρ分账','','所有均值来自配对运行；n<5的行只作过程记录。此处仍是实现的受限组件，不是完整原生系统复现。','',
        '| 负载 | 后端/联合步骤 | n | 通信节省 | 95%区间 |','|---|---|---:|---:|---|']
    for r in compression:
        ci='待五次' if r['ci95'] is None else f"[{r['ci95'][0]:.2f}%, {r['ci95'][1]:.2f}%]"
        md.append(f"| {r['workload']} | {r['kind']} | {r['n']} | {r['mean']:.2f}% | {ci} |")
    md+=['','普通后端名表示raw map→compressed map；联合步骤先加selective，再压缩。两项条件节省按乘法合成，不能相加。','',
         '| ρ负载 | 基线→selective | n | 优化前后端占比 | 后端自身节省 | 总体节省 |','|---|---|---:|---:|---:|---:|']
    for r in rho:md.append(f"| {r['workload']} | {r['baseline']} → {r['selective']} | {r['n']} | {r['backend_share_pct']:.2f}% | {r['backend_saving_pct']:.2f}% | {r['overall']['mean']:.2f}% |")
    md+=['','恒等式逐种子精确核对：总体节省 = 优化前后端流量占比 × 后端自身节省。表中均值乘积不必等于乘积均值。前树的完整通信摘要在每个配对中相同。']
    (PACKAGE/'14_前端压缩与rho分账.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(compression_rows=len(compression),rho_pairs=len(rho),cost_rows=len(costs))))
if __name__=='__main__':main()
