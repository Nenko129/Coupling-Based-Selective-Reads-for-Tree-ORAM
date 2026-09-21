"""Freeze all five predeclared Freecursive slices and their existing controls.

Read-only with respect to raw runs, running queues and protocol sources.
This audits finite-window evidence, not native-system security or peak memory.
"""
from common import *
import math, random, statistics
from collections import defaultdict
import composition_runtime
from run_extended_composition import identity as extended_identity
from audit_frontend_batches import check_bill
from audit_storage_components import audit_materialized

KINDS = ('deferred', 'sde', 'ring', 'r0')
SEEDS = tuple(range(101, 106))
T4 = 2.7764451051977987


def stat(xs):
    assert len(xs) == 5
    m = statistics.mean(xs)
    half = T4 * statistics.stdev(xs) / math.sqrt(5)
    return dict(n=5, mean=m, ci95=[m-half, m+half], values=xs)


def label(s):
    return '/'.join((s['family'], s['workload'], s.get('condition', 'B64_base')))


def independent_answer(s, trace):
    """Regenerate both address/version input and pre-write return-value digest."""
    p = PACKAGE / trace['path']
    assert sha(p) == trace['sha256']
    t = json.loads(p.read_text(encoding='utf-8'))
    N, B, seed = s['N'], s['B'], s['trace_seed']
    assert (t['N'], t['count'], t['seed'], t['workload']) == (
        N, s['warmup']+s['requests'], seed, s['workload'])
    assert t['write_probability'] == .5 and len(t['rows']) == t['count']
    address_rng, write_rng = random.Random(seed), random.Random(seed+2000000)
    permutation = list(range(N)); random.Random(314159).shuffle(permutation)
    versions = [0]*N; answer = hashlib.sha256()
    assert s['workload'] in ('uniform', 'hot90')
    for i, (a, v) in enumerate(t['rows']):
        if s['workload'] == 'uniform':
            expected_address = address_rng.randrange(N)
        else:
            hot = max(1, N//100)
            j = address_rng.randrange(hot) if address_rng.random() < .9 else address_rng.randrange(hot, N)
            expected_address = permutation[j]
        expected_version = i+1 if write_rng.random() < .5 else None
        assert (a, v) == (expected_address, expected_version)
        old = (a.to_bytes(8, 'big') + bytes(B-8)) if versions[a] == 0 else hashlib.shake_256(
            b'SOC3-EVAL-PAYLOAD-v1' + a.to_bytes(8, 'big') + versions[a].to_bytes(8, 'big')).digest(B)
        answer.update(old)
        if v is not None: versions[a] = v
    return answer.hexdigest()


def check_run(r, s, extended, answers):
    assert r['status'] == 'passed' and r['spec'] == s
    expected = extended_identity() if extended else composition_runtime.identity()
    assert r['source_hashes'] == expected
    if extended:
        e = r['extended_experiment']
        assert e['accelerated'] is True and e['source_identity'] == expected
        assert e['type'] == 'frontend_sensitivity' and e['public_trace'] is False
        assert e['parameters'] == {k:s[k] for k in ('beta', 'X') if k in s}
        assert e['accelerator_proof_sha256'] == sha(PACKAGE/'results/fast_prf_regression.json')
    assert (s['N'], s['warmup'], s['requests'], s['profile'], s['R']) == (4096, 2048, 4096, [4,3,4], 256)
    assert s['oram_seed'] == s['trace_seed']+900
    assert r['correctness_checked_requests'] == 6144
    assert not any(r[k] for k in ('native_full_paper_reproduction','latency_claim','true_client_peak_measured'))
    assert sha(PACKAGE/r['trace']['path']) == r['trace']['sha256']
    key = (r['trace']['path'], s['B'])
    if key not in answers: answers[key] = independent_answer(s, r['trace'])
    assert r['answer_sha256'] == answers[key]
    compressed = s['family'] == 'free_compressed'
    X = s.get('X', 32 if compressed else s['B']//4)
    beta = s.get('beta', 14)
    assert (64+X*beta <= 8*s['B']) if compressed else (4*X <= s['B'])
    counts = [s['N']]
    while counts[-1] > 1: counts.append((counts[-1]+X-1)//X)
    population = sum(counts); L = 1
    while 3*2**L < 2*population: L += 1
    assert r['configs'] == [dict(kind=s['kind'],L=L,N=population,B=s['B'],Z=4,A=3,S=4,R=256,tree=0,compact=True,fused=True)]
    assert len(r['setup']) == 1
    setup = r['setup'][0]; check_bill(setup); assert setup['first_sequence'] == 0
    seq = setup['next_sequence']; cached = 0
    for phase, count in (('warmup',2048),('measurement',4096)):
        x = r['phases'][phase]; assert x['requests'] == count and len(x['bills']) == 1
        bill = x['bills'][0]; check_bill(bill)
        assert bill['first_sequence'] == seq; seq = bill['next_sequence']
        assert x['total_bytes'] == bill['total_bytes'] and x['rpc'] == bill['rpc']
        m = x['frontend_metrics']; assert m['application_requests'] == count
        assert len(x['schedules']) == 1
        assert x['schedules'][0]['slots'] == count+m.get('plb_misses',0)+m.get('group_backend_slots',0)
        cached += m.get('plb_misses',0)-m.get('plb_evictions',0)
        assert 0 <= cached <= min(s['plb'],population-s['N'])
        if not compressed: assert not any(m.get(k,0) for k in ('group_resets','group_cached_rotations','group_backend_slots'))
    assert r['bytes_per_request']*4096 == r['phases']['measurement']['total_bytes']
    assert r['rpc_per_request']*4096 == r['phases']['measurement']['rpc']
    resource = audit_materialized(r)
    assert r['frontend_memory_representation'] == dict(plb_payload_bytes=s['plb']*s['B'],
        plb_leaf_and_address_bytes=s['plb']*12,terminal_leaf_bytes=4*counts[-1],
        stash_reserved_bytes=256*s['B'],full_private_posmap_present=False,measured_peak=False)
    assert len(r['final_stash_blocks']) == 1 and 0 <= r['final_stash_blocks'][0] <= 256
    return dict(packing=X,beta=beta if compressed else None,counts=counts,resource=resource)


def pair(a, b, same_frontend):
    assert a['trace'] == b['trace'] and a['answer_sha256'] == b['answer_sha256']
    assert a['spec']['trace_seed'] == b['spec']['trace_seed']
    assert a['spec']['B'] == b['spec']['B']
    if same_frontend:
        ignored = {'id','kind'}
        assert {k:v for k,v in a['spec'].items() if k not in ignored} == {k:v for k,v in b['spec'].items() if k not in ignored}
        for phase in ('warmup','measurement'):
            assert a['phases'][phase]['frontend_metrics'] == b['phases'][phase]['frontend_metrics']
            assert a['phases'][phase]['schedules'] == b['phases'][phase]['schedules']
    aa, bb = a['phases']['measurement'], b['phases']['measurement']
    return dict(seed=a['spec']['trace_seed'],baseline_id=a['spec']['id'],variant_id=b['spec']['id'],
        baseline_bytes=aa['total_bytes']/4096,variant_bytes=bb['total_bytes']/4096,
        saving_pct=100*(1-bb['total_bytes']/aa['total_bytes']),
        rpc_saving_pct=100*(1-bb['rpc']/aa['rpc']))


def effect(name, pairs):
    assert [x['seed'] for x in pairs] == list(SEEDS)
    e = stat([x['saving_pct'] for x in pairs])
    costs = [[x[k] for x in pairs] for k in ('baseline_bytes','variant_bytes')]
    cvs = [statistics.stdev(x)/statistics.mean(x) for x in costs]
    return dict(name=name,bytes_saving_pct=e,rpc_saving_pct=stat([x['rpc_saving_pct'] for x in pairs]),
        baseline_mean=statistics.mean(costs[0]),variant_mean=statistics.mean(costs[1]),pairs=pairs,
        run_cost_cv=cvs,needs_more_repeats=max(cvs)>.10 or (e['ci95'][1]-e['ci95'][0])/2>5)


def main():
    plan_paths = [PACKAGE/'formal_frontend_sensitivity_plan.json',PACKAGE/'formal_composition_plan.json']
    p, base = [json.loads(x.read_text(encoding='utf-8')) for x in plan_paths]
    selected = [(x['spec'],True) for x in p['items'] if x['spec']['family'].startswith('free_')]
    assert len(selected) == 100
    controls = [(s,False) for s in base['specs'] if (s['family'],s['workload']) in (
        ('free_raw','uniform'),('free_compressed','uniform'),('free_compressed','hot90'))]
    assert len(controls) == 60
    proofs = {}
    for name in ('fast_prf_regression','extended_runner_checks'):
        pp = PACKAGE/'results'/f'{name}.json'; q = json.loads(pp.read_text(encoding='utf-8'))
        assert q['status'] == 'passed' and q['source_hashes'] == source_identity()
        if name == 'extended_runner_checks':
            for filename, expected in q['adapters'].items():
                assert sha(Path(__file__).parent/filename) == expected
        proofs[str(pp.relative_to(PACKAGE))] = sha(pp)
    fast = json.loads((PACKAGE/'results/fast_prf_regression.json').read_text(encoding='utf-8'))
    assert fast['accelerator_sha256'] == sha(Path(__file__).parent/'fast_prf.py')
    records={}; receipts=[]; groups=defaultdict(dict); answers={}; params={}
    for s, extended in selected+controls:
        path=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json"
        r=json.loads(path.read_text(encoding='utf-8')); x=check_run(r,s,extended,answers)
        records[s['id']]=r; key=label(s); groups[key][s['kind'],s['trace_seed']]=r
        params[s['id']]=x
        receipts.append(dict(id=s['id'],path=str(path.relative_to(PACKAGE)),sha256=sha(path),
            reused_control=not extended,parameters=x))
    assert len(records)==160 and len(groups)==8 and len(answers)==15
    cells=[]; selective=[]; changes=[]
    for key, rows in sorted(groups.items()):
        assert len(rows)==20
        for kind in KINDS:
            rs=[rows[kind,seed] for seed in SEEDS]; first=rs[0]; s=first['spec']
            assert all(params[r['spec']['id']]==params[first['spec']['id']] for r in rs)
            metrics=set().union(*(r['phases']['measurement']['frontend_metrics'] for r in rs))
            cells.append(dict(configuration=key,kind=kind,spec={k:v for k,v in s.items() if k not in ('id','trace_seed','oram_seed')},
                bytes=stat([r['bytes_per_request'] for r in rs]),rpc=stat([r['rpc_per_request'] for r in rs]),
                slots=stat([r['phases']['measurement']['schedules'][0]['slots'] for r in rs]),
                frontend_metrics={k:stat([r['phases']['measurement']['frontend_metrics'].get(k,0) for r in rs]) for k in sorted(metrics)},
                parameters=params[first['spec']['id']],ids=[r['spec']['id'] for r in rs]))
        for old,new in (('deferred','sde'),('ring','r0')):
            selective.append(effect(f'{key}: {old} -> {new}',[pair(rows[old,i],rows[new,i],True) for i in SEEDS]))
    for condition in ('plb4','plb32','beta4'):
        a=groups['free_compressed/hot90/B64_base']; b=groups['free_compressed/hot90/'+condition]
        for kind in KINDS:
            for i in SEEDS:
                old, new = a[kind,i]['spec'], b[kind,i]['spec']
                ignored = {'id','study','condition','experiment_class','X','beta'}
                if condition.startswith('plb'): ignored.add('plb')
                assert {k:v for k,v in old.items() if k not in ignored} == {k:v for k,v in new.items() if k not in ignored}
                assert params[old['id']]['packing'] == params[new['id']]['packing'] == 32
                assert (old.get('beta',14),new.get('beta',14)) == ((14,4) if condition=='beta4' else (14,14))
            changes.append(effect(f'{kind}: B64_base -> {condition}',[pair(a[kind,i],b[kind,i],False) for i in SEEDS]))
    for condition in ('B64_base','B4096'):
        a=groups['free_raw/uniform/'+condition]; b=groups['free_compressed/uniform/'+condition]
        for kind in KINDS:
            for i in SEEDS:
                ignored = {'id','family','X'}
                assert {k:v for k,v in a[kind,i]['spec'].items() if k not in ignored} == {k:v for k,v in b[kind,i]['spec'].items() if k not in ignored}
            changes.append(effect(f'{kind}: raw -> compressed / {condition}',[pair(a[kind,i],b[kind,i],False) for i in SEEDS]))
    assert len(cells)==32 and len(selective)==16 and len(changes)==20
    out=dict(status='passed',new_sensitivity_runs=100,reused_control_runs=60,runs=160,receipts=receipts,
        plan_hashes={str(x.relative_to(PACKAGE)):sha(x) for x in plan_paths},proof_hashes=proofs,
        auditor_sha256=sha(__file__),helper_sha256={n:sha(Path(__file__).parent/n) for n in (
            'audit_frontend_batches.py','audit_storage_components.py','run_extended_composition.py')},
        independently_replayed_trace_files=10,independent_payload_replays=len(answers),
        independently_checked_returns=len(answers)*6144,cells=cells,selective_effects=selective,parameter_effects=changes,
        additional_repeat_groups=[e['name'] for e in selective+changes if e['needs_more_repeats']],
        all_free_slices_complete=True,all_220_sensitivity_runs_complete=False,
        native_full_system=False,security_proof=False,true_client_peak_measured=False,latency_claim=False,
        scope='five predeclared Freecursive-style finite-window slices plus three reused control configurations; no PMMAC/hardware controller; no steady-state claim')
    save(PACKAGE/'results/free_sensitivity_completed_audit.json',out)
    md=['# Freecursive五组敏感性：完整通信与参数代价','',
        '五组预声明切片全部完成：100次新运行，加60次既有对照，共160份最终收据。每配置四个后端、各五个种子；32格绝对开销、16组selective效应及20组前端参数效应。ρ其余敏感性仍在运行，本报告不把整个220次计划标为完成。','',
        'N4096；暖机2048、测量4096应用请求；Z4/A3/S4、R256；种子101—105。应用层双向序列化总字节包含实现中的递归、认证和所有维护通信，初始化与暖机单列，不含TCP/TLS。95%区间为五个独立合成运行的配对Student-t区间，不能解释为所有配置的总体保证。','',
        '## 同前端selective增益','',
        '| 配置与比较 | 基线 bytes/op | selective bytes/op | 减少率 / 95%区间 |','|---|---:|---:|---|']
    for e in selective:
        x=e['bytes_saving_pct']; lo,hi=x['ci95']
        md.append(f"| {e['name']} | {e['baseline_mean']:,.2f} | {e['variant_mean']:,.2f} | {x['mean']:.3f}% / [{lo:.3f}, {hi:.3f}]% |")
    md+=['','## 改变前端参数的代价','',
        '下面各行保持后端不变。负减少率表示通信增加；不能将这些百分比与selective节省直接相加。B64_base压缩对照为PLB8、β14、X32。raw→compressed的X在64B时为16→32，在4096B时为1024→2048。','',
        '| 后端与变化 | 变化前 bytes/op | 变化后 bytes/op | 减少率 / 95%区间 |','|---|---:|---:|---|']
    for e in changes:
        x=e['bytes_saving_pct']; lo,hi=x['ci95']
        md.append(f"| {e['name']} | {e['baseline_mean']:,.2f} | {e['variant_mean']:,.2f} | {x['mean']:.3f}% / [{lo:.3f}, {hi:.3f}]% |")
    md+=['','## 前端实际工作量','',
        '同配置同种子的四后端逐项核对相同remove/admit摘要、PLB命中/未命中、驱逐和group reset计数，故每配置只列一行五次均值。该核对覆盖暖机和测量两个阶段。','',
        '| 配置 | X / β | 后端总人口 | Transfer时隙 | PLB命中 | PLB未命中 | group reset | reset后端时隙 |','|---|---|---:|---:|---:|---:|---:|---:|']
    for c in cells:
        if c['kind']!='deferred':continue
        m=c['frontend_metrics']; x=c['parameters']; val=lambda k:m.get(k,{'mean':0})['mean']
        md.append(f"| {c['configuration']} | {x['packing']} / {x['beta']} | {sum(x['counts'])} | {c['slots']['mean']:.1f} | {val('plb_hits'):.1f} | {val('plb_misses'):.1f} | {val('group_resets'):.1f} | {val('group_backend_slots'):.1f} |")
    md+=['','每个运行验证时隙数=应用请求+PLB未命中+group reset的后端时隙，及缓存接纳/驱逐守恒。','',
        '## 空间与统计边界','',
        '64B→4096B同时改变合法打包容量X，并在固定PLB条目数下改变其payload字节预算；因此是配置切片，不是保持X和可信字节预算不变的单因素消融。改变PLB条目数同样改变资源，不能把其单独节省归功于selective。',
        '逐深度整数重算全部160份服务器对象账单，核对每份PLB payload/地址叶标签、terminal leaf、stash预留；完整数值保存在JSON每行parameters.resource。它仍未覆盖并存解码/加密/写回/认证scratch，不声称真实可信峰值或延迟改进。',
        f"本批触发预声明追加重复条件的组数为{len(out['additional_repeat_groups'])}（成本CV>10%或减少率区间半宽>5个百分点）。负效应与包含零的区间均保留。",'',
        '## 独立审计范围','',
        '按预声明计划完整选取五组Freecursive切片，不按结果好坏筛选。源码、原始收据、输入trace和等价加速检查均绑定哈希；独立重建10条地址/版本trace、15组不同块长的返回值摘要，共92160个返回值。核对最终标记、请求/回复及分项账单、RPC连续序号、几何和实际对象空间。',
        '结果是当前Freecursive-style受限组合的有限窗口证据；未复现原生PMMAC和硬件控制器，不替代安全证明，也不代表所有缓存/参数/负载均有同样收益。',
        '`results/free_sensitivity_completed_audit.json`保存160份来源、每种子值、全部32格及36组配对效应；此独立快照不绑定仍变化的extended_statistics.json。']
    (PACKAGE/'49_Freecursive敏感性完整结果.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',runs=160,new_runs=100,reused_controls=60,cells=32,
        selective_effects=16,parameter_effects=20,checked_returns=92160,additional_repeat_groups=out['additional_repeat_groups'])))


if __name__=='__main__':main()
