"""Read-only reuse of the audited engine, with SOC3 extras disabled.

The full_probe arm retains the selective placement constraint but reads every
level. It is an attribution control, NOT a native-paper reproduction.
"""
from pathlib import Path
import sys, json, hashlib, dataclasses
HOME = Path(__file__).resolve().parents[1]
EVAL = HOME.parent / '论文带宽实验_2026-09-16'
sys.path.insert(0, str(EVAL / 'src'))
import common
import heterogeneous_oram as h
import cached_transport as cache
from cached_cost import expected_tree
from run_core import geometry

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)

@dataclasses.dataclass(frozen=True)
class FullProbeConfig(h.Config):
    @property
    def selective(self): return False
    @property
    def constrained(self): return True

def configuration(s):
    assert s['family'] in ('IR','AB') and s['arm'] in ('base','full_probe','selective')
    assert s['compact'] is False and s['fusion'] is False and s['root_retained'] is True
    Z,A,S=s['profile'];L=geometry(s['N'],A)
    kind=('sde' if s['arm']!='base' else 'deferred') if s['family']=='IR' else ('gc_ring' if s['arm']!='base' else 'ring')
    cls=FullProbeConfig if s['arm']=='full_probe' else h.Config
    c=cls(kind=kind,L=L,N=s['N'],B=s['B'],Z=Z,A=A,S=S,R=s['R'],compact=False,fused=False,
          Z_by_depth=tuple(s.get('Z_by_depth',())),S_by_depth=tuple(s.get('S_by_depth',())))
    assert not c.rootless and not c.fused and not c.compact and (0 in c.levels)
    assert c.N*4<=s['terminal_bytes'], 'this component experiment fixes a trusted flat position map'
    return c

def identity():
    paths=[HOME/'src'/n for n in ('minimal_runtime.py','run_minimal.py','run_frontend_minimal.py','check_minimal_contract.py','prepare_matrix.py','dispatch.py')]
    paths += [EVAL/'src'/n for n in ('common.py','heterogeneous_oram.py','heterogeneous_fusion.py','cached_transport.py','cached_cost.py','run_core.py','workloads.py','meter.py')]
    paths += list(common.FROZEN.glob('*.py'))
    return {str(p.relative_to(HOME.parent.parent)):sha(p) for p in sorted(set(paths))}

def install(s): cache.install({0:s['cached_levels']})
