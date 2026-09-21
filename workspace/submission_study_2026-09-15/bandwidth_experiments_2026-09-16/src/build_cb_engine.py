"""Generate an isolated authenticated Compact-Bucket engine, with a review diff.

This does not change any source used by the running formal experiments.
S is the logical read threshold; physical dummy reserve is S-Y.
"""
from common import *
import difflib


def main():
    src=Path(__file__).parent/'heterogeneous_oram.py';old=src.read_text(encoding='utf-8');new=old
    edits=[]
    def edit(label,a,b,count=1):
        nonlocal new
        assert new.count(a)==count,(label,new.count(a),count)
        new=new.replace(a,b);edits.append(label)
    edit('parameter_fields','Z_by_depth:tuple=(); S_by_depth:tuple=()',
         'Z_by_depth:tuple=(); S_by_depth:tuple=(); Y:int=0; Y_by_depth:tuple=()')
    edit('profile_dimensions','for profile in (self.Z_by_depth,self.S_by_depth):',
         'for profile in (self.Z_by_depth,self.S_by_depth,self.Y_by_depth):')
    edit('configuration_rules',"        if self.kind not in KINDS", "        if not self.ring or not self.fused:raise ValueError('CB engine requires a fused Ring-family protocol')\n        if not 0<=self.Y<=min(self.Z,self.S):raise ValueError('CB overlap')\n        if self.kind not in KINDS")
    edit('per_depth_constraints',"            if not 1<=z<=8 or (self.ring and ss<1) or z+(ss if self.ring else 0)>64:raise ValueError('depth profile capacity')",
         "            y=self.Y_by_depth[d] if self.Y_by_depth else self.Y\n            if not 1<=z<=8 or ss<1 or not 0<=y<=min(z,ss) or z+ss-y>64:raise ValueError('depth profile capacity/overlap')")
    edit('per_depth_dispatch','if self.Z_by_depth or self.S_by_depth else self',
         'if self.Z_by_depth or self.S_by_depth or self.Y_by_depth else self')
    edit('physical_bucket_length','return self.Z+self.S if self.ring else self.Z',
         'return self.Z+self.S-self.Y if self.ring else self.Z',count=2)
    edit('encrypted_counter_space','((8+(30 if self.compact else 64)*self.Z+31)//32)*32',
         '((8+(8 if self.Y else 0)+(30 if self.compact else 64)*self.Z+31)//32)*32',count=2)
    edit('bind_crypto_context',"        if self.Z_by_depth or self.S_by_depth:\n            return encode(b'SOC3-DEPTH-PROFILES-EVAL-v1',base,bytes(self.Z_by_depth),bytes(self.S_by_depth))\n        return base",
         "        return encode(b'SOC3-CB-EXPERIMENT-v1',base,bytes(self.Z_by_depth),bytes(self.S_by_depth),ui(self.Y,8),bytes(self.Y_by_depth))")
    edit('bucket_overlap_property',"    def n(self):return self.Z+self.S-self.Y if self.ring else self.Z\n    @property\n    def secret(self)",
         "    def Y(self):return self.parent.Y_by_depth[self.d] if self.parent.Y_by_depth else self.parent.Y\n    @property\n    def n(self):return self.Z+self.S-self.Y if self.ring else self.Z\n    @property\n    def secret(self)")
    edit('header_counter',"    def public(self)->bytes:","    green:int=0 # non-target real blocks consumed in this bucket epoch, encrypted\n    def public(self)->bytes:")
    edit('encode_counter',"        raw=ui((1<<len(ds))-1,8)","        need(0<=self.green<=c.Y,'green counter bounds')\n        raw=(ui(self.green,8) if c.Y else b'')+ui((1<<len(ds))-1,8)")
    edit('decode_counter',"        r=Cursor(plain);livebits=r.uint(8);", "        r=Cursor(plain);h.green=r.uint(8) if c.Y else 0\n        need(0<=h.green<=min(c.Y,h.count),'green counter bounds')\n        livebits=r.uint(8);")
    edit('counter_retained_on_header_update',"h=Header(old.gamma,old.w,old.v+1,old.count,old.used,dict(old.live));", "h=Header(old.gamma,old.w,old.v+1,old.count,old.used,dict(old.live),old.green);")
    edit('work_metrics',"        self.observer=None", "        self.cb_metrics=Counter()\n        self.observer=None")
    edit('empty_slot_opening',"        c=self.c;ds=tuple(sorted(depth(b) for b in selection));count=sum(map(len,selection.values()))",
         "        empty={b:{} for b,v in selection.items() if not v}\n        need(all(not view.headers[b].live for b in empty),'empty opening with live payload')\n        selection={b:v for b,v in selection.items() if v}\n        if not selection:return empty\n        c=self.c;ds=tuple(sorted(depth(b) for b in selection));count=sum(map(len,selection.values()))")
    edit('merge_empty_openings',"        return {b:{j:self.P.decrypt(self.ctx,self.oid(b,j),ui(view.headers[b].w),ct) for j,ct in cts.items()} for b,cts in allcts.items()}",
         "        return empty | {b:{j:self.P.decrypt(self.ctx,self.oid(b,j),ui(view.headers[b].w),ct) for j,ct in cts.items()} for b,cts in allcts.items()}")
    edit('public_variable_cover',"need(real<=set(unused),'remaining real not unread');k=c.Z-len(real)",
         "need(real<=set(unused),'remaining real not unread');cover=min(c.Z,len(unused));k=cover-len(real)\n        need(0<=k<=len(dummy),'CB cover capacity')\n        self.cb_metrics['maintenance_cover_slots']+=cover\n        self.cb_metrics['zero_cover_buckets']+=int(cover==0)")
    edit('bind_cb_fusion','from heterogeneous_fusion import fused_logical','from cb_fusion import fused_logical')
    target=Path(__file__).parent/'cb_oram.py';target.write_text(new,encoding='utf-8')
    (PACKAGE/'cb_engine.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=src.name,tofile=target.name)),encoding='utf-8')
    transfer=Path(__file__).parent/'ir_transfer.py';told=transfer.read_text(encoding='utf-8')
    assert told.count('from heterogeneous_oram import (')==1
    tnew=told.replace('from heterogeneous_oram import (','from cb_oram import (')
    tp=Path(__file__).parent/'cb_transfer.py';tp.write_text(tnew,encoding='utf-8')
    save(PACKAGE/'results/cb_engine_build.json',dict(source_sha256=sha(src),target_sha256=sha(target),transfer_source_sha256=sha(transfer),
        transfer_target_sha256=sha(tp),generator_sha256=sha(__file__),edits=edits,security_closed=False))
    print(json.dumps(dict(edits=len(edits),target=str(target))))


if __name__=='__main__':main()
