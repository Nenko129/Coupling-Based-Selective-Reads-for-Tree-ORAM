"""Independent by-depth content accounting; not a trusted peak-memory meter."""
from common import *
from collections import Counter,defaultdict

FIELDS=('headers','ciphertext_slots','local_authentication','bucket_tags','global_tags')


def storage(configs,cuts=None):
    cuts=cuts or {};remote=Counter({k:0 for k in FIELDS});local=Counter({k:0 for k in FIELDS})
    remote_nodes=local_nodes=0;detail=[]
    for c in configs:
        ring=c['kind'] in ('ring','gc_ring','r0');cut=cuts.get(c['tree'],0)
        for d in range(c['L']+1):
            count=2**d;z=c.get('Z_by_depth',[])[d] if c.get('Z_by_depth') else c['Z']
            dummy=c.get('S_by_depth',[])[d] if c.get('S_by_depth') else c['S'];n=z+dummy if ring else z
            empty_root=d==0 and c['kind']=='r0'
            H=60+16+32*((8+(30 if c['compact'] else 64)*z+31)//32)
            # Number of nonempty intervals in a power-of-two padded local tree:
            # ceil(n/1)+ceil(n/2)+...+ceil(n/2^ceil(log2(n))).
            tag_nodes=sum((n+(1<<j)-1)//(1<<j) for j in range((n-1).bit_length()+1)) if ring else 0
            parts=dict(headers=0 if empty_root else count*H,
                ciphertext_slots=0 if empty_root else count*n*(c['B']+16),
                local_authentication=0 if empty_root else count*tag_nodes*64,
                bucket_tags=count*64,global_tags=count*64)
            if d<cut:local.update(parts);local_nodes+=count
            else:remote.update(parts);remote_nodes+=count
            detail.append(dict(tree=c['tree'],depth=d,location='client_prefix' if d<cut else 'server',buckets=count,
                Z=z,S=dummy if ring else 0,physical_slots=0 if empty_root else n,components=parts))
    return dict(remote=dict(remote),remote_bytes=sum(remote.values()),remote_nodes=remote_nodes,
        local=dict(local),local_bytes=sum(local.values()),local_nodes=local_nodes,by_depth=detail)


def audit_materialized(r):
    cuts={0:r['spec']['cached_levels']} if 'cache_representation' in r else {}
    predicted=storage(r['configs'],cuts);actual=r['server_storage']
    rows=actual if isinstance(actual,list) else [actual]
    components=Counter({k:0 for k in FIELDS});nodes=0
    for obj in rows:
        assert obj['total_bytes']==sum(obj['components'].values());components.update(obj['components']);nodes+=obj['physical_bucket_records']
    assert dict(components)==predicted['remote'] and nodes==predicted['remote_nodes']
    if cuts:
        cache=r['cache_representation']
        assert (cache['bytes'],cache['bucket_records'],cache['global_tag_records'])==(predicted['local_bytes'],predicted['local_nodes'],predicted['local_nodes'])
    else:assert predicted['local_bytes']==0
    reserved=sum(c['R']*c['B'] for c in r['configs'])
    terminal=r.get('terminal_position_map_bytes')
    if terminal is not None:assert terminal==4*r['configs'][-1]['N']
    memory=r.get('frontend_memory_representation')
    if memory is not None:
        reported=sum(v for k,v in memory.items() if k in ('stash_reserved_bytes','front_stash_reserved_bytes','back_stash_reserved_bytes'))
        assert reported==reserved and memory['measured_peak'] is False
        if r['spec']['family']=='rho':
            assert memory['flat_backend_posmap_bytes']==4*r['spec']['N'] and memory['front_posmap_bytes']==4*r['spec']['rho']
            assert memory['llc_payload_bytes']==r['spec']['llc']*r['spec']['B']
        else:
            assert memory['plb_payload_bytes']==r['spec']['plb']*r['spec']['B']
    return dict(**predicted,reserved_stash_payload_bytes=reserved,terminal_map_bytes=terminal,
        declared_frontend_memory=memory,measured_trusted_peak=False)


def main():
    receipts=[];groups=defaultdict(list);audit_sources={}
    for name in ('core_components_complete_audit.json','public_completed_audit.json'):
        p=PACKAGE/'results'/name;a=json.loads(p.read_text());assert a['status']=='passed';audit_sources[name]=sha(p)
        for item in a['receipts']:
            path=PACKAGE/item['path'];assert sha(path)==item['sha256'];r=json.loads(path.read_text());s=r['spec'];resource=audit_materialized(r)
            family=s.get('family','core');key=(family,s.get('layout','uniform'),s['kind'],s['N'],s['B'],digest(r['configs']))
            row=dict(source=item,spec=s,configs=r['configs'],resource=resource);receipts.append(row);groups[key].append(row)
    assert len(receipts)==220
    cells=[]
    for key,rs in sorted(groups.items()):
        assert all(r['resource']==rs[0]['resource'] for r in rs)
        cells.append(dict(family=key[0],layout=key[1],kind=key[2],N=key[3],B=key[4],observations=len(rs),
            resource=rs[0]['resource'],ids=[r['spec']['id'] for r in rs]))
    assert len(cells)==30
    tp=PACKAGE/'results/fair_tuning_candidates.json';tuning=json.loads(tp.read_text());candidate_rows=[]
    for c in tuning['candidates']:
        x=storage(c['configs']);persistent=sum(t['R']*t['B'] for t in c['configs'])+4*c['configs'][-1]['N']
        assert x['remote_bytes']==c['server_object_bytes'] and persistent==c['persistent_payload_plus_terminal']
        server_ok=x['remote_bytes']<=4*(1<<30);payload_ok=persistent<=256*(1<<20)
        assert c['true_peak_memory_checked'] is False
        candidate_rows.append(dict(id=c['candidate_id'],kind=c['spec']['kind'],server_bytes=x['remote_bytes'],
            persistent_payload_plus_terminal=persistent,server_budget_ok=server_ok,payload_budget_ok=payload_ok,
            selected=c['candidate_id'] in tuning['selected'],resource=x))
    assert len(candidate_rows)==72
    selected=[]
    for c in tuning['candidates']:
        if c['candidate_id'] not in tuning['selected']:continue
        sid=f"B3_{c['spec']['kind']}_uniform_seed101";p=PACKAGE/'results/formal_tuned'/f'{sid}.json';r=json.loads(p.read_text())
        assert r['status']=='passed' and r['configs']==c['configs']
        resource=audit_materialized(r);assert resource['remote_bytes']==c['server_object_bytes']
        selected.append(dict(id=c['candidate_id'],spec=c['spec'],resource=resource,
            source=dict(id=sid,path=str(p.relative_to(PACKAGE)),sha256=sha(p))))
    assert len(selected)==5
    out=dict(status='passed',completed_run_count=220,completed_cells=30,selected_config_storage_witnesses=5,
        receipts=receipts,cells=cells,candidates=candidate_rows,selected=selected,audit_sources=audit_sources,
        tuning_source_sha256=sha(tp),auditor_sha256=sha(__file__),
        scope='actual serialized server and cached-prefix object content; stash-payload reservations and declared map/frontend fields separately',
        true_client_peak_measured=False,allocator_and_index_overhead_included=False,all_paper_configurations_covered=False,
        pending_scope=['remaining B3/B4/frontends and integrated IR/AB resource ledgers','transient ciphertext/plaintext/write/verification buffers','client metadata/container and allocator overhead'])
    save(PACKAGE/'results/storage_components_audit.json',out)
    md=['# 服务器对象与客户端已列资源：独立空间对照','',
        '独立按树深度计算密文槽、固定长度桶头、局部认证树、桶标签和全局标签，逐项核对220份已完成运行（140核心/静态组件＋80公开trace）的实际对象账单。得到30格空间记录，各格所有已完成运行相同。另核对72个调优候选及每个入选配置的一份实际运行；这些5份只证明配置对应的空间数值，不充作调优性能五次重复。',
        '', '## 计量边界','',
        '- 服务器列：真实序列化对象内容，不含Python字典、索引、对象头或分配器。',
        '- 缓存前缀列：当前可信缓存中实际序列化对象内容；包括认证标签，R0根仍有标签。',
        '- stash列：按每树R×B预留payload容量，不是实际占用或进程RSS；不含每条record的地址、leaf、uid及容器。',
        '- terminal列：核心递归实现的可信终端map。组合前端的PLB/LLC/位置表在配套JSON分别保留，不能把空白当作零。',
        '- 上述项不构成真实峰值：并存密文、decoded payload、final-write帧、认证scratch和元数据仍未被完整计入。不能据此声称256MiB可信峰值已通过。',
        '', '## 30格实际对象对照','',
        '| 家族/布局 | 后端 | N/B | 观测数 | 服务器对象MiB | 可信缓存前缀KiB | stash预留KiB | terminal KiB |',
        '|---|---|---|---:|---:|---:|---:|---:|']
    for c in cells:
        x=c['resource'];terminal='前端另列' if x['terminal_map_bytes'] is None else f"{x['terminal_map_bytes']/1024:.3f}"
        md.append(f"| {c['family']}/{c['layout']} | {c['kind']} | {c['N']}/{c['B']} | {c['observations']} | {x['remote_bytes']/(1<<20):.6f} | {x['local_bytes']/1024:.3f} | {x['reserved_stash_payload_bytes']/1024:.3f} | {terminal} |")
    md+=['', '## 调优配置的共同上限与实际空间','',
        '候选筛选采用共同上限：服务器对象4GiB，stash预留payload加终端map256MiB。共同上限不意味着双方实际占用相同。下面服务器列已与入选配置的实际对象账单逐项相等；预算客户项仍沿预先声明的有限口径。','',
        '| 后端 | Z/A/S | 服务器对象MiB | stash payload＋terminal MiB | 空间见证运行 |','|---|---|---:|---:|---|']
    for c in selected:
        x=c['resource'];s=c['spec'];client=x['reserved_stash_payload_bytes']+x['terminal_map_bytes']
        md.append(f"| {s['kind']} | {'/'.join(map(str,s['profile']))} | {x['remote_bytes']/(1<<20):.6f} | {client/(1<<20):.6f} | {c['source']['id']} |")
    ring=next(c for c in selected if c['spec']['kind']=='ring');r0=next(c for c in selected if c['spec']['kind']=='r0')
    difference=100*(1-r0['resource']['remote_bytes']/ring['resource']['remote_bytes'])
    md+=['',f'在这组入选配置中，R0服务器对象比Ring少{difference:.3f}%，因此不是依靠更大服务器对象存储换取其候选带宽优势；两者分别使用S6/S9，仍需随性能结果披露参数差异。该观察不证明全候选最优，也不替代尚缺的基线/组合安全绑定。',
        '', '## 独立计算与复核入口','',
        '深度d共有2^d个桶。secret header长度为32字节对齐的(8＋30Z)，未compact时30替换为64；加60字节公开头和16字节nonce。Ring局部认证树的实际节点数为各j从0到ceil(log2 n)的ceil(n/2^j)之和，其中n=Z+S。R0根的header/slots/local-tree为零，但两种64B标签保留。缓存前缀按真实cut分到客户与服务器两侧。',
        '`results/storage_components_audit.json`保存逐层整数分项、全部来源hash、72候选与5个入选配置空间见证；不使用运行时间或RSS代理可信峰值。集成IR/AB和其余规模/敏感性资源表仍须继续补齐。',
        '损坏账单拒绝检查另见 `results/storage_audit_rejections.json`：覆盖总数仍自洽但头部虚增、同总量错分项、桶记录数、terminal大小、缓存对象/层数，以及ρ stash/完整PosMap漏计。它只检查上述审计拒绝行为，不转化为峰值内存通过。']
    (PACKAGE/'44_实际对象空间与预算口径.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',runs=220,cells=30,candidates=72,selected_storage_witnesses=5,R0_vs_tuned_Ring_storage_saving_pct=difference)))


if __name__=='__main__':main()
