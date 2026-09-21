"""Source-bound report of classical execution, arithmetic, and planned reference."""
from common import *
from check_classical_stash_binding import validate


def main():
    files=['classical_execution_projection_checks.json','classical_stash_execution_ledger.json',
           'classical_stash_execution_ledger_audit.json','classical_active_failstop_checks.json',
           'classical_minima_audit.json']
    data={name:json.loads((PACKAGE/'results'/name).read_text()) for name in files}
    bound=data[files[1]];validate(bound)
    assert data[files[2]]['source_sha256']==sha(PACKAGE/'results'/files[1])
    active=data[files[3]];assert active['status']=='passed' and active['source_hashes']==source_identity()
    assert active['checker_sha256']==sha(PACKAGE/'src/check_classical_active_failstop.py')
    minima=data[files[4]];assert minima['status']=='passed' and minima['ledger_sha256']==sha(PACKAGE/'results'/files[1])
    assert minima['ledger_audit_sha256']==sha(PACKAGE/'results'/files[2])
    assert minima['auditor_sha256']==sha(PACKAGE/'src/audit_classical_minima.py')
    checks=data[files[0]];extra=bound['supplemental_path']
    md=['# 经典Path/Ring执行归约、访问边界余量与补充对照','',
        '本次把经典stash算术推进到具体执行的逻辑投影、递归初始化账本和阶段边界。可支持本文均匀核心在理想独立叶标签下的stash分析；不据此标记完整主动安全、真实峰值内存或全部组合已闭合。既有Z4 Path经验基线继续保留。','',
        '## 1. 执行与经典逻辑过程的耦合','',
        '固定地址/读写序列及全部初始叶、fresh-remap叶随机带。逻辑投影保留每个当前地址的(uid, leaf, payload, bucket)，bucket=0表示stash，删除密文、物理槽置换、认证标签及dummy。将uid顺序作为经典贪心算法允许的一种固定平局规则。','',
        '对完成态作归纳：空树与空stash投影相同。Path读取旧叶整条路径，把其中当前记录与stash合并，删除旧目标，生成一次新uid及新叶，按叶至根顺序逐桶填入至多Z个合格记录。桶外记录保持不动。这正是经典Path状态转移；payload更新不参与放置选择。目标不存在时返回零并首次生成记录，与原文空树初始化一致。','',
        '普通Ring的一次逻辑读仅移除旧目标，随后把新版本加入stash。其他桶记录保持位置。neutral只重排同一桶的剩余真实记录，不改变uid/leaf/payload/所属桶，也不推进t/g；count和used归零。融合步骤在此投影上等于neutral后移除目标，并保留逻辑消费后的count/used；这里使用冻结融合实现的完成态语义，不将此投影替代完整转录证明。每A次逻辑读之后，以g的L位逆序叶执行一次整路径贪心驱逐，随后g递增。实际Ring未施加selective放置约束。','',
        '因而成功认证前缀的逻辑放置逐步对应普通Path/Ring。认证失败后的执行不被当作另一个成功前缀；客户永久停止。经典Ring的无限桶/stale-block支配论证仍引用原论文§4及附录B，而不是用本次有限运行重新证明指数尾界。','',
        '初始化先建全dummy树，再从最深位置表向数据层逐块执行正常访问。因此第j层的初始化访问数精确为Σ(i=0..j)N_i。对固定应用地址历史，递归map地址由公开块打包函数确定，不依赖本层放置随机性；本结论不包含按私有stash命中、冲突或容量反馈改变访问调度的组合。','',
        '## 2. 访问完成边界与容量表达式','',
        'Path要求Z=5且N≤2^L，可令原定理的工作集上限为2^L；从空树开始的任意固定地址前缀满足14(3/5)^R。Z4并不因为运行未溢出而获得该定理覆盖。若R≥N，唯一当前版本不变量直接给出零stash溢出概率，无须尾界。','',
        'Ring在N≤A·2^(L−1)且q=Z ln(2Z/A)+A/2−Z−ln4>0时使用经典驱逐后界。为避免依赖阶段的隐含约定，本账本显式预留A−1：两次驱逐之间，每次逻辑访问至多净增一个stash记录，neutral不增加stash；完成态距上次驱逐至多A−1次。因此对R≥A−1，采用', '',
        '`ε_ring(R) ≤ min(1, (A/(2Z))^(R−A+1) / (1−exp(−q)))`。','',
        '首次驱逐之前stash最多A−1；t可整除A时先驱逐再检查R，和源码顺序一致。该余量是保守选择，并不声称原论文有错误。中途读取整条路径所需工作区不计入R；这不是可信内存峰值证明。','',
        '每层Q_j=2^56+Σ(i=0..j)N_i，按Σ_j Q_j ε_j作联合界，不假定各层失败独立。这里只分配stash失败预算2^-130；总ORAM优势还需要PRF/认证/模偏差与公开寿命执行限制的完整绑定，故回执的full_security_admission仍为false。','',
        '## 3. 当前核心的逐配置结果','',
        '| 配置 | Z/A/S | 当前R | 理想stash寿命上界log2 | 经典表达式需要的最小公共R |','|---|---|---:|---:|---:|']
    for row in bound['rows']:
        s=row['spec'];l=row['ledger'];name=('B1' if row['plan']=='formal_core_plan.json' else 'B3')+' '+s['kind']
        upper=f"{l['log2_lifetime_upper']:.6f}" if l['all_points_covered'] else 'Z4不获该定理覆盖'
        md.append(f"| {name} | {'/'.join(map(str,s['profile']))} | {s['R']} | {upper} | {row.get('minimum_common_R_for_classical_bound','—')} |")
    md.append(f"| 补充Path | 5/3/3 | {extra['minimum_common_R']} | {extra['ledger']['log2_lifetime_upper']:.6f} | {extra['minimum_common_R']} |")
    md+=['',
        'Ring两组现用R256在加入阶段余量后仍满足该stash预算。表内最小R只描述经典表达式，不改变任何已执行的R256正式配置。补充Path使用相同N16384/B4096、map B256、terminal上限8192及两种负载五个种子，调整Z5和R258；位置表层N256≤R258，采用确定性当前记录数界。','',
        '29号文档原先的2^96、2^-128算术表没有显式A−1阶段储备，保留为历史表达式；若将其用于任意完成访问边界，应使用下面保守修订。此表与上面实际递归2^56请求账本不是同一个寿命口径。','',
        '| Z/A | 示例树数K | R256时修订log2上界 | 修订最小R |','|---|---:|---:|---:|']
    for r in bound['historical_horizon_phase_corrections']:
        md.append(f"| {r['Z']}/{r['A']} | {r['K']} | {r['lifetime_log2_at_R256']:.6f} | {r['minimum_R']} |")
    md+=['','## 4. 独立核验覆盖','',
        f"- {checks['execution_cases']}组实际加密诊断，{checks['totals']['access_boundaries']}个访问完成态，逐地址核对uid/leaf/payload/所属桶，包含初始化、三层递归、集中叶碰撞、非空stash和两个Ring参数族。",
        f"- 显式neutral投影恒等检查{checks['totals']['neutral_identity']}次；融合逻辑读投影{checks['totals']['fused_logical_projection']}次，触发early桶{checks['totals']['fused_early_buckets']}个；定期驱逐{checks['totals']['scheduled_evictions']}次。",
        '- 算术核验用独立128阶指数包络检查生产者64阶上界，核对真实递归几何、初始化计数和全部有理数界；6种篡改账本均被拒绝。另独立验证三个最小公共R和四行历史阶段修订；最小值只针对所列保守表达式。',
        f"- {active['cases']}个主动响应检查覆盖opening、payload proof、ACK路由和重放，包括Path Z5与Ring Z7/S9的16槽布局；坏响应之后没有继续解密，提交锚点不变，后续不再发RPC。不声称服务器回滚。",
        '- 有限诊断提供源码绑定与反例发现能力，不把通过数量当作任意长度安全证明或性能样本。','',
        '## 5. 补充Path对照的预声明','',
        '`formal_classical_reference_plan.json`已在新测量前固定十个单元：uniform/hot90×seed101..105，暖机2048、测量4096请求，与B3的输入及随机种子逐一配对。使用已经过逐字节差分验证的bulk执行器；所有收发应用帧、认证、递归和维护均计费。周期模型为657456 bytes/op，尚不冒充该批次实测结果。','',
        '该组用于报告经典stash定理覆盖下的成本，不替换更强的Z4经验基线，也不以增大的Z制造主文优势。实际测量与原始来源另存results/formal_classical_reference；单worker有实际可用内存门槛，队列在内存不足时等待，不通过重启挤入任务。','',
        '## 来源与复核入口','',
        '- [Path ORAM JACM版](https://elaineshi.com/docs/pathoram.pdf)：§3.4–3.5、定理5.1。',
        '- [Ring ORAM USENIX版](https://www.usenix.org/system/files/conference/usenixsecurity15/sec15-paper-ren-ling.pdf)：§4及附录B。',
        '- `results/classical_execution_projection_checks.json`、`results/classical_stash_execution_ledger.json`、`results/classical_stash_execution_ledger_audit.json`、`results/classical_active_failstop_checks.json`：完整来源、逐格结果与checker哈希。',
        '- `results/classical_reference_evidence_audit.json`绑定本报告输入。所有冻结源码及正式worker未作修改；IR/AB的命中、green/CB、异质容量或DeadQ不能继承本账本。']
    report=PACKAGE/'45_经典基线执行归约与容量账本.md';report.write_text('\n'.join(md)+'\n',encoding='utf-8')
    save(PACKAGE/'results/classical_reference_evidence_audit.json',dict(status='evidence_consistent',
        source_receipts={name:sha(PACKAGE/'results'/name) for name in files},
        report_sha256=sha(report),builder_sha256=sha(__file__),
        plan_sha256=sha(PACKAGE/'formal_classical_reference_plan.json'),
        full_security_admission=False,formal_supplementary_performance_completed=False))
    print(json.dumps(dict(status='evidence_consistent',report=report.name)))


if __name__=='__main__':main()
