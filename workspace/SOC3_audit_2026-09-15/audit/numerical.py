"""Independent rational oracle, full-joint witnesses and clean recomputation."""
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
import csv, hashlib, json, math, platform, re, subprocess

ROOT=Path(__file__).resolve().parents[1]
NUM=ROOT/'research_20260914/optimization_v1/numerics'
FLAGS=['-std=c++17','-O3','-fopenmp','-frounding-math','-ffp-contract=off','-fno-fast-math']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
dy=lambda s:F.from_float(float.fromhex(s))

def seed_check():
    doc=json.loads((NUM/'poisson_seed.json').read_text())
    assert (doc['rate_num'],doc['rate_den'],doc['terms'])==(3,1,128)
    term=T=F(1)
    for k in range(1,129):term*=F(3,k);T+=term
    remainder=term*F(3,129)/(1-F(3,130))
    lo,hi=1/(T+remainder),1/T
    assert tuple(map(str,(lo.numerator,lo.denominator)))==tuple(doc['rational_lower'])
    assert tuple(map(str,(hi.numerator,hi.denominator)))==tuple(doc['rational_upper'])
    assert dy(doc['lower_hex'])<=lo<hi<=dy(doc['upper_hex'])
    assert 'POISSON_ZERO_UPPER = '+doc['upper_hex'] in (NUM/'poisson_seed.h').read_text()
    assert dy(doc['upper_hex'])-dy(doc['lower_hex'])==F.from_float(math.ulp(float.fromhex(doc['upper_hex'])))
    return dy(doc['upper_hex'])

def exact(C=8,H=4,M=8):
    poi=[seed_check()]
    for k in range(1,M+2):poi.append(poi[-1]*F(3,k))
    tau=poi[M+1]*F(M+2,M-1);tp=3*poi[M]*F(M+1,M-2)
    p={(0,0,0):F(1)};bp=bm=F(0);out=[]
    for h in range(1,H+1):
        mu=sum(sum(u)*v for u,v in p.items())+bm
        nxt=defaultdict(F);ep=em=F(0)
        for left,lp in p.items():
            for right,rp in p.items():
                for arrival in range(M+1):
                    u=(max(0,sum(right)+left[2]+arrival-7),left[0],left[1])
                    w=lp*rp*poi[arrival]
                    if sum(u)<=C:nxt[u]+=w
                    else:ep+=w;em+=sum(u)*w
        bp,bm=2*bp+tau+ep,2*bm+2*(mu+3)*bp+2*mu*tau+tp+em
        p=dict(nxt)
        out.append(dict(h=h,p=p,bp=bp,bm=bm,ep=ep,em=em,mass=sum(p.values()),
                        mean=sum(sum(u)*v for u,v in p.items())+bm,
                        sl=[sum(max(0,sum(u)-r)*v for u,v in p.items()) for r in range(C+1)]))
    assert out[-1]['ep']>0 and out[-1]['em']>0 and out[0]['bp']>0
    assert len({sum(u) for u in p})>3 and any(all(u) and w for u,w in p.items())
    return out

def run(exe,args,prefix):
    p=subprocess.run([str(exe),*map(str,args),str(prefix)],check=True,capture_output=True,text=True)
    Path(str(prefix)+'.log').write_text(p.stderr)

def build(src,exe):
    subprocess.run(['g++',*FLAGS,str(src),'-I',str(NUM),'-o',str(exe)],check=True,capture_output=True)

def rows(prefix,suffix):return list(csv.DictReader(Path(str(prefix)+suffix).open()))

def check_small(prefix,oracle,joint=False):
    levels=rows(prefix,'_levels.csv');grid=rows(prefix,'.csv');checks=0
    def bound(got,want):
        nonlocal checks
        v=dy(got)
        assert v>=want,('not an upper bound',v,want)
        # Detect wrong but looser recurrences as well; this is an audit
        # diagnostic, not the mathematical upper-bound acceptance criterion.
        assert v<=want*(1+F(1,10**10)) or want==v==0,('wrong recurrence / unexpectedly loose small-domain result',v,want)
        checks+=1
    for e,lev in zip(oracle,levels):
        assert int(lev['height'])==e['h']
        for name,key in [('mass_upper_hex','mass'),('mean_upper_hex','mean'),('unknown_prob_hex','bp'),
                         ('unknown_moment_hex','bm'),('exit_prob_hex','ep'),('exit_moment_hex','em')]:bound(lev[name],e[key])
        for r in range(9):
            row=grid[(e['h']-1)*9+r]
            assert (int(row['height']),int(row['threshold']))==(e['h'],r)
            bound(row['known_upper_hex'],e['sl'][r]);bound(row['total_upper_hex'],e['sl'][r]+e['bm'])
    assert len(levels)==4 and len(grid)==36
    if joint:
        seen=set()
        for row in rows(prefix,'_joint.csv'):
            h=int(row['height']);u=tuple(int(row[k]) for k in ('a','b','c'));key=(h,*u)
            assert key not in seen;seen.add(key)
            bound(row['mass_hex'],oracle[h-1]['p'].get(u,F(0)))
        expected={(h,a,b,c) for h in range(1,5) for a in range(9) for b in range(9-a) for c in range(9-a-b)}
        assert seen==expected
    return checks

def audit(out,full=True,mutations=True):
    out.mkdir(parents=True,exist_ok=True)
    seed_check();source=(NUM/'ghost_z7a6.cpp').read_text()
    assert 'constexpr int Z=7;constexpr double rate=3.;' in source
    assert 'add(mean,rate)' in source and 'int u=cap+Z-j+1' in source
    assert 'np[s.row[d][a]+b]=q[d]' in source
    base=out/'kernel';build(NUM/'ghost_z7a6.cpp',base)
    # This injection only observes the retained PMF. Strip it to recover source.
    marker='p.swap(np);bp=nbp;bm=nbm;'
    injection='''
{std::ofstream joint(prefix+"_joint.csv", h==1?std::ios::out:std::ios::app);
if(h==1)joint<<"height,a,b,c,mass_hex\\n";
for(auto ab:s.pairs)for(int c=0;c<=cap-ab.first-ab.second;c++)
joint<<h<<','<<ab.first<<','<<ab.second<<','<<c<<','<<hx(p[s.row[ab.first][ab.second]+c])<<'\\n';}
'''
    observed=source.replace(marker,marker+injection)
    assert source.count(marker)==1 and observed.replace(injection,'')==source
    obs_src=out/'kernel_observed.cpp';obs_src.write_text(observed)
    obs=out/'kernel_observed';build(obs_src,obs)
    oracle=exact();count=0
    for mode in ('up','next'):
        plain=out/('small_'+mode);witness=out/('joint_'+mode)
        run(base,[8,4,8,1,mode],plain);run(obs,[8,4,8,1,mode],witness)
        assert Path(str(plain)+'.csv').read_bytes()==Path(str(witness)+'.csv').read_bytes()
        for x,y in zip(rows(plain,'_levels.csv'),rows(witness,'_levels.csv')):
            assert {k:v for k,v in x.items() if k!='seconds'}=={k:v for k,v in y.items() if k!='seconds'}
        count+=check_small(witness,oracle,joint=True)
    rejected=[]
    if mutations:
        changes={
            'rate_1_5':('constexpr double rate=3.;','constexpr double rate=1.5;'),
            'Phi4':('constexpr int Z=7;','constexpr int Z=4;'),
            'first_moment_rate_1_5':('add(mean,rate)','add(mean,1.5)'),
            'cap_exit_Z4':('int u=cap+Z-j+1','int u=cap+4-j+1'),
            'joint_coordinate_permutation':('np[s.row[d][a]+b]=q[d]','np[s.row[a][b]+d]=q[d]')}
        for name,(a,b) in changes.items():
            assert observed.count(a)==1
            src=out/(name+'.cpp');src.write_text(observed.replace(a,b));exe=out/name;build(src,exe)
            prefix=out/(name+'_result');run(exe,[8,4,8,1,'up'],prefix)
            try:check_small(prefix,oracle,joint=True)
            except AssertionError:rejected.append(name)
            else:raise AssertionError('mutation survived: '+name)
    invalid=subprocess.run([str(base),'8','4','6','1','up',str(out/'invalid_M')],capture_output=True)
    assert invalid.returncode!=0
    for n in (1,4):run(base,[32,8,32,n,'up'],out/('threads'+str(n)))
    assert sha(out/'threads1.csv')==sha(out/'threads4.csv')
    grids={}
    if full:
        for mode in ('up','next'):
            prefix=out/('full_'+mode);run(base,[280,24,128,4,mode],prefix)
            meta=json.loads(Path(str(prefix)+'_meta.json').read_text())
            assert (meta['Z'],meta['rate'],meta['height'],meta['cap'],meta['poisson_cutoff'])==(7,'3',24,280,128)
            assert meta['arithmetic']==mode and meta['rounding_self_test'] and not meta['renormalized'] and not meta['positive_states_discarded']
            assert dy(meta['poisson_zero_upper_hex'])==seed_check()
            poi=seed_check()
            for k in range(1,129):poi*=F(3,k)
            assert dy(meta['poisson_tail_prob_upper_hex'])>=poi*F(3,129)*F(130,127)
            assert dy(meta['poisson_tail_moment_upper_hex'])>=3*poi*F(129,126)
            values={}
            for r in rows(prefix,'.csv'):
                h,t=int(r['height']),int(r['threshold']);assert (h,t) not in values
                k,u,v=map(dy,(r['known_upper_hex'],r['unknown_moment_hex'],r['total_upper_hex']))
                assert k>=0 and u>=0 and v>=k+u;values[h,t]=v
            assert set(values)=={(h,t) for h in range(1,25) for t in range(281)}
            for h in range(1,25):assert all(values[h,t]>=values[h,t+1] for t in range(280))
            # Independent exact-dyadic audit of every full-grid error update.
            prev_prob=prev_moment=prev_mean=F(0)
            tau=dy(meta['poisson_tail_prob_upper_hex']);tp=dy(meta['poisson_tail_moment_upper_hex'])
            levels=rows(prefix,'_levels.csv');assert len(levels)==24
            for h,lev in enumerate(levels,1):
                assert int(lev['height'])==h
                ep,em=dy(lev['exit_prob_hex']),dy(lev['exit_moment_hex'])
                prob,moment,mean=dy(lev['unknown_prob_hex']),dy(lev['unknown_moment_hex']),dy(lev['mean_upper_hex'])
                assert ep>=0 and em>=0
                assert prob>=2*prev_prob+tau+ep
                assert moment>=2*prev_moment+2*(prev_mean+3)*prev_prob+2*prev_mean*tau+tp+em
                assert values[h,280]==moment and mean>=0
                prev_prob,prev_moment,prev_mean=prob,moment,mean
            same=sha(Path(str(prefix)+'.csv'))==sha(NUM/f'z7a6_{mode}_c280_h24.csv')
            # This release must reproduce the received endpoints on the
            # recorded toolchain. A changed compiler requires a new review.
            assert same,'different full-grid endpoints: review toolchain, do not reuse this release receipt'
            grids[mode]=dict(points=len(values),matches_received_hex_grid=same,full_level_error_propagations_checked=24,sha256=sha(Path(str(prefix)+'.csv')))
            print('numeric full',mode,'PASS',flush=True)
    result=dict(seed_recomputed_with_exact_rationals=True,exact_domain=dict(C=8,H=4,M=8),
                exact_inequalities_and_tightness_checks=count,joint_tuples_per_mode=660,
                nonzero_cap_exit_at_h4=True,mutants_rejected=rejected,invalid_M6_rejected=True,
                threads_1_4_match=True,full_grids=grids,compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
                flags=FLAGS,python=platform.python_version(),platform=platform.platform(),
                source_sha256=sha(NUM/'ghost_z7a6.cpp'),seed_sha256=sha(NUM/'poisson_seed.h'),
                inputs_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [Path(__file__),NUM/'ghost_z7a6.cpp',NUM/'poisson_seed.h',NUM/'poisson_seed.json']},
                outputs_sha256={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.suffix in ('.csv','.json','.cpp')})
    (out/'receipt.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--small-only',action='store_true')
    args=p.parse_args();print(json.dumps(audit(args.out,not args.small_only),indent=2))
