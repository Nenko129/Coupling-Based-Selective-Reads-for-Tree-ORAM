"""Public-count-triggered fusion of neutral reshuffles and a logical Ring read."""
from optimized_oram import Record, node, need, ui

def logical_slot(tree,b,h,address):
    c=tree.c;draw=tree.P.draw(tree.ctx,b'LOGICAL_SLOT'+ui(b,8))
    matches=[j for j,x in h.live.items() if x.address==address]
    need(len(matches)<=1,'multiple target slots')
    dummy=[j for j in range(c.n) if not(h.used>>j&1) and j not in h.live]
    need(bool(dummy),'no fresh dummy')
    return matches[0] if matches else dummy[draw%len(dummy)]

def fused_logical(tree,view,address):
    c=tree.c
    # open_path has authenticated every header before any slot choice.
    neutral={b for b,h in view.headers.items() if h.count==c.S}
    requested={};logical={}
    for d in view.selected:
        b=node(view.leaf,d,c.L);h=view.headers[b]
        if b in neutral:requested[b]=tree.subset(b,h)
        else:
            logical[b]=logical_slot(tree,b,h,address);requested[b]=(logical[b],)
    # The original read_slots verifier checks ALL ciphertexts and local proofs
    # before decrypting any payload, including every padding/cover slot.
    plains=tree.read_slots(view,requested,'logical')
    rebuilt={}
    for d in view.selected:
        b=node(view.leaf,d,c.L)
        if b not in neutral:continue
        oldh=view.headers[b]
        records=[Record(x.uid,x.address,x.leaf,plains[b][j]) for j,x in oldh.live.items()]
        prepared=tree.prepare(b,oldh,sorted(records,key=lambda x:x.uid),oldh.gamma)
        h,hd,slots,local,D=prepared;rebuilt[b]=prepared
        # This is a local intermediate state, never installed as a server root.
        view.headers[b]=h
        by_uid={r.uid:r.payload for r in records}
        plains[b]={j:by_uid[x.uid] for j,x in h.live.items()}
        logical[b]=logical_slot(tree,b,h,address)
    old=tree.stash.pop(address,None);changes={}
    for d in view.selected:
        b=node(view.leaf,d,c.L);h=view.headers[b]
        matches=[j for j,x in h.live.items() if x.address==address]
        if matches:
            need(old is None,'duplicate current');j=matches[0];x=h.live.pop(j)
            old=Record(x.uid,x.address,x.leaf,plains[b][j])
        j=logical[b];h.count+=1;h.used|=1<<j
        # Retain both header-version increments of neutral followed by logical;
        # intermediate header encryption also consumed its unique nonce.
        final=tree.prepare(b,h,None)
        if b in rebuilt:
            _,_,slots,local,D=rebuilt[b]
            final=(final[0],final[1],slots,local,D)
        changes[b]=final
    tree.write(view,changes,'logical')
    return old
