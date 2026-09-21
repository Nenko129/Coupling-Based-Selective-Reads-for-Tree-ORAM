"""Depth-dependent Phi_Z / Poi(lambda) verifier fork and rational seed inputs."""
from common import *
from fractions import Fraction as F
import math,difflib

NUM=PACKAGE/'numerics'

def seed(x,terms=160):
    term=partial=F(1)
    for k in range(1,terms+1):term=term*x/k;partial+=term
    omitted=term*x/(terms+1);tail=omitted/(1-x/(terms+2));lo=1/(partial+tail);hi=1/partial
    lf,hf=float(lo),float(hi)
    if F.from_float(lf)>lo:lf=math.nextafter(lf,-math.inf)
    if F.from_float(hf)<hi:hf=math.nextafter(hf,math.inf)
    assert F.from_float(lf)<=lo<=hi<=F.from_float(hf)
    return dict(rate=str(x),terms=terms,lower_hex=lf.hex(),upper_hex=hf.hex(),
                rational_lower=str(lo),rational_upper=str(hi),proof='positive exp(x) Taylor sum and geometric remainder, reciprocal and outward dyadic rounding')

def write_profile(name,z,rates):
    assert len(z)==len(rates);seeds={str(x):seed(x) for x in sorted(set(rates))}
    text=''.join(f'{zz} {rr.numerator} {rr.denominator} {seeds[str(rr)]["upper_hex"]}\n' for zz,rr in zip(z,rates))
    path=NUM/'profiles'/f'{name}.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='ascii')
    save(path.with_suffix('.json'),dict(name=name,Z_root_to_leaf=z,lambda_root_to_leaf=list(map(str,rates)),seeds=seeds,
         profile_text_sha256=sha(path),scope='independent-Poisson field recurrence; protocol reduction is a separate obligation'))

def main():
    NUM.mkdir(exist_ok=True);source=FROZEN.parent/'numerics/ghost_z7a6.cpp';old=source.read_text(encoding='utf-8');s=old
    def change(a,b):
        nonlocal s
        assert s.count(a)==1,(a[:80],s.count(a));s=s.replace(a,b)
    change('#include "poisson_seed.h"','#include <cstdlib>')
    change('if(argc!=7)','if(argc!=8)')
    change('constexpr int Z=7;constexpr double rate=3.;','''
std::ifstream input(argv[7]);std::vector<int>Zs;std::vector<double>rates,seeds;
int zz,nn,dd;std::string sh;
while(input>>zz>>nn>>dd>>sh){
 if(zz<1||zz>8||nn<1||dd<1||(dd&(dd-1))||double(nn)/dd>=M+1)throw std::invalid_argument("profile values");
 char* end=nullptr;double sd=std::strtod(sh.c_str(),&end);if(!end||*end||!(sd>0&&sd<=1))throw std::invalid_argument("seed parse");
 Zs.push_back(zz);rates.push_back(double(nn)/dd);seeds.push_back(sd);
}
if(int(Zs.size())!=height||!input.eof())throw std::invalid_argument("profile length/format");
''')
    a=s.index('std::vector<double>poi(M+2,0.);');b=s.index('Simplex s(cap);',a)
    block=s[a:b].replace('POISSON_ZERO_UPPER','seeds[height-h]');s=s[:a]+s[b:]
    change('for(int h=1;h<=height;h++){','for(int h=1;h<=height;h++){\nint Z=Zs[height-h];double rate=rates[height-h];\n'+block)
    change('std::ofstream csv(prefix+".csv"),log(prefix+"_levels.csv"),meta(prefix+"_meta.json");',
           'std::ofstream csv(prefix+".csv"),log(prefix+"_levels.csv"),meta(prefix+"_meta.json"),joint;\nif(cap<=16){joint.open(prefix+"_joint.csv");joint<<"height,a,b,c,upper_hex\\n";}')
    change('set_rounding();p.swap(np);bp=nbp;bm=nbm;',
           '''set_rounding();p.swap(np);bp=nbp;bm=nbm;
if(joint){for(auto ab:s.pairs){int a=ab.first,b=ab.second;for(int cc=0;cc<=cap-a-b;cc++)if(p[s.row[a][b]+cc]!=0)joint<<h<<','<<a<<','<<b<<','<<cc<<','<<hx(p[s.row[a][b]+cc])<<'\\n';}joint.flush();}
''')
    start=s.index('meta<<"{\\n');end=s.index('return 0;',start)
    s=s[:start]+'''meta<<"{\\n  \\"model\\": \\"m2-depth-profile-independent-Poisson-ghost\\",\\n  \\"cap\\": "<<cap<<",\\n  \\"height\\": "<<height<<",\\n  \\"poisson_cutoff\\": "<<M<<",\\n  \\"arithmetic\\": \\""<<mode<<"\\",\\n  \\"Z_root_to_leaf\\": [";
for(int d=0;d<height;d++){if(d)meta<<',';meta<<Zs[d];}meta<<"],\\n  \\"rate_root_to_leaf\\": [";
for(int d=0;d<height;d++){if(d)meta<<',';meta<<rates[d];}meta<<"],\\n  \\"seed_upper_root_to_leaf\\": [";
for(int d=0;d<height;d++){if(d)meta<<',';meta<<"\\""<<hx(seeds[d])<<"\\"";}
meta<<"],\\n  \\"rounding_self_test\\": true,\\n  \\"renormalized\\": false,\\n  \\"positive_states_discarded\\": false\\n}\\n";
''' .replace('\\"','\\"')+s[end:]
    target=NUM/'ghost_profile.cpp';target.write_text(s,encoding='utf-8')
    (NUM/'profile_kernel.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='frozen/ghost_z7a6.cpp',tofile='evaluation/ghost_profile.cpp')),encoding='utf-8')
    native=[4]*10+[2]*7+[3]*3+[4]*5
    for L in (10,12,14):
        z=[native[min(24,25*d//(L+1))] for d in range(L+1)]
        write_profile(f'IR43_scaled_L{L}',z,[F(3,2)]*(L+1))
    write_profile('IR43_native_leaf4',native,[F(3,2)]*24+[F(4)])
    write_profile('uniform43_h13',[4]*13,[F(3,2)]*13)
    write_profile('uniform76_h12',[7]*12,[F(3)]*12)
    for name,z,rr in [('small_mixed',[4,1,3],[F(3,2),F(3),F(4)]),('small_uniform7',[7]*3,[F(3)]*3),('small_uniform4',[4]*3,[F(3,2)]*3)]:
        write_profile(name,z,rr)
    save(NUM/'generation_receipt.json',dict(source_sha256=sha(source),output_sha256=sha(target),generator_sha256=sha(__file__),
         scope='unvalidated generated kernel; must compile, run rounding/pointwise checks and audit before numerical admission'))
    print(str(target))
if __name__=='__main__':main()
