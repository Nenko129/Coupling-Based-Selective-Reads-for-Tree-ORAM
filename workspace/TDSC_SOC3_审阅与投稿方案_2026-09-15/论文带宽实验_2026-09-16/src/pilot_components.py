"""Isolated static-IR/AB pilots; not the native paper systems."""
from common import *
from run_core import geometry
import subprocess,time

def main():
    specs=[]
    for family in ('IR_static','AB_static'):
        profile=[4,3,3] if family=='IR_static' else [7,6,6];N=1024;L=geometry(N,profile[1])
        for variant in ('uniform','depth_profile'):
            for kind in (('deferred','sde') if family=='IR_static' else ('ring','r0')):
                spec=dict(id=f'pilot_{family}_{variant}_{kind}_N1024_B64',kind=kind,N=N,B=64,profile=profile,
                          map_B=512,terminal_bytes=32768,compact=True,fusion=True,R=256,warmup=512,requests=1024,
                          trace_seed=901,oram_seed=1901,workload='uniform',experiment_class='pilot_components')
                if family=='IR_static':
                    native=[4]*10+[2]*7+[3]*3+[4]*5
                    spec['Z_by_depth']=[native[min(24,(25*d)//(L+1))] for d in range(L+1)] if variant=='depth_profile' else [4]*(L+1)
                    spec['profile_scaling']='published 25-level full-IR Z profile sampled at floor(25*d/(L+1)); no cached levels in this pilot'
                else:spec['S_by_depth']=([6]*(L-2)+[4]*3) if variant=='depth_profile' else [6]*(L+1)
                specs.append(spec)
    save(PACKAGE/'component_pilot_plan.json',dict(specs=specs,scope='pilot only; no top cache, native IR-Stash/DWB, native CB/DeadQ'))
    for spec in specs:
        path=PACKAGE/'specs'/f"{spec['id']}.json";save(path,spec)
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).parent/'run_heterogeneous.py'),'--spec',str(path)],
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if p.returncode:raise SystemExit(p.returncode)
    print('component pilots finished',flush=True)
if __name__=='__main__':main()
