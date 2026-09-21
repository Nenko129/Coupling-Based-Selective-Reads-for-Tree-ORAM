"""Independent exact Cartesian joint PMF checks for depth-dependent kernel."""
from common import *
from fractions import Fraction as F
from collections import defaultdict
import csv,subprocess,math,time

NUM=PACKAGE/'numerics'
def linux(p):return '/mnt/d/'+str(Path(p).relative_to(Path('D:/'))).replace('\\','/')
def read_joint(path):
    out=defaultdict(dict)
    for r in csv.DictReader(path.open()):out[int(r['height'])][int(r['a']),int(r['b']),int(r['c'])]=F.from_float(float.fromhex(r['upper_hex']))
    return out

def exact_layers(profile,cap,M):
    z=profile['Z_root_to_leaf'];rates=list(map(F,profile['lambda_root_to_leaf']));p={(0,0,0):F(1)};out=[]
    for zz,rate in reversed(list(zip(z,rates))):
        pp=[F.from_float(float.fromhex(profile['seeds'][str(rate)]['upper_hex']))]
        for k in range(1,M+1):pp.append(pp[-1]*rate/k)
        nxt=defaultdict(F);ep=F(0);em=F(0)
        for left,lp in p.items():
            for right,rp in p.items():
                for k,kp in enumerate(pp):
                    target=(max(0,sum(right)+left[2]+k-zz),left[0],left[1]);weight=lp*rp*kp
                    if sum(target)<=cap:nxt[target]+=weight
                    else:ep+=weight;em+=weight*sum(target)
        p=dict(nxt);out.append(dict(pmf=p,exit_probability=ep,exit_moment=em))
    return out

def main():
    rows=[]
    for name in ('small_mixed','small_uniform7','small_uniform4'):
        path=NUM/'profiles'/f'{name}.txt';profile=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        assert profile['profile_text_sha256']==sha(path)
        exact=exact_layers(profile,6,8)
        for mode in ('up','next'):
            prefix=NUM/'checks'/f'{name}_{mode}';prefix.parent.mkdir(exist_ok=True)
            cmd=['wsl','--exec',linux(NUM/'ghost_profile'),'6','3','8','1',mode,linux(prefix),linux(path)]
            with prefix.with_suffix('.log').open('w',encoding='utf-8') as log:
                subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
            meta=json.loads(prefix.with_name(prefix.name+'_meta.json').read_text())
            assert meta['Z_root_to_leaf']==profile['Z_root_to_leaf']
            assert list(map(F,meta['rate_root_to_leaf']))==list(map(F,profile['lambda_root_to_leaf']))
            assert meta['rounding_self_test'] and not meta['renormalized'] and not meta['positive_states_discarded']
            joint=read_joint(prefix.with_name(prefix.name+'_joint.csv'));checked=0
            levels=list(csv.DictReader(prefix.with_name(prefix.name+'_levels.csv').open()))
            for h,ex in enumerate(exact,1):
                for state,prob in ex['pmf'].items():assert joint[h].get(state,F(0))>=prob,(name,mode,h,state)
                checked+=len(ex['pmf'])
                assert F.from_float(float.fromhex(levels[h-1]['exit_prob_hex']))>=ex['exit_probability']
                assert F.from_float(float.fromhex(levels[h-1]['exit_moment_hex']))>=ex['exit_moment']
            for row in csv.DictReader(prefix.with_suffix('.csv').open()):
                h,r=int(row['height']),int(row['threshold']);sl=sum(prob*max(0,sum(state)-r) for state,prob in exact[h-1]['pmf'].items())
                known=F.from_float(float.fromhex(row['known_upper_hex']));unknown=F.from_float(float.fromhex(row['unknown_moment_hex']))
                total=F.from_float(float.fromhex(row['total_upper_hex']))
                assert known>=sl and total>=known+unknown
            rows.append(dict(profile=name,mode=mode,pointwise_joint_states_checked=checked,exact_cap_exit_probability_and_moment=True,stoploss_all_thresholds=True))
    save(NUM/'exact_checks.json',dict(status='passed',rows=rows,kernel_sha256=sha(NUM/'ghost_profile.cpp'),binary_sha256=sha(NUM/'ghost_profile'),
         checker_sha256=sha(__file__),scope='finite cap6/height3/M8 exact polynomial checks; not the practical-height certificate or protocol reduction'))
    print(json.dumps(dict(status='passed',cases=len(rows),states=sum(r['pointwise_joint_states_checked'] for r in rows))))
if __name__=='__main__':main()
