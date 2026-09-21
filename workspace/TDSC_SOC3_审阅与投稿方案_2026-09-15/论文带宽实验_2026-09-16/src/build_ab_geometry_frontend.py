"""Expose public tree height without changing recursive map algorithms."""
from common import *
import composition_runtime,inspect,difflib


def main():
    original=inspect.getsource(composition_runtime.frontends.FreecursiveFront.__init__)
    needle='profile=(4,3,4)):';assert original.count(needle)==1
    modified=original.replace(needle,'profile=(4,3,4),L=None):')
    needle='self.L=max(1,math.ceil(math.log2(2*total/3)))';assert modified.count(needle)==1
    modified=modified.replace(needle,'self.L=max(1,math.ceil(math.log2(2*total/3))) if L is None else L')
    text='''"""Same unified map frontend with an explicit public tree-height parameter.

Generated from the frozen Freecursive constructor; no lookup or map algorithm
is replaced. The real Backend binding is supplied by ab_cb_runtime.install.
"""
from frontends import *
from ir_dwb_controller import StepwiseFront


class GeometryFront(FreecursiveFront):
'''+modified+'''

class GeometryStepwiseFront(StepwiseFront):
    def __init__(self,*args,**kwargs):
        kwargs['compressed']=False
        GeometryFront.__init__(self,*args,**kwargs)
        self.pending_writeback=None
'''
    path=Path(__file__).parent/'ab_geometry_frontend.py';path.write_text(text,encoding='utf-8')
    (PACKAGE/'ab_frontend_geometry.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),modified.splitlines(True),
        fromfile='frozen FreecursiveFront.__init__',tofile='GeometryFront.__init__')),encoding='utf-8')
    save(PACKAGE/'results/ab_frontend_geometry_build.json',dict(source_sha256=sha(COMPOSITION/'frontends.py'),
        target_sha256=sha(path),generator_sha256=sha(__file__),changes=['optional explicit public height','preserve the original height formula when omitted']))
    print(json.dumps(dict(status='generated',changes=2)))


if __name__=='__main__':main()
