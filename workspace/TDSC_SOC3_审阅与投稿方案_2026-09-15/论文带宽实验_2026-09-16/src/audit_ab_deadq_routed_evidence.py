"""Recompute Merkle transitions and byte accounts from compressed wire files."""
from common import PACKAGE,save,sha
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import struct


def root_of(i,value,proof):
    tag=hashlib.sha256(b'DeadQ-row-v1\x00'+struct.pack('>II',i,len(value))+value).digest()
    for sibling in proof:
        left,right=(sibling,tag) if i%2 else (tag,sibling)
        tag=hashlib.sha256(b'DeadQ-node-v1\x00'+left+right).digest();i//=2
    assert i==0
    return tag


def inspect(frames,g):
    M,b,r,Q,B=[g[k] for k in ('buckets','base','extra','queue_cap','payload_bytes')]
    P=M*b;count=2+M+2*P;qindex=1+M+P;depth=(count-1).bit_length()
    total=Counter();root=None;tx=None;last_tx=0;step=0;new_nonces=set()
    for request,response in frames:
        total['rpc']+=1;total['request_bytes']+=len(request);total['response_bytes']+=len(response)
        op=request[0:1]
        if op==b'B':
            assert tx is None and len(request)==len(response)==41 and response==b'b'+request[1:]
            tx=struct.unpack('>Q',request[1:9])[0];assert tx==last_tx+1;last_tx=tx;step=0
            if root is not None:assert request[9:]==root
            root=request[9:];total['control_bytes']+=82;continue
        assert struct.unpack('>QI',request[1:13])==(tx,step)
        if op==b'C':
            assert len(request)==len(response)==45 and request[13:]==root and response==b'c'+request[1:]
            tx=None;total['control_bytes']+=90;total['commits']+=1;continue
        assert op in (b'G',b'U') and response[:17]==op.lower()+request[1:17]
        i=struct.unpack('>I',request[13:17])[0];assert 0<=i<count
        length=8 if i==0 else 12+5*(b+r) if i<=M else 16 if i<qindex else 4+12*Q if i==qindex else B+37
        assert struct.unpack('>I',response[17:21])[0]==length
        value=response[21:21+length];start=21+length
        assert len(response)==start+32*depth+(32 if op==b'U' else 0)
        proof=[response[start+32*j:start+32*(j+1)] for j in range(depth)]
        assert root_of(i,value,proof)==root
        category='data_record_bytes' if i>qindex else 'metadata_bytes'
        total[category]+=length;total['proof_bytes']+=32*depth;total['control_bytes']+=38
        if op==b'G':assert len(request)==17;total['reads']+=1
        else:
            assert len(request)==21+length and struct.unpack('>I',request[17:21])[0]==length
            root=root_of(i,request[21:],proof);assert response[-32:]==root
            total[category]+=length;total['control_bytes']+=36;total['updates']+=1
            if i>qindex:
                nonce=request[21:33];assert nonce not in new_nonces;new_nonces.add(nonce)
        step+=1
    assert tx is None
    total['total_bytes']=total['request_bytes']+total['response_bytes']
    assert total['total_bytes']==sum(total[k] for k in ('data_record_bytes','metadata_bytes','proof_bytes','control_bytes'))
    return dict(total)


def main():
    source=PACKAGE/'results/ab_deadq_routed_checks.json';a=json.loads(source.read_text())
    assert a['status']=='passed' and not a['native_AB'] and not a['CB_integration'] and not a['bandwidth_improvement_claim']
    for name,value in a['runtime_hashes'].items():assert sha(Path(__file__).parent/name)==value
    assert a['checker_sha256']==sha(Path(__file__).parent/'check_ab_deadq_routed_allocator.py')
    assert a['oracle_sha256']==sha(Path(__file__).parent/'ab_deadq_allocator_model.py')
    refs=[a['witness']]+a['trials'];checks=[]
    for ref in refs:
        p=PACKAGE/ref['wire']['path'];assert sha(p)==ref['wire']['sha256'];raw=gzip.decompress(p.read_bytes())
        assert hashlib.sha256(raw).hexdigest()==ref['wire']['uncompressed_sha256']
        frames=[(bytes.fromhex(x['request']),bytes.fromhex(x['response'])) for x in map(json.loads,raw.splitlines())]
        assert len(frames)==ref['wire']['frames']
        bill=inspect(frames,ref['geometry']);assert bill==ref.get('bill',ref.get('total_bill'))
        checks.append(dict(path=ref['wire']['path'],frames=len(frames),commits=bill['commits'],bill=bill))
    corruptions=[]
    for label,opcode,which in (('read proof',b'G',-1),('write proof/new root',b'U',-1),('final commit',b'C',-1)):
        damaged=list(frames);i=next(j for j,(q,r) in enumerate(damaged) if q[:1]==opcode);req,rep=damaged[i]
        rep=rep[:which]+bytes([rep[which]^1]) if which==-1 else rep
        damaged[i]=(req,rep)
        try:inspect(damaged,ref['geometry'])
        except AssertionError:corruptions.append(label)
        else:raise AssertionError('wire audit accepted '+label)
    assert len(a['negative_checks'])==13 and sum(x['transitions'] for x in a['trials'])==1000
    assert a['public_shape_check']['equal_address_length_shapes']
    w=a['witness'];bill=w['total_bill'];steps=w['steps']
    md=['# AB DeadQ：认证外部索引与加密记录路由','',
        '52号文档的公共分配模型现已增加实际认证外部索引、AES-GCM密文记录和串行提交接口。该模块仍是单层分配器原型，不是完整AB或CB/Selective ORAM；不从微观账单推断应用请求的带宽收益。','',
        '## 实现与信任边界','',
        '- 映射、有效位、反向所有权、generation、bucket epoch、FIFO及scheduled计数保存在服务器Merkle行存储。客户端按需取行并验证当前根；运行时不调用原来的全状态Allocator，也不常驻O(P)所有权数组。',
        '- 组件发现同时遍历逻辑映射与物理home的反向所有者，并验证双向一致。队列最多Q项，组件最多K桶；组件和候选供给者所需行只在本事务缓存，提交后清空。队列扫描及其认证通信实际计费。',
        '- 数据采用256位AES-GCM密钥、96位单调nonce及128位tag；固定记录含dummy标志、UID和B字节payload。AAD绑定实例/几何摘要、logical bucket/slot、physical地址、epoch与generation。先验证Merkle打开，再解密记录。AES-GCM行为参照[官方文档](https://cryptography.io/en/latest/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM)。',
        '- 每个输出槽（包括dummy）重加密，私有打乱不改变公共输出长度。nonce在准备阶段分配，错误后永久停止，不回滚重用。可复现测试密钥是公开夹具；默认provision使用新随机密钥，部署不可重复实例密钥后重置nonce。',
        '- 所有写入在服务器working tree中完成。客户端验证每次旧行证明、推导更新根，最后核对tx/step/root提交响应后才发布新可信根并返回消费记录。未提交时第二个操作不准入，fusion产生的dead租用因此不能提前出借。',
        '- 最终响应一致性不保证恶意服务器持久保存数据；后续不一致会被打开证明拒绝。坏最终ACK可能发生在服务器已写入后，客户端永久停止，不能声称服务器回滚或故障恢复。串行、无重启可信客户端是当前前提。','',
        'generation和bucket epoch仍不是SOC3的γ。此模块没有目标叶fresh remap、CB动态阈值、green迁移、跨层位置表或scheduled球箱放置；这些必须在引擎集成时绑定，不能由本检查代替。','',
        '## 检查结果','',
        '| 检查 | 结果 |','|---|---|',
        '| 加密状态与独立全状态oracle逐步对照 | 五个种子×200步；1,000次完成态，111次扩张、101次连带重建；映射/队列/epoch/version及真实记录集合逐项一致 |',
        '| 错误响应和上下文 | 13项：目录proof、密文、更新根、错误ACK、旧ACK、重放FIFO，以及六个AEAD上下文字段和nonce中止；全部fail-stop |',
        '| 公共访问形状 | 固定120个公共操作，比较全dummy与每桶一个真实记录、不同密钥和私有打乱；访问地址与请求/回复长度相同；有限检查不等于转录证明 |',
        f"| 独立原始wire核验 | 六个gzip原始帧文件，{sum(x['frames'] for x in checks):,}个RPC、1,006次提交；逐次重算Merkle根及四类字节，另拒绝三类故意损坏的帧 |",'',
        '测试中的全状态扫描、payload oracle和原始wire记录属于独立测试工具，运行时客户端不使用它们。初始化通过可信provision构建全表，它的临时内存不被声称为常数；以下事务账单不包含setup，持久对象大小单列。','',
        '## 四物理槽的真实密文见证','',
        'M2/b2/r1/K2/Q4/B64。初始真实UID91归B；两次scheduled暖机、消费A两槽后，B借A的物理槽0，并把UID91的密文放在该远端槽。随后触发A重建，必须先暂存{A,B}，UID91回到B的新合法槽。全过程物理数据槽数仍为4；额外metadata和Merkle树不是免费存储。','',
        '| 操作 | RPC | 数据记录字节 | 索引字节 | proof字节 | 控制字节 | 双向总字节 |','|---|---:|---:|---:|---:|---:|---:|']
    labels=['A scheduled暖机','B scheduled暖机','消费A槽0','消费A槽1','B扩张，借入物理槽0','A触发{A,B}联合重建']
    for label,step in zip(labels,steps):
        x=step['bill'];md.append('| '+label+' | '+' | '.join(f"{x[k]:,}" for k in ('rpc','data_record_bytes','metadata_bytes','proof_bytes','control_bytes','total_bytes'))+' |')
    md+=['| 合计 | '+' | '.join(f"{bill[k]:,}" for k in ('rpc','data_record_bytes','metadata_bytes','proof_bytes','control_bytes','total_bytes'))+' |','',
        f"总计{bill['total_bytes']:,}字节，数据记录占{100*bill['data_record_bytes']/bill['total_bytes']:.2f}%，其余索引、证明及控制占{100*(1-bill['data_record_bytes']/bill['total_bytes']):.2f}%。这是当前逐行证明、逐次RPC实现的微观代价，不是不可降低的理论下界，也不是相对Ring的提升率。合并证明或批量提交有潜在空间，必须保留相同认证语义再实测。",'',
        f"该例服务器提交态序列化行共{w['provisioned_row_bytes']}字节，Merkle标签共{w['server_merkle_tag_bytes']}字节；不包含语言对象开销与working tree副本。根、密钥、domain、nonce和计数器等选定持久字段共{w['trusted_serialized_root_key_domain_counters_bytes']}字节，但这不是客户端总内存：几何、密码运行库、payload staging、缓存行、准备写回及proof scratch均需另计。禁止把该数字称为可信峰值。",'',
        '## 下一步与结果使用限制','',
        '真正的组合性能实验需要将此路由层接入Ring+CB、GC-Ring+CB和R0+CB，统一物理空间、动态n/τ、随机数域及认证语义。联合neutral与scheduled放置必须区分，γ不得被借槽epoch替代；同一公共策略下比较完整请求的全部字节。当前ABDF的约20%–22%仍属于无DeadQ条件协议，不能移植为本新层的收益。','',
        '容量/green尾界、自适应转录证明、真实可信峰值、重启恢复和原生AB等价性均未完成。现有加密检查补上了“外部索引与实际数据路由”这一段，不将整体工作标为闭合。','',
        '复现入口：`src/check_ab_deadq_routed_allocator.py`，随后`src/audit_ab_deadq_routed_evidence.py`。原始帧及元数据在`results/ab_deadq_routed_wire/`和`results/ab_deadq_routed_checks.json`；运行中的AB/IR/核心源文件未改动。']
    report=PACKAGE/'54_AB_DeadQ认证路由与加密检查.md';report.write_text('\n'.join(md)+'\n',encoding='utf-8')
    out=dict(status='passed',source_sha256=sha(source),report_sha256=sha(report),auditor_sha256=sha(__file__),
        traces=checks,rejected_wire_corruptions=corruptions,native_AB=False,CB_integration=False,security_proof=False,bandwidth_improvement_claim=False)
    save(PACKAGE/'results/ab_deadq_routed_evidence_audit.json',out)
    print(json.dumps(dict(status='passed',frames=sum(x['frames'] for x in checks),commits=sum(x['commits'] for x in checks),wire_corruptions=len(corruptions),report=report.name)))


if __name__=='__main__':main()
