// Scalar nonnegative upper enclosure for the m=2 independent Poisson ghost.
// Certifies this recursion, not the actual-to-ghost protocol reduction.
// g++ -std=c++17 -O3 -fopenmp -frounding-math -ffp-contract=off -fno-fast-math
// usage: ./ghost_scalar CAP HEIGHT POISSON_CUTOFF THREADS up|next OUTPUT_PREFIX
#pragma STDC FENV_ACCESS ON
#include <algorithm>
#include <cfenv>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <omp.h>
#ifdef __SSE__
#include <xmmintrin.h>
#endif
#include <cstdlib>
static bool next_mode=false;
static inline double add(double x,double y){double z=x+y;if(next_mode&&x!=0&&y!=0)z=std::nextafter(z,INFINITY);return z;}
static inline double mul(double x,double y){if(x==0||y==0)return 0;double z=x*y;if(next_mode)z=std::nextafter(z,INFINITY);return z;}
static inline double divu(double x,double y){if(x==0)return 0;double z=x/y;if(next_mode)z=std::nextafter(z,INFINITY);return z;}
static void set_rounding(){
#ifdef __SSE__
_mm_setcsr(_mm_getcsr() & ~(unsigned(1u<<15)|unsigned(1u<<6)));
#endif
if(std::fesetround(next_mode?FE_TONEAREST:FE_UPWARD)!=0)throw std::runtime_error("cannot set rounding");
}
static void self_test(){
set_rounding();volatile double one=1.,tiny=0x1p-54,smallest=std::numeric_limits<double>::denorm_min(),two=2.;
if(add(one,tiny)<=1.)throw std::runtime_error("addition self-test");
if(divu(smallest,two)!=smallest)throw std::runtime_error("subnormal self-test");
if(!std::numeric_limits<double>::is_iec559)throw std::runtime_error("not IEEE754");
}
struct Simplex{
int cap;size_t size=0;std::vector<std::vector<size_t>>row;std::vector<std::pair<int,int>>pairs;
explicit Simplex(int c):cap(c),row(c+1){for(int a=0;a<=c;a++){row[a].resize(c-a+1);for(int b=0;b<=c-a;b++){row[a][b]=size;size+=size_t(c-a-b+1);pairs.emplace_back(a,b);}}}
};
static std::vector<double>totals(const Simplex&s,const std::vector<double>&p){
std::vector<double>f(s.cap+1,0.);for(auto ab:s.pairs){int a=ab.first,b=ab.second;size_t off=s.row[a][b];for(int c=0;c<=s.cap-a-b;c++)f[a+b+c]=add(f[a+b+c],p[off+c]);}return f;}
static double moment(const std::vector<double>&f){double m=0.;for(size_t s=1;s<f.size();s++)m=add(m,mul(double(s),f[s]));return m;}
static std::string hx(double x){std::ostringstream o;o<<std::hexfloat<<x;return o.str();}
int main(int argc,char**argv){try{
if(argc!=8)throw std::invalid_argument("CAP HEIGHT POISSON_CUTOFF THREADS up|next OUTPUT_PREFIX");
int cap=std::stoi(argv[1]),height=std::stoi(argv[2]),M=std::stoi(argv[3]),threads=std::stoi(argv[4]);std::string mode=argv[5],prefix=argv[6];
if(cap<4||cap>1000||height<1||height>64||M<7||M>512||threads<1||(mode!="up"&&mode!="next"))throw std::invalid_argument("guardrails");
next_mode=mode=="next";self_test();omp_set_num_threads(threads);

std::ifstream input(argv[7]);std::vector<int>Zs;std::vector<double>rates,seeds;
int zz,nn,dd;std::string sh;
while(input>>zz>>nn>>dd>>sh){
 if(zz<1||zz>8||nn<1||dd<1||(dd&(dd-1))||double(nn)/dd>=M+1)throw std::invalid_argument("profile values");
 char* end=nullptr;double sd=std::strtod(sh.c_str(),&end);if(!end||*end||!(sd>0&&sd<=1))throw std::invalid_argument("seed parse");
 Zs.push_back(zz);rates.push_back(double(nn)/dd);seeds.push_back(sd);
}
if(int(Zs.size())!=height||!input.eof())throw std::invalid_argument("profile length/format");

Simplex s(cap);std::vector<double>p(s.size,0.),np(s.size,0.);p[0]=1.;double bp=0.,bm=0.;
std::ofstream csv(prefix+".csv"),log(prefix+"_levels.csv"),meta(prefix+"_meta.json"),joint;
if(cap<=16){joint.open(prefix+"_joint.csv");joint<<"height,a,b,c,upper_hex\n";}
if(!csv||!log||!meta)throw std::runtime_error("outputs");
csv<<"height,threshold,known_upper_hex,unknown_moment_hex,total_upper_hex,total_upper_decimal\n";
log<<"height,mass_upper_hex,mean_upper_hex,unknown_prob_hex,unknown_moment_hex,exit_prob_hex,exit_moment_hex,seconds\n";
std::cerr<<"states="<<s.size<<" bytes="<<16*s.size<<" mode="<<mode<<" threads="<<threads<<"\n";
for(int h=1;h<=height;h++){
int Z=Zs[height-h];double rate=rates[height-h];
std::vector<double>poi(M+2,0.);poi[0]=seeds[height-h];
for(int k=1;k<=M+1;k++)poi[k]=divu(mul(poi[k-1],rate),double(k));
double tau=divu(mul(poi[M+1],double(M+2)),double(M+2)-rate);
double tail_moment=divu(mul(mul(rate,poi[M]),double(M+1)),double(M+1)-rate);

auto start=std::chrono::steady_clock::now();set_rounding();auto f=totals(s,p);double mean=add(moment(f),bm);int Tmax=cap+M;
std::vector<double>T(Tmax+2,0.),tail(Tmax+3,0.),excess(Tmax+3,0.);
for(int j=0;j<=cap;j++)if(f[j]!=0)for(int k=0;k<=M;k++)T[j+k]=add(T[j+k],mul(f[j],poi[k]));
for(int t=Tmax;t>=0;t--){tail[t]=add(T[t],tail[t+1]);excess[t]=add(excess[t+1],tail[t+1]);}
double ep=0.,em=0.;for(int j=0;j<=cap;j++){int u=cap+Z-j+1;if(u>Tmax)continue;ep=add(ep,mul(f[j],tail[u]));em=add(em,mul(f[j],add(mul(double(cap+1),tail[u]),excess[u])));}
double nbp=add(add(mul(2.,bp),tau),ep);
double nbm=mul(2.,bm);nbm=add(nbm,mul(mul(2.,add(mean,rate)),bp));nbm=add(nbm,mul(mul(2.,mean),tau));nbm=add(nbm,tail_moment);nbm=add(nbm,em);
std::fill(np.begin(),np.end(),0.);double pre[Z+1];pre[0]=T[0];for(int t=1;t<=Z;t++)pre[t]=add(pre[t-1],T[t]);
long long pairs=static_cast<long long>(s.pairs.size());
#pragma omp parallel
{
set_rounding();std::vector<double>q(cap+1,0.);
#pragma omp for schedule(dynamic,8)
for(long long i=0;i<pairs;i++){
int a=s.pairs[i].first,b=s.pairs[i].second,n=cap-a-b;std::fill(q.begin(),q.begin()+n+1,0.);const double*row=p.data()+s.row[a][b];
for(int c=0;c<=n;c++){double pc=row[c];if(pc==0)continue;if(c<=Z)q[0]=add(q[0],mul(pc,pre[Z-c]));int dlo=std::max(1,c-Z);for(int d=dlo;d<=n;d++)q[d]=add(q[d],mul(pc,T[d+Z-c]));}
for(int d=0;d<=n;d++)np[s.row[d][a]+b]=q[d];
}
}
set_rounding();p.swap(np);bp=nbp;bm=nbm;
if(joint){for(auto ab:s.pairs){int a=ab.first,b=ab.second;for(int cc=0;cc<=cap-a-b;cc++)if(p[s.row[a][b]+cc]!=0)joint<<h<<','<<a<<','<<b<<','<<cc<<','<<hx(p[s.row[a][b]+cc])<<'\n';}joint.flush();}
auto nf=totals(s,p);double mass=0.;for(double x:nf)mass=add(mass,x);double fm=add(moment(nf),bm);
std::vector<double>sl(cap+1,0.);double suffix=0.;for(int r=cap-1;r>=0;r--){suffix=add(suffix,nf[r+1]);sl[r]=add(sl[r+1],suffix);}
for(int r=0;r<=cap;r++){double upper=add(sl[r],bm);if(!std::isfinite(upper))throw std::runtime_error("nonfinite");csv<<h<<','<<r<<','<<hx(sl[r])<<','<<hx(bm)<<','<<hx(upper)<<','<<std::setprecision(17)<<std::scientific<<upper<<'\n';}
double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
log<<h<<','<<hx(mass)<<','<<hx(fm)<<','<<hx(bp)<<','<<hx(bm)<<','<<hx(ep)<<','<<hx(em)<<','<<sec<<'\n';csv.flush();log.flush();
std::cerr<<"h="<<h<<" mean<="<<std::setprecision(10)<<fm<<" unknown_m<="<<bm;if(cap>=186)std::cerr<<" H186<="<<add(sl[186],bm);std::cerr<<" seconds="<<sec<<"\n";
}
meta<<"{\n  \"model\": \"m2-depth-profile-independent-Poisson-ghost\",\n  \"cap\": "<<cap<<",\n  \"height\": "<<height<<",\n  \"poisson_cutoff\": "<<M<<",\n  \"arithmetic\": \""<<mode<<"\",\n  \"Z_root_to_leaf\": [";
for(int d=0;d<height;d++){if(d)meta<<',';meta<<Zs[d];}meta<<"],\n  \"rate_root_to_leaf\": [";
for(int d=0;d<height;d++){if(d)meta<<',';meta<<rates[d];}meta<<"],\n  \"seed_upper_root_to_leaf\": [";
for(int d=0;d<height;d++){if(d)meta<<',';meta<<"\""<<hx(seeds[d])<<"\"";}
meta<<"],\n  \"rounding_self_test\": true,\n  \"renormalized\": false,\n  \"positive_states_discarded\": false\n}\n";
return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
