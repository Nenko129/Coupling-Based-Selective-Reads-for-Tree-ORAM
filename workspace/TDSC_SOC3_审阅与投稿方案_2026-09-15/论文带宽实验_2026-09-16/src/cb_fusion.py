"""CB logical read with public-count neutral fusion and retained green records.

Policy: a non-target bucket samples all unused slots while G<Y; afterwards it
samples unused dummy slots. The target always wins if present. The policy is a
specific instantiation of String ORAM's permitted selection, not author code.
"""
from cb_oram import Record,node,need,ui


def eligible_slots(c,h,address):
    matches=[j for j,x in h.live.items() if x.address==address]
    need(len(matches)<=1,'multiple target slots')
    if matches:return tuple(matches)
    out=tuple(j for j in range(c.n) if not(h.used>>j&1) and (h.green<c.Y or j not in h.live))
    need(bool(out),'no CB eligible slot before public threshold')
    return out


def logical_slot(tree,b,h,address):
    c=tree.c.at(b);draw=tree.P.draw(tree.ctx,b'LOGICAL_SLOT'+ui(b,8))
    choices=eligible_slots(c,h,address)
    return choices[draw%len(choices)]


def fused_logical(tree,view,address):
    c=tree.c;neutral={b for b,h in view.headers.items() if h.count==c.at(b).S}
    requested={};logical={}
    for d in view.selected:
        b=node(view.leaf,d,c.L);h=view.headers[b]
        if b in neutral:requested[b]=tree.subset(b,h)
        else:
            logical[b]=logical_slot(tree,b,h,address);requested[b]=(logical[b],)
    # Even an empty cover uses a globally authenticated header. Nonempty local
    # proofs are all checked before any chosen ciphertext is decrypted.
    plains=tree.read_slots(view,requested,'logical');rebuilt={}
    for d in view.selected:
        b=node(view.leaf,d,c.L)
        if b not in neutral:continue
        oldh=view.headers[b]
        records=[Record(x.uid,x.address,x.leaf,plains[b][j]) for j,x in oldh.live.items()]
        prepared=tree.prepare(b,oldh,sorted(records,key=lambda x:x.uid),oldh.gamma)
        h,hd,slots,local,D=prepared;rebuilt[b]=prepared;view.headers[b]=h
        by_uid={r.uid:r.payload for r in records};plains[b]={j:by_uid[x.uid] for j,x in h.live.items()}
        logical[b]=logical_slot(tree,b,h,address)
    old=tree.stash.pop(address,None);greens=[];changes={}
    for d in view.selected:
        b=node(view.leaf,d,c.L);h=view.headers[b];j=logical[b]
        if j in h.live:
            x=h.live.pop(j);record=Record(x.uid,x.address,x.leaf,plains[b][j])
            if x.address==address:
                need(old is None,'duplicate target');old=record
            else:
                need(h.green<c.at(b).Y,'green quota exhausted');h.green+=1;greens.append(record)
        h.count+=1;h.used|=1<<j
        final=tree.prepare(b,h,None)
        if b in rebuilt:
            _,_,slots,local,D=rebuilt[b];final=(final[0],final[1],slots,local,D)
        changes[b]=final
    # Green payloads become usable only after the final write acknowledges.
    tree.write(view,changes,'logical')
    for r in greens:
        need(r.address not in tree.stash,'duplicate green address');tree.stash[r.address]=r
    tree.cb_metrics['green_promotions']+=len(greens)
    tree.cb_metrics['neutral_rebuilds']+=len(neutral)
    return old
