"""Independent Fraction enumeration for Z7/rate3; same test obligations as baseline."""
from fractions import Fraction as F
from collections import defaultdict
from pathlib import Path
import csv,json,subprocess,platform
ROOT=Path(__file__).resolve().parent

def exact_small(C=8,H=4,M=8):
    seed=json.loads((ROOT/'poisson_seed.json').read_text());poi=[F.from_float(float.fromhex(seed['upper_hex']))]
    for k in range(1,M+2):poi.append(poi[-1]*3/k)
    tau=poi[M+1]*F(M+2,M-1);mtail=3*poi[M]*F(M+1,M-2)
    p={(0,0,0):F(1)};bp=bm=F(0);answer=[]
    for h in range(1,H+1):
        mean=sum(sum(v)*q for v,q in p.items())+bm;nxt=defaultdict(F);ep=em=F(0)
        for lv,lp in p.items():
            for rv,rp in p.items():
                for k in range(M+1):
                    u=(max(0,sum(rv)+lv[2]+k-7),lv[0],lv[1]);w=lp*rp*poi[k]
                    if sum(u)<=C:nxt[u]+=w
                    else:ep+=w;em+=sum(u)*w
        bp,bm=2*bp+tau+ep,2*bm+2*(mean+3)*bp+2*mean*tau+mtail+em
        p=dict(nxt);answer.append(dict(h=h,bp=bp,bm=bm,sl=[sum(max(0,sum(v)-r)*q for v,q in p.items()) for r in range(C+1)]))
    return answer

def main():
    exact=exact_small();checks=0
    for mode in ('up','next'):
        prefix=ROOT/('validation_'+mode)
        subprocess.run([str(ROOT/'ghost_z7a6'),'8','4','8','1',mode,str(prefix)],check=True,capture_output=True)
        rows=list(csv.DictReader(open(str(prefix)+'.csv')));levels=list(csv.DictReader(open(str(prefix)+'_levels.csv')))
        for e in exact:
            lev=levels[e['h']-1]
            assert F.from_float(float.fromhex(lev['unknown_prob_hex']))>=e['bp'];checks+=1
            assert F.from_float(float.fromhex(lev['unknown_moment_hex']))>=e['bm'];checks+=1
            for r in range(9):
                row=rows[(e['h']-1)*9+r]
                assert F.from_float(float.fromhex(row['known_upper_hex']))>=e['sl'][r];checks+=1
                assert F.from_float(float.fromhex(row['total_upper_hex']))>=e['sl'][r]+e['bm'];checks+=1
    for threads in (1,4):
        subprocess.run([str(ROOT/'ghost_z7a6'),'32','8','32',str(threads),'up',str(ROOT/('threads'+str(threads)))],check=True,capture_output=True)
    assert (ROOT/'threads1.csv').read_bytes()==(ROOT/'threads4.csv').read_bytes()
    result=dict(Z=7,rate='3',exact_rational_inequalities=checks,thread_count_bitwise_match=True,
                python=platform.python_version(),platform=platform.platform(),
                compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
                flags=['-std=c++17','-O3','-fopenmp','-frounding-math','-ffp-contract=off','-fno-fast-math'])
    (ROOT/'validation_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
