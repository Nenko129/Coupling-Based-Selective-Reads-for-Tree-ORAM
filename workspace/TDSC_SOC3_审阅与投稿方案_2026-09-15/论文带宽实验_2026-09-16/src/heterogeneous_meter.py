"""Independent public-layout invoice for the static heterogeneous serializer."""
from common import *
from collections import Counter
import meter
from optimized_oram import INIT,OPEN_FULL,OPEN_HEAD,READ_SLOTS,WRITE,FRAME,TAG,node,local_indices,witnesses
from optimized_cost import COMPONENTS

def invoice_event(c,e):
    v=Counter({k:0 for k in COMPONENTS});op=e['opcode']
    def layout(d):return c.at(1<<d) if hasattr(c,'at') else c
    if op==INIT:
        bc=layout(e['bucket'].bit_length()-1);root=c.rootless and e['bucket']==1
        v['headers_upload']=0 if root else bc.H;v['data_upload']=0 if root else bc.n*c.W
        v['authentication_upload']=(2+(len(local_indices(bc.n)) if c.ring and not root else 0))*TAG
        v['framing_and_control']=2*FRAME+8
    else:
        ds=e['depths'];k=len(ds)
        if op in (OPEN_FULL,OPEN_HEAD):
            v['headers_download']=sum(layout(d).H for d in ds)
            v['authentication_download']=(c.L+len(c.levels)-k+(k if op==OPEN_HEAD else 0))*TAG
            v['data_download']=sum(layout(d).n*c.W for d in ds) if op==OPEN_FULL else 0
            v['framing_and_control']=2*FRAME+16
        elif op==READ_SLOTS:
            v['data_download']=sum(len(s) for s in e['slots'])*c.W
            v['authentication_download']=sum(len(witnesses(layout(d).n,tuple(s))) for d,s in zip(ds,e['slots']))*TAG
            v['framing_and_control']=2*FRAME+16+8*k
        elif op==WRITE:
            full=e['full_depths'];v['headers_upload']=sum(layout(d).H for d in ds)
            v['data_upload']=sum(layout(d).n*c.W for d in full)
            v['authentication_upload']=(k+max(ds)+1+sum(len(local_indices(layout(d).n)) for d in full if c.ring))*TAG
            v['framing_and_control']=2*FRAME+24
        else:raise AssertionError(op)
    return dict(v)

def install(engine):
    # Each experiment executes in a dedicated process. No frozen file is edited.
    meter.invoice_event=invoice_event;engine.Transport=meter.StreamingTransport
    return meter.StreamingTransport
