"""Isolate a public initialization cadence; do not mutate earlier AB evidence."""
from common import *
import difflib


def main():
    source=Path(__file__).parent/'ab_geometry_frontend.py';original=source.read_text();text=original
    text=text.replace('class GeometryFront(', 'class PacedGeometryFront(').replace('class GeometryStepwiseFront(', 'class PacedGeometryStepwiseFront(')
    text=text.replace('GeometryFront.__init__(self,*args,**kwargs)','PacedGeometryFront.__init__(self,*args,**kwargs)')
    needle="                self.backend.tick(None,self.padding.fresh('init'),admit=(a,self.initial_leaf(level,i),payload))\n"
    assert text.count(needle)==1
    text=text.replace(needle,needle+"                for _ in range(A-1):self.backend.tick(None,self.padding.fresh('init-cadence'))\n")
    text=text.replace('The real Backend binding is supplied by ab_cb_runtime.install.',
        'One record is admitted every A public slots during initialization.\nThe remaining A-1 slots are ordinary CB dummy Transfers, billed to setup.\nBackend is bound explicitly by the new driver; earlier drivers are unchanged.')
    target=source.with_name('ab_paced_frontend.py');target.write_text(text,encoding='utf-8')
    diff=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=source.name,tofile=target.name))
    source.with_name('ab_paced_frontend.diff').write_text(diff,encoding='utf-8')
    save(PACKAGE/'results/ab_paced_frontend_build.json',dict(status='generated',base_sha256=sha(source),output_sha256=sha(target),
        generator_sha256=sha(__file__),public_cadence='one admission and A-1 ordinary dummy slots per initial record; no stash-dependent loop'))


if __name__=='__main__':main()
