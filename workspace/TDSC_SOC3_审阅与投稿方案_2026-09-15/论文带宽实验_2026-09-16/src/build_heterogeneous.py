"""Produce an auditable fork; never edit the frozen implementation in place."""
from common import *
import difflib

def main():
    original=(FROZEN/'optimized_oram.py').read_text(encoding='utf-8');s=original
    def change(old,new,count=1):
        nonlocal s
        assert s.count(old)==count,(old[:100],s.count(old),count)
        s=s.replace(old,new)
    change('compact:bool=True; fused:bool=True','compact:bool=True; fused:bool=True; Z_by_depth:tuple=(); S_by_depth:tuple=()')
    old="        if self.n>64 or self.R<0 or (self.ring and self.S<1):raise ValueError('slots/stash/dummies')"
    change(old,old+'''
        for profile in (self.Z_by_depth,self.S_by_depth):
            if profile and len(profile)!=self.L+1:raise ValueError('depth profile length')
        for d in range(self.L+1):
            z=self.Z_by_depth[d] if self.Z_by_depth else self.Z
            ss=self.S_by_depth[d] if self.S_by_depth else self.S
            if not 1<=z<=8 or (self.ring and ss<1) or z+(ss if self.ring else 0)>64:raise ValueError('depth profile capacity')
    def at(self,b):
        return BucketConfig(self,depth(b)) if self.Z_by_depth or self.S_by_depth else self
''')
    old="        return encode(b'Selective-ORAM-optimization-v3',self.kind.encode(),*[ui(v,8) for v in (self.tree,self.L,self.N,self.B,self.Z,self.A,self.S,self.R,int(self.compact),int(self.fused))])"
    change(old,old.replace('return encode','base=encode')+'''
        if self.Z_by_depth or self.S_by_depth:
            return encode(b'SOC3-DEPTH-PROFILES-EVAL-v1',base,bytes(self.Z_by_depth),bytes(self.S_by_depth))
        return base

class BucketConfig:
    """Public per-bucket layout. All crypto uses the full profile context."""
    def __init__(self,parent,d):self.parent=parent;self.d=d
    def __getattr__(self,name):return getattr(self.parent,name)
    @property
    def Z(self):return self.parent.Z_by_depth[self.d] if self.parent.Z_by_depth else self.parent.Z
    @property
    def S(self):return self.parent.S_by_depth[self.d] if self.parent.S_by_depth else self.parent.S
    @property
    def n(self):return self.Z+self.S if self.ring else self.Z
    @property
    def secret(self):return ((8+(30 if self.compact else 64)*self.Z+31)//32)*32
    @property
    def H(self):return PUBLIC+NONCE+self.secret
''')
    change("            b=q.uint();need(1<=b<(1<<(c.L+1)),'init bucket')","            b=q.uint();need(1<=b<(1<<(c.L+1)),'init bucket');bc=c.at(b)")
    change('hd=q.take(c.H);slots=[q.take(c.W) for _ in range(c.n)]','hd=q.take(bc.H);slots=[q.take(c.W) for _ in range(bc.n)]')
    change('local={p:q.take(TAG) for p in local_indices(c.n)} if c.ring else {}','local={p:q.take(TAG) for p in local_indices(bc.n)} if c.ring else {}')
    change("                    inds=from_bitmap(q.uint(),c.n);s=self.buckets[tree,path[d]]","                    bc=c.at(path[d]);inds=from_bitmap(q.uint(),bc.n);s=self.buckets[tree,path[d]]")
    change('for p in witnesses(c.n,inds))','for p in witnesses(bc.n,inds))')
    change('b=path[d];old=self.buckets[tree,b];hd=q.take(c.H)','b=path[d];bc=c.at(b);old=self.buckets[tree,b];hd=q.take(bc.H)')
    change('slots=[q.take(c.W) for _ in range(c.n)] if d in full else old.slots','slots=[q.take(c.W) for _ in range(bc.n)] if d in full else old.slots')
    change('local=({p:q.take(TAG) for p in local_indices(c.n)} if c.ring else {}) if d in full else old.local','local=({p:q.take(TAG) for p in local_indices(bc.n)} if c.ring else {}) if d in full else old.local')
    change('        c=self.c\n        if records is None:','        c=self.c.at(b)\n        if records is None:')
    change('        def visit(b:int,d:int):\n            left=','        def visit(b:int,d:int):\n            bc=c.at(b)\n            left=')
    change("body=ui(b,8)+hd+b''.join(slots)+(b''.join(local[p] for p in local_indices(c.n)) if c.ring else b'')+bt+gt","body=ui(b,8)+hd+b''.join(slots)+(b''.join(local[p] for p in local_indices(bc.n)) if c.ring else b'')+bt+gt")
    change("comp={'headers_upload':c.H,'data_upload':c.n*c.W,'authentication_upload':(len(local)+2)*TAG}","comp={'headers_upload':bc.H,'data_upload':bc.n*c.W,'authentication_upload':(len(local)+2)*TAG}")
    change("comp={'headers_download':k*c.H,'authentication_download':(c.L+skip+(k if c.ring else 0))*TAG}","comp={'headers_download':sum(c.at(node(leaf,d,c.L)).H for d in ds),'authentication_download':(c.L+skip+(k if c.ring else 0))*TAG}")
    change("if not c.ring:comp['data_download']=k*c.n*c.W","if not c.ring:comp['data_download']=sum(c.at(node(leaf,d,c.L)).n*c.W for d in ds)")
    change('b=node(leaf,d,c.L);wh[b]=q.take(c.H)','b=node(leaf,d,c.L);bc=c.at(b);wh[b]=q.take(bc.H)')
    change('else:cts[b]=[q.take(c.W) for _ in range(c.n)];D[b]=self.droot(b,cts[b])','else:cts[b]=[q.take(c.W) for _ in range(bc.n)];D[b]=self.droot(b,cts[b])')
    change('Header.decode(c,pub,self.P.decrypt(self.ctx,self.oid(b),pub,hd[PUBLIC:]))','Header.decode(c.at(b),pub,self.P.decrypt(self.ctx,self.oid(b),pub,hd[PUBLIC:]))')
    change('proofcount=sum(len(witnesses(c.n,tuple(sorted(v)))) for v in selection.values())','proofcount=sum(len(witnesses(c.at(b).n,tuple(sorted(v)))) for b,v in selection.items())')
    change('b=node(view.leaf,d,c.L);inds=tuple(sorted(selection[b]));cts={j:q.take(c.W) for j in inds}','b=node(view.leaf,d,c.L);bc=c.at(b);inds=tuple(sorted(selection[b]));cts={j:q.take(c.W) for j in inds}')
    change('proof={p:q.take(TAG) for p in witnesses(c.n,inds)}','proof={p:q.take(TAG) for p in witnesses(bc.n,inds)}')
    change('computed=local_open_root(c,self.P,b,cts,proof)','computed=local_open_root(bc,self.P,b,cts,proof)')
    change('for p in local_indices(c.n)) if slots is not None and c.ring', 'for p in local_indices(c.at(b).n)) if slots is not None and c.ring')
    change("{'headers_upload':len(ds)*c.H,'data_upload':dataup,'authentication_upload':authup}","{'headers_upload':sum(c.at(b).H for b in changes),'data_upload':dataup,'authentication_upload':authup}")
    change('c=self.c;real=set(h.live);','c=self.c.at(b);real=set(h.live);')
    change('from fused_logical import fused_logical','from heterogeneous_fusion import fused_logical')
    change(')][:c.Z]',')][:c.at(b).Z]')
    change('if view.headers[b].count==c.S:self.neutral(view,b)','if view.headers[b].count==c.at(b).S:self.neutral(view,b)')
    change("dummy=[j for j in range(c.n) if not(h.used>>j&1) and j not in h.live]","dummy=[j for j in range(c.at(b).n) if not(h.used>>j&1) and j not in h.live]")
    target=Path(__file__).parent/'heterogeneous_oram.py';target.write_text(s,encoding='utf-8')
    fusion=(FROZEN/'fused_logical.py').read_text(encoding='utf-8')
    fusion=fusion.replace('from optimized_oram import','from heterogeneous_oram import').replace('c=tree.c;draw=','c=tree.c.at(b);draw=').replace('if h.count==c.S','if h.count==c.at(b).S')
    (target.parent/'heterogeneous_fusion.py').write_text(fusion,encoding='utf-8')
    diff=''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='frozen/optimized_oram.py',tofile='evaluation/heterogeneous_oram.py'))
    (PACKAGE/'heterogeneous_engine.diff').write_text(diff,encoding='utf-8')
    save(PACKAGE/'results/heterogeneous_fork_identity.json',dict(source_sha256=sha(FROZEN/'optimized_oram.py'),output_sha256=sha(target),
         generator_sha256=sha(__file__),diff_sha256=sha(PACKAGE/'heterogeneous_engine.diff'),scope='static depth Z/S only; no top cache, IR-Stash/DWB, CB or DeadQ'))
    print('generated static heterogeneous fork')
if __name__=='__main__':main()
