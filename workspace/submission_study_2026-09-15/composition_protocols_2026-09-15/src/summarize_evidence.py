"""Derive comparison tables from executed experiment rows."""
from pathlib import Path
from collections import Counter
import json,statistics

OUT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((OUT/'results'/name).read_text(encoding='utf-8'))
def pct(old,new):return 100*(1-new/old)

def main():
    short=read('experiment_summary.json');rows=read('experiment_rows.json')
    long=read('long_trace_rows.json')
    means={(a['family'],a['workload']):a['mean_bytes_per_request'] for a in short['aggregate']}
    compression=[]
    for workload in ['uniform','zipf','scan']:
        raw=means['free_raw',workload];comp=means['free_compressed',workload]
        compression.append({'workload':workload,'SDE_raw_to_compressed_pct':pct(raw['SDE'],comp['SDE']),
                            'R0_43_raw_to_compressed_pct':pct(raw['R0-43'],comp['R0-43']),
                            'raw_Path_to_compressed_SDE_pct':pct(raw['Path'],comp['SDE']),
                            'raw_Ring43_to_compressed_R0_43_pct':pct(raw['Ring43'],comp['R0-43'])})
    breakdown=[]
    for row in long:
        sums=Counter()
        for bill in row['serialized_bills']:sums.update(bill['components'])
        Q=row['measured_requests'];C={k:v/Q for k,v in sums.items()}
        backend=row['serialized_bills'][-1]['total_bytes']/Q
        breakdown.append({'family':row['family'],'backend':row['backend'],
                          'bytes_per_request':row['bytes_per_request'],'rpc_per_request':row['rpc_per_request'],
                          'backend_bytes_per_request':backend,'backend_share':backend/row['bytes_per_request'],
                          'ciphertext_bytes_per_request':C['data_download']+C['data_upload'],
                          'header_bytes_per_request':C['headers_download']+C['headers_upload'],
                          'authentication_bytes_per_request':C['authentication_download']+C['authentication_upload'],
                          'control_bytes_per_request':C['framing_and_control'],
                          'backend_slots_per_request':[x/Q for x in row['backend_slots_measured']],
                          'component_bytes_per_request':C})
    rho={r['backend']:r for r in breakdown if r['family']=='rho'}
    dilution=[]
    for old,new in [('Deferred','SDE'),('Ring43','R0-43')]:
        before,after=rho[old],rho[new]
        gain_backend=pct(before['backend_bytes_per_request'],after['backend_bytes_per_request'])
        gain_total=pct(before['bytes_per_request'],after['bytes_per_request'])
        assert abs(gain_total-before['backend_share']*gain_backend)<1e-10
        dilution.append({'pair':[old,new],'baseline_backend_share_pct':100*before['backend_share'],
                         'backend_saving_pct':gain_backend,'total_saving_pct':gain_total})
    payload={'compression':compression,'long_trace_breakdown':breakdown,'rho_dilution':dilution,
             'all_costs':'bytes in serialized authenticated application frames, not network latency'}
    (OUT/'results/derived_comparisons.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    lines=['# 可复核数据表','',
           '由 `src/summarize_evidence.py` 从已执行账单生成。单位均为每应用请求的字节；RPC是应用层请求/响应对，不是实测网络往返延迟。',
           '', '## 1. 长轨迹：字节、RPC和账单分解','',
           'N=256，B=64；warmup=1536，measurement=3072，uniform，seed=41。', '',
           '| 前端 | 后端 | 总字节 | RPC | 数据密文 | 桶头 | 认证 | 控制 |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in breakdown:
        values=[r[k] for k in ['bytes_per_request','rpc_per_request','ciphertext_bytes_per_request','header_bytes_per_request','authentication_bytes_per_request','control_bytes_per_request']]
        lines.append('| '+r['family']+' | '+r['backend']+' | '+' | '.join(f'{v:.3f}' for v in values)+' |')
    lines+=['','数据密文包含该字段内的nonce。认证字段保留原SOC3协议的64字节tag；不能据此代表移植PMMAC后的结果。各列经四舍五入，精确总和见JSON。',
            '', '## 2. 短轨迹：各后端总字节','',
            '每行是3个种子的均值；每种子warmup=64，measurement=192。', '',
            '| 前端 | 负载 | Path | Deferred | SDE | Ring43 | GC-Ring43 | R0-43 | Ring76 | R0-76 |',
            '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in short['aggregate']:
        v=r['mean_bytes_per_request']
        lines.append('| '+r['family']+' | '+r['workload']+' | '+' | '.join(f'{v[k]:.3f}' for k in ['Path','Deferred','SDE','Ring43','GC-Ring43','R0-43','Ring76','R0-76'])+' |')
    lines+=['','## 3. raw→compressed的条件组合收益','',
            '均在同一PLB容量和64字节payload下；raw X16，compressed X32/β14。未将这些联合收益归为pure selective gain。','',
            '| 负载 | SDE内再压缩map | R0-43内再压缩map | raw Path→compressed SDE | raw Ring43→compressed R0-43 |',
            '|---|---:|---:|---:|---:|']
    for r in compression:
        lines.append('| '+r['workload']+' | '+' | '.join(f'{r[k]:.3f}%' for k in ['SDE_raw_to_compressed_pct','R0_43_raw_to_compressed_pct','raw_Path_to_compressed_SDE_pct','raw_Ring43_to_compressed_R0_43_pct'])+' |')
    lines+=['','## 4. ρ整体收益稀释','',
            '| 配对 | 优化前完整后端占比 | 完整后端节省 | 前后端合计节省 |','|---|---:|---:|---:|']
    for r in dilution:
        lines.append('| '+'→'.join(r['pair'])+' | '+' | '.join(f'{r[k]:.3f}%' for k in ['baseline_backend_share_pct','backend_saving_pct','total_saving_pct'])+' |')
    (OUT/'03_可复核数据表.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
