"""Exact arithmetic for published classical stash bounds, not protocol admission."""
from common import *
from fractions import Fraction as F
import math


def pack(x):return dict(numerator=str(x.numerator),denominator=str(x.denominator))


def exp_interval(x,m=64):
    assert x>=0 and F(x,m+2)<1
    term=F(1);partial=term
    for k in range(1,m+1):term=term*x/k;partial+=term
    nextterm=term*x/(m+1)
    return partial,partial+nextterm/(1-x/(m+2))


def ring_constants(Z,A):
    rho=F(A,2*Z);x=F(2*Z-A,2)
    if rho>=1:return None
    lower,upper=exp_interval(x);beta=4*rho**Z*upper
    return dict(rho=rho,x=x,exp_lower=lower,exp_upper=upper,beta_upper=beta)


def min_r(fn,target):
    for r in range(4097):
        if fn(r)<=target:return r
    raise AssertionError('search range insufficient')


def main():
    Q=2**96;target=F(1,2**128);rows=[]
    for K in (1,16):
        for Z,A in ((4,3),(7,6),(5,5)):
            c=ring_constants(Z,A);admissible=c is not None and c['beta_upper']<1
            r=dict(protocol='classical_ring',Z=Z,A=A,R=256,tree_union_factor=K,per_tree_access_bound=str(Q),
                theorem_parameter_test=admissible,executed_protocol_admitted=False)
            if c is not None:r['constants']={key:pack(v) for key,v in c.items()}
            if admissible:
                bound=lambda R:K*Q*c['rho']**R/(1-c['beta_upper'])
                r.update(lifetime_stash_upper=pack(bound(256)),display_log2_upper=math.log2(bound(256)),
                    meets_stash_budget=bound(256)<=target,min_R_for_stash_budget=min_r(bound,target),
                    formula='K Q (A/(2Z))^R / (1-beta_upper)')
            else:r.update(meets_stash_budget=None,reason='published q>0 condition not certified; this is not evidence of insecurity')
            rows.append(r)
        bound=lambda R:K*Q*14*F(3,5)**R
        rows.append(dict(protocol='classical_path',Z=5,A=None,R=256,tree_union_factor=K,per_tree_access_bound=str(Q),
            theorem_parameter_test=True,executed_protocol_admitted=False,formula='K Q 14 (3/5)^R',
            lifetime_stash_upper=pack(bound(256)),display_log2_upper=math.log2(bound(256)),
            meets_stash_budget=bound(256)<=target,min_R_for_stash_budget=min_r(bound,target)))
    sources={name:dict(path=str(ROOT/'baselines'/f'{name}.pdf'),sha256=sha(ROOT/'baselines'/f'{name}.pdf'),
        pdf_page=page,visual_reference_sha256=sha(ROOT/'tmp/pdfs'/f'{name}_capacity-{page}.png')) for name,page in (('path',11),('ring',10))}
    out=dict(status='published_bound_arithmetic_only',sources=sources,rows=rows,stash_budget=pack(target),
        exp_truncation_degree=64,producer_sha256=sha(__file__),full_security_admission=False,
        exclusions=['Path Z4 theorem unavailable here','CB green, IR heterogeneity, cache-driven lifetimes and new protocols require separate reduction',
            'initialization, between-service boundaries, recursion schedule, placement tie-breaking and crypto budget still need execution binding'])
    save(PACKAGE/'results/baseline_capacity_arithmetic.json',out)
    md=['# 基线容量定理与精确参数核对','',
        '本表核对原论文定理的数值条件，不给当前执行程序自动签发安全准入。目的在于区分“已实际测量的较强经验基线”和“与Selective同寿命、同失败预算的有证明基线”。','',
        '原文已逐页渲染核对：Path JACM版PDF第11页定理5.1；Ring USENIX版PDF第10页§4.3。','',
        '## 原论文适用范围','',
        '- Path：Z=5、L=ceil(log2 N)，单前缀尾界为14(3/5)^R。当前Z4不能直接套该定理。',
        '- Ring：N<=A*2^(L-1)，令a=A/2；要求Z>a且q=Z ln(Z/a)+a-Z-ln4>0。单前缀尾界为(a/Z)^R/(1-exp(-q))。dummy槽S不出现在该经典占用界中；这不意味着任意CB/动态槽协议均被覆盖。','',
        '## 统一寿命预算的数值核对','',
        '下面取每树最多2^96次访问、仅stash失败预算2^-128。K=1为单树，K=16是明确标注的保守多树示例，尚未绑定各实验实际递归层数。认证/PRF等失败预算另外计算。R均先取当前核心实验常用的256。','',
        '| 经典协议 | Z/A | K | log2(寿命stash上界)，仅显示取近似 | 该界能否满足2^-128 | 使该界满足目标的最小R |',
        '|---|---|---:|---:|---|---:|']
    for r in rows:
        label='Ring' if r['protocol']=='classical_ring' else 'Path'
        z=f"{r['Z']}/{r['A']}" if r['A'] is not None else str(r['Z'])
        numeric='条件不满足' if 'display_log2_upper' not in r else f"{r['display_log2_upper']:.3f}"
        verdict='不可套用该界' if r['meets_stash_budget'] is None else ('是' if r['meets_stash_budget'] else '不足以证明')
        md.append(f"| {label} | {z} | {r['tree_union_factor']} | {numeric} | {verdict} | {r.get('min_R_for_stash_budget','—')} |")
    md+=['','所有通过/不通过及最小R判断使用有理数；浮点log2只用于表格显示。令rho=A/(2Z)，beta=4 exp(Z-A/2)rho^Z=exp(-q)。用64阶Taylor和及几何余项上界包住指数，再以beta_upper<1替代q的浮点判断。','',
        'Path的R256上界不足不等于该配置实际不安全；它说明不能用这个较松的经典界声称达到上述寿命预算。应保留Z4经验基线，并另增经证明覆盖的Z5/足够R参照，或提供更强的适用界。Ring的4/3和7/6通过的是参数算术条件；原型与经典过程的逐阶段归约尚须完成。','',
        '## 尚须绑定到执行的事项','',
        '逐层N/L、空树加载、每次访问与定期维护先后顺序、服务间stash检查、放置顺序、fusion的占用投影、递归输入适应性和总访问预算都须核对。Deferred不能仅因为使用相同Z/A就改名为经典Ring已证；AB的green迁移也不能套此表。','',
        '证据为 `results/baseline_capacity_arithmetic.json`，包含所有有理数分子分母、原PDF哈希和精确页图哈希；独立复算检查见 `results/baseline_capacity_arithmetic_audit.json`。']
    (PACKAGE/'29_基线容量定理与参数核对.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(dict(rows=len(rows),numeric_certified=sum(r['meets_stash_budget'] is True for r in rows),execution_admitted=False)))


if __name__=='__main__':main()
