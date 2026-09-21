"""Audit the complete predeclared rho matrix as receipts arrive.

An independent address-residency machine reconstructs cache metrics and both
remove/admit streams; it does not invoke frontend, tree, or PRF execution.
Incomplete cells stay visible and do not acquire final confidence intervals.
"""
from common import *
import bisect, math, random
from collections import Counter, OrderedDict, defaultdict
from fractions import Fraction
import composition_runtime
from run_extended_composition import identity as extended_identity
from audit_frontend_batches import check_bill
from audit_storage_components import audit_materialized
from audit_free_sensitivity_completed import stat, effect, pair

KINDS=('deferred','sde','ring','r0')
SEEDS=tuple(range(101,106))


def input_and_answer(s, trace):
    path=PACKAGE/trace['path']; assert sha(path)==trace['sha256']
    t=json.loads(path.read_text(encoding='utf-8'))
    assert (t['N'],t['count'],t['seed'],t['workload'],t['write_probability'])==(4096,6144,s['trace_seed'],s['workload'],.5)
    assert len(t['rows'])==6144
    rng=random.Random(s['trace_seed']); writes=random.Random(s['trace_seed']+2000000)
    permutation=list(range(4096));random.Random(314159).shuffle(permutation)
    cdf=[];total=0.0
    for i in range(4096):total+=(i+1)**(-.9);cdf.append(total)
    versions=[0]*4096;answer=hashlib.sha256()
    for i,(a,v) in enumerate(t['rows']):
        if s['workload']=='uniform':expected=rng.randrange(4096)
        elif s['workload']=='hot90':expected=permutation[rng.randrange(40) if rng.random()<.9 else rng.randrange(40,4096)]
        elif s['workload']=='zipf09':expected=permutation[min(4095,bisect.bisect_left(cdf,rng.random()*total))]
        else:raise AssertionError('undeclared workload')
        assert (a,v)==(expected,i+1 if writes.random()<.5 else None)
        old=a.to_bytes(8,'big')+bytes(56) if versions[a]==0 else hashlib.shake_256(
            b'SOC3-EVAL-PAYLOAD-v1'+a.to_bytes(8,'big')+versions[a].to_bytes(8,'big')).digest(64)
        answer.update(old)
        if v is not None:versions[a]=v
    return t['rows'],answer.hexdigest()


def cache_replay(s, rows):
    """An address-only ownership ledger with a front-slot/back-slot scheduler."""
    llc=OrderedDict();tags=OrderedDict();free=list(range(s['rho']));back=set(range(4096))
    n=s.get('frame_ratio',3);phases={}
    for phase,requests in (('warmup',rows[:2048]),('measurement',rows[2048:])):
        cursor=0;metrics=Counter();counts=[0,0];hashes=[hashlib.sha256(),hashlib.sha256()]
        def emit(tree,remove=None,admit=None):
            counts[tree]+=1
            hashes[tree].update(json.dumps([remove,admit],separators=(',',':')).encode()+b'\n')
        while cursor<len(requests):
            metrics['frames']+=1;pending=None
            for _ in range(n):
                if pending is None:
                    while cursor<len(requests) and requests[cursor][0] in llc:
                        target=requests[cursor][0];cursor+=1
                        llc.move_to_end(target);metrics['llc_hits']+=1
                if pending is not None or cursor==len(requests):
                    emit(0);metrics['rho_dummy_slots']+=1;continue
                target=requests[cursor][0];cursor+=1;metrics['llc_misses']+=1
                outgoing=llc.popitem(last=False)[0] if len(llc)==s['llc'] else None
                if target in tags:
                    metrics['rho_hits']+=1;slot=tags.pop(target)
                    emit(0,slot,None if outgoing is None else slot)
                    if outgoing is None:free.append(slot)
                    else:tags[outgoing]=slot
                    llc[target]=None
                else:
                    metrics['rho_misses']+=1;victim=None
                    assert target in back
                    if outgoing is None:
                        emit(0);metrics['rho_dummy_slots']+=1
                    else:
                        if free:
                            slot=free.pop(0);remove=None
                        else:
                            victim,slot=tags.popitem(last=False);remove=slot
                        tags[outgoing]=slot;emit(0,remove,slot)
                    pending=(target,victim)
            if pending is None:
                emit(1);metrics['back_dummy_slots']+=1
            else:
                target,victim=pending;back.remove(target)
                if victim is not None:
                    assert victim not in back;back.add(victim)
                llc[target]=None;emit(1,target,victim)
            # Check canonical ownership at each completed public frame.
            local=set(llc);cached=set(tags)
            assert not(local&cached or local&back or cached&back)
            assert len(local)+len(cached)+len(back)==4096
            assert len(llc)<=s['llc'] and len(tags)<=s['rho']
            assert len(tags)+len(free)==s['rho']
            assert set(tags.values()).isdisjoint(free) and len(set(tags.values()))==len(tags)
            assert set(tags.values())|set(free)==set(range(s['rho']))
        metrics['application_requests']=len(requests)
        assert metrics['llc_hits']+metrics['llc_misses']==len(requests)
        assert metrics['rho_hits']+metrics['rho_misses']==metrics['llc_misses']
        assert counts==[n*metrics['frames'],metrics['frames']]
        assert metrics['rho_misses']+metrics['back_dummy_slots']==metrics['frames']
        phases[phase]=dict(frontend_metrics=dict(metrics),schedules=[dict(slots=c,remove_admit_sha256=h.hexdigest()) for c,h in zip(counts,hashes)],
            final_residency=dict(llc=len(llc),rho=len(tags),backend=len(back)))
    return phases


def configurations(s):
    def depth(pop,scale):
        L=1
        while 2**L<scale*pop:L+=1
        return L
    front=dict(kind='path',L=depth(s['rho'],8),N=s['rho'],B=64,Z=2,A=1,S=0,R=s['rho'],tree=1,compact=True,fused=True)
    back=dict(kind=s['kind'],L=depth(4096,2/3),N=4096,B=64,Z=4,A=3,S=4,R=256,tree=0,compact=True,fused=True)
    return [front,back]


def audit(r,s,extended,inputs,replays):
    assert r['status']=='passed' and r['spec']==s
    expected=extended_identity() if extended else dict(composition_runtime.identity(),path_stash_replacement_fix={
        n:sha(Path(__file__).parent/n) for n in ('transfer_backend_fixed.py','run_rho_fixed.py')})
    assert r['source_hashes']==expected
    if extended:
        e=r['extended_experiment'];assert e['source_identity']==expected and e['accelerated'] is True
        assert e['parameters']=={k:s[k] for k in ('frame_ratio',) if k in s}
        assert e['type']=='frontend_sensitivity' and not e['public_trace']
        assert e['accelerator_proof_sha256']==sha(PACKAGE/'results/fast_prf_regression.json')
    else:assert r['fix'].startswith('Path uses post-removal pool')
    assert (s['family'],s['N'],s['B'],s['R'],s['profile'],s['warmup'],s['requests'])==('rho',4096,64,256,[4,3,4],2048,4096)
    assert s['oram_seed']==s['trace_seed']+900 and s['trace_seed'] in SEEDS
    assert not any(r[k] for k in ('native_full_paper_reproduction','latency_claim','true_client_peak_measured'))
    assert r['correctness_checked_requests']==6144 and r['configs']==configurations(s)
    assert sha(PACKAGE/r['trace']['path'])==r['trace']['sha256']
    input_key=(s['workload'],s['trace_seed'])
    if input_key not in inputs:inputs[input_key]=input_and_answer(s,r['trace'])
    rows,answer=inputs[input_key];assert r['answer_sha256']==answer
    replay_key=(s['workload'],s['trace_seed'],s['llc'],s['rho'],s.get('frame_ratio',3))
    if replay_key not in replays:replays[replay_key]=cache_replay(s,rows)
    model=replays[replay_key]
    assert len(r['setup'])==2
    seq=[]
    for b in r['setup']:
        check_bill(b);assert b['first_sequence']==0;seq.append(b['next_sequence'])
    for phase,count in (('warmup',2048),('measurement',4096)):
        p=r['phases'][phase];assert p['requests']==count and len(p['bills'])==2
        assert p['schedules']==model[phase]['schedules']
        assert p['frontend_metrics']==model[phase]['frontend_metrics']
        assert p['total_bytes']==sum(b['total_bytes'] for b in p['bills'])
        assert p['rpc']==sum(b['rpc'] for b in p['bills'])
        for i,b in enumerate(p['bills']):
            check_bill(b);assert b['first_sequence']==seq[i];seq[i]=b['next_sequence']
    assert r['bytes_per_request']*4096==r['phases']['measurement']['total_bytes']
    assert r['rpc_per_request']*4096==r['phases']['measurement']['rpc']
    expected_memory=dict(llc_payload_bytes=s['llc']*64,rho_directory_entries=s['rho'],flat_backend_posmap_bytes=4096*4,
        front_posmap_bytes=4*s['rho'],front_stash_reserved_bytes=s['rho']*64,back_stash_reserved_bytes=256*64,
        full_private_posmap_present=True,measured_peak=False)
    assert r['frontend_memory_representation']==expected_memory
    assert len(r['final_stash_blocks'])==2
    assert all(0<=n<=c['R'] for n,c in zip(r['final_stash_blocks'],r['configs']))
    return audit_materialized(r),model


def name(s):return s['workload']+'/'+s.get('condition','base')


def main():
    plan_paths=[PACKAGE/'formal_frontend_sensitivity_plan.json',PACKAGE/'formal_composition_plan.json']
    p,b=[json.loads(x.read_text(encoding='utf-8')) for x in plan_paths]
    entries=[(x['spec'],True) for x in p['items'] if x['spec']['family']=='rho'];assert len(entries)==120
    entries += [(dict(s,id=s['id'].replace('C_rho','C2_rho',1),experiment_class='formal_rho_fixed'),False)
        for s in b['specs'] if s['family']=='rho' and s['workload'] in ('hot90','zipf09','uniform')]
    assert len(entries)==180
    proofs={}
    for fn in ('fast_prf_regression.json','extended_runner_checks.json'):
        path=PACKAGE/'results'/fn;q=json.loads(path.read_text(encoding='utf-8'))
        assert q['status']=='passed' and q['source_hashes']==source_identity()
        if fn=='fast_prf_regression.json':assert q['accelerator_sha256']==sha(Path(__file__).parent/'fast_prf.py')
        else:
            for n,h in q['adapters'].items():assert sha(Path(__file__).parent/n)==h
        proofs[str(path.relative_to(PACKAGE))]=sha(path)
    records={};receipts=[];missing=[];pending=[];inputs={};replays={};groups=defaultdict(dict);resources={};models={}
    expected_groups=Counter(name(s) for s,_ in entries)
    for s,extended in entries:
        path=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        if not path.exists():missing.append(s['id']);continue
        r=json.loads(path.read_text(encoding='utf-8'))
        if ('extended_experiment' if extended else 'fix') not in r:pending.append(s['id']);continue
        resource,model=audit(r,s,extended,inputs,replays);sid=s['id']
        records[sid]=r;resources[sid]=resource;models[sid]=model
        groups[name(s)][s['kind'],s['trace_seed']]=r
        receipts.append(dict(id=sid,path=str(path.relative_to(PACKAGE)),sha256=sha(path),reused_control=not extended))
    complete={k:v for k,v in groups.items() if len(v)==20};cells=[];effects=[];parameter_effects=[]
    for key,rs in sorted(complete.items()):
        for kind in KINDS:
            rr=[rs[kind,i] for i in SEEDS];ms=[r['phases']['measurement'] for r in rr]
            first=rr[0];sid=first['spec']['id'];s=first['spec']
            assert all(resources[r['spec']['id']]==resources[sid] for r in rr)
            keys=set().union(*(m['frontend_metrics'] for m in ms))
            cells.append(dict(configuration=key,kind=kind,n=5,ids=[r['spec']['id'] for r in rr],
                llc=s['llc'],rho=s['rho'],frame_ratio=s.get('frame_ratio',3),resource=resources[sid],
                bytes=stat([m['total_bytes']/4096 for m in ms]),rpc=stat([m['rpc']/4096 for m in ms]),
                front_bytes=stat([m['bills'][0]['total_bytes']/4096 for m in ms]),
                backend_bytes=stat([m['bills'][1]['total_bytes']/4096 for m in ms]),
                frontend_metrics={k:stat([m['frontend_metrics'].get(k,0) for m in ms]) for k in sorted(keys)}))
        for base,new in (('deferred','sde'),('ring','r0')):
            pairs=[]
            for i in SEEDS:
                aa,bb=rs[base,i],rs[new,i];x=pair(aa,bb,True)
                a,b=aa['phases']['measurement']['bills'],bb['phases']['measurement']['bills']
                assert a[0]==b[0]  # Full front-tree bill and transcript match.
                f,old,newb=a[0]['total_bytes'],a[1]['total_bytes'],b[1]['total_bytes']
                assert Fraction(old-newb,f+old)==Fraction(old,f+old)*Fraction(old-newb,old)
                x.update(front_bytes=f/4096,backend_share_pct=100*old/(f+old),backend_saving_pct=100*(1-newb/old))
                pairs.append(x)
            e=effect(f'{key}: {base} -> {new}',pairs)
            e.update(configuration=key,backend_share_pct=stat([x['backend_share_pct'] for x in pairs]),
                backend_saving_pct=stat([x['backend_saving_pct'] for x in pairs]))
            effects.append(e)
    for key,rs in sorted(complete.items()):
        workload,condition=key.split('/')
        if condition=='base':continue
        base=complete[workload+'/base']
        varied='llc' if condition.startswith('llc') else ('rho' if condition.startswith('rho') else 'frame_ratio')
        for kind in KINDS:
            pairs=[]
            for i in SEEDS:
                aa,bb=base[kind,i],rs[kind,i]
                def public(s):
                    q=dict(s,frame_ratio=s.get('frame_ratio',3))
                    return {k:v for k,v in q.items() if k not in ('id','study','condition','experiment_class',varied)}
                assert public(aa['spec'])==public(bb['spec'])
                pairs.append(pair(aa,bb,False))
            parameter_effects.append(effect(f'{workload}/{kind}: base -> {condition}',pairs))
    progress=[dict(configuration=k,completed=len(groups.get(k,{})),expected=count) for k,count in sorted(expected_groups.items())]
    done=len(records)==180
    out=dict(status='complete_receipts_audited' if done else 'partial_receipts_audited',completed=len(records),expected=180,
        new_completed=sum(not r['reused_control'] for r in receipts),new_expected=120,reused_controls=60,receipts=receipts,
        missing=missing,pending_final_receipt=pending,progress=progress,cells=cells,effects=effects,parameter_effects=parameter_effects,
        independent_trace_replays=len(inputs),independent_return_checks=len(inputs)*6144,independent_cache_replays=len(replays),
        completed_cell_only_statistics=True,plan_hashes={str(x.relative_to(PACKAGE)):sha(x) for x in plan_paths},proof_hashes=proofs,
        auditor_sha256=sha(__file__),helpers={n:sha(Path(__file__).parent/n) for n in (
            'audit_frontend_batches.py','audit_storage_components.py','audit_free_sensitivity_completed.py','run_extended_composition.py')},
        new_security_proof=False,native_full_system=False,true_client_peak_measured=False,latency_claim=False,
        additional_repeat_groups=[e['name'] for e in effects+parameter_effects if e['needs_more_repeats']],
        scope='rho-inspired address-LRU two-tree frontend with full trusted backend PosMap and public frame length; finite windows; no ECC/native set-associative or asynchronous controller')
    save(PACKAGE/'results/rho_sensitivity_audit.json',out)
    if done:save(PACKAGE/'results/rho_sensitivity_completed_snapshot.json',out)
    md=['# ρ参数敏感性与独立缓存重放','',
        f"已核对{out['new_completed']}/120次新敏感性运行，加60次既有对照；总计{len(records)}/180份最终收据。只对四后端、各五种子均完成的配置给出最终配对表，其余配置在下表逐项保留。",'',
        '| 配置 | 完成 / 计划 |','|---|---:|']
    for row in progress:md.append(f"| {row['configuration']} | {row['completed']} / {row['expected']} |")
    md+=['','N4096/B64，暖机2048、测量4096应用请求；后树Z4/A3/S4/R256。每个访问帧固定n次前树Transfer加一次后树Transfer；帧总数允许公开。base为LLC32、ρ缓存128、n3。应用层双向总字节含认证与所有维护，初始化和暖机另列，不计TCP/TLS。','',
        '## 同前端：整体与后端收益','',
        '| 比较 | 基线 bytes/op | selective bytes/op | 整体节省 / 95%区间 | 基线后端占比 | 后端自身节省 |',
        '|---|---:|---:|---|---:|---:|']
    for e in effects:
        x=e['bytes_saving_pct'];lo,hi=x['ci95']
        md.append(f"| {e['name']} | {e['baseline_mean']:,.2f} | {e['variant_mean']:,.2f} | {x['mean']:.3f}% / [{lo:.3f}, {hi:.3f}]% | {e['backend_share_pct']['mean']:.3f}% | {e['backend_saving_pct']['mean']:.3f}% |")
    md+=['','逐种子以有理数核对：整体节省=原后端字节占比×后端自身节省。前树的完整账单和传输摘要在每对中相同，不能把后端百分比直接写成整体收益；表中的均值相乘不要求等于逐种子乘积的均值。','',
        '## 参数变化本身的通信效应','',
        '保持后端不变，改变一项公开参数；负值表示总通信增加。改变LLC/ρ容量会改变资源和前树几何，不能把该收益归于selective，也不是固定可信字节预算比较。','',
        '| 变化 | 原 bytes/op | 新 bytes/op | 节省 / 95%区间 |','|---|---:|---:|---|']
    for e in parameter_effects:
        x=e['bytes_saving_pct'];lo,hi=x['ci95']
        md.append(f"| {e['name']} | {e['baseline_mean']:,.2f} | {e['variant_mean']:,.2f} | {x['mean']:.3f}% / [{lo:.3f}, {hi:.3f}]% |")
    md+=['','## 独立重放出的前端工作量','',
        '每配置四后端的计数与remove/admit摘要相同，以下只列一次五种子均值。命中计数分母不同：LLC按应用请求，ρ按LLC miss，dummy按对应树时隙。','',
        '| 配置 | LLC / ρ / n | LLC命中 | ρ命中 | ρ未命中 | 帧数 | 前树dummy | 后树dummy |','|---|---|---:|---:|---:|---:|---:|---:|']
    for c in cells:
        if c['kind']!='deferred':continue
        m=c['frontend_metrics'];v=lambda k:m.get(k,{'mean':0})['mean']
        md.append(f"| {c['configuration']} | {c['llc']} / {c['rho']} / {c['frame_ratio']} | {v('llc_hits'):.1f} | {v('rho_hits'):.1f} | {v('rho_misses'):.1f} | {v('frames'):.1f} | {v('rho_dummy_slots'):.1f} | {v('back_dummy_slots'):.1f} |")
    md+=['','独立地址所有权模型不调用原前端、树或PRF。它从输入重建LLC与ρ的LRU、迁移slot和后端驻留集合；每个完成帧核对唯一所有权，总人口守恒及目录slot分区。实际收据逐阶段与独立模型的全部前端计数、两树remove/admit摘要一致。',
        f"本次独立重建{len(inputs)}条输入及返回摘要（{len(inputs)*6144}个返回值），执行{len(replays)}组缓存调度重放。还核对原始身份、最终标记、账单分项、RPC连续序号、前后树几何和实际服务器对象；每个完整配置有五个种子。",'',
        '资源JSON分别保留前树Z2、stash预留ρ×B、后树R256、完整可信后端PosMap、前树PosMap、LLC及目录容量；不把这些有限项称为真实峰值。前树R=ρ可容纳其全部人口，不凭低Z声称获得SOC3数值证书。',
        '本结果针对当前ρ-inspired变体，不含原生ECC、set-associative标签或异步硬件控制器；不声称完整原生系统复现、稳态或延迟改善。有限样本区间不是对所有负载/容量的保证。',
        f"触发追加重复门槛的完整组数：{len(out['additional_repeat_groups'])}。全部预声明组未收齐前不冻结完整快照或输出全批完成结论。",'',
        '`results/rho_sensitivity_audit.json`为当前逐项来源与独立统计；全部180份最终收据齐备后才生成rho_sensitivity_completed_snapshot.json。']
    (PACKAGE/'50_rho敏感性独立统计.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=out['status'],new_completed=out['new_completed'],expected=120,reused=60,
        cells=len(cells),selective_effects=len(effects),parameter_effects=len(parameter_effects),cache_replays=len(replays),
        repeat_groups=out['additional_repeat_groups'])))


if __name__=='__main__':main()
