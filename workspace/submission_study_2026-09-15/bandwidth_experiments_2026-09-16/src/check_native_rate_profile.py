"""Additional exact PMF check for the native-load sensitivity's new rates."""
from common import *
from build_profile_numerics import write_profile, NUM
from check_profile_numerics import exact_layers, read_joint, linux
from fractions import Fraction as F
import subprocess,csv

def main():
    name='small_native_rate';path=NUM/'profiles'/f'{name}.txt'
    assert not path.exists()
    write_profile(name,[2,3,4],[F(1,2),F(1),F(35,8)])
    profile=json.loads(path.with_suffix('.json').read_text());exact=exact_layers(profile,6,8);rows=[]
    for mode in ('up','next'):
        prefix=NUM/'checks'/f'{name}_{mode}'
        command=['wsl','--exec',linux(NUM/'ghost_profile'),'6','3','8','1',mode,linux(prefix),linux(path)]
        with prefix.with_suffix('.log').open('w',encoding='utf-8') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        joint=read_joint(prefix.with_name(prefix.name+'_joint.csv'))
        levels=list(csv.DictReader(prefix.with_name(prefix.name+'_levels.csv').open()))
        count=0
        for h,ex in enumerate(exact,1):
            for state,prob in ex['pmf'].items():assert joint[h].get(state,F(0))>=prob
            count+=len(ex['pmf'])
            assert F.from_float(float.fromhex(levels[h-1]['exit_prob_hex']))>=ex['exit_probability']
            assert F.from_float(float.fromhex(levels[h-1]['exit_moment_hex']))>=ex['exit_moment']
        for row in csv.DictReader(prefix.with_suffix('.csv').open()):
            h,r=int(row['height']),int(row['threshold'])
            sl=sum(prob*max(0,sum(state)-r) for state,prob in exact[h-1]['pmf'].items())
            known=F.from_float(float.fromhex(row['known_upper_hex']));unknown=F.from_float(float.fromhex(row['unknown_moment_hex']))
            assert known>=sl and F.from_float(float.fromhex(row['total_upper_hex']))>=known+unknown
        rows.append(dict(mode=mode,pointwise_states=count,joint_sha256=sha(prefix.with_name(prefix.name+'_joint.csv'))))
    save(NUM/'native_rate_exact_checks.json',dict(status='passed',rows=rows,profile_sha256=sha(path),
         kernel_sha256=sha(NUM/'ghost_profile.cpp'),binary_sha256=sha(NUM/'ghost_profile'),checker_sha256=sha(__file__)))
    print(json.dumps(dict(status='passed',rows=rows)))
if __name__=='__main__':main()
