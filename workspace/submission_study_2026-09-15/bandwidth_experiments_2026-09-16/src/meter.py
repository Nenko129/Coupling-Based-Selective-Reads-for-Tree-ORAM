"""Bounded-history transport, preserving the original bytes and response checks."""
from common import *
from collections import Counter,defaultdict
import hashlib
from optimized_oram import frame,parse_frame,need
from optimized_cost import invoice_event,COMPONENTS

class StreamingTransport:
    def __init__(self,server):
        self.server=server;self.seq=0;self.mutator=None;self.phase='physical_setup'
        self.capture_limit=0;self.events=[];self.total=Counter();self.reset_meter()

    def reset_meter(self):
        self.components=Counter();self.stage=defaultdict(Counter);self.tree=defaultdict(Counter)
        self.opcodes=Counter();self.rpc_count=0;self.up=0;self.down=0
        self.transcript=hashlib.sha256();self.first_seq=self.seq

    def rpc(self,c,op,body,stage,meta,components):
        seq=self.seq;self.seq+=1;request=frame(op,c.tree,seq,body)
        response=self.server.handle(request)
        if self.mutator is not None:response=self.mutator(c,op,seq,stage,meta,request,response)
        e=dict(sequence=seq,tree=c.tree,stage=stage,opcode=op,request_bytes=len(request),response_bytes=len(response),
               request_sha256=hashlib.sha256(request).hexdigest(),response_sha256=hashlib.sha256(response).hexdigest(),**meta)
        parts=dict(components);parts['framing_and_control']=len(request)+len(response)-sum(parts.values())
        predicted=invoice_event(c,e)
        need(sum(predicted.values())==len(request)+len(response),'independent frame length invoice')
        need(all(predicted[k]==parts.get(k,0) for k in COMPONENTS),'independent component invoice')
        e['components']=parts
        if len(self.events)<self.capture_limit:self.events.append(e)
        for key in ('request_sha256','response_sha256'):self.transcript.update(bytes.fromhex(e[key]))
        self.rpc_count+=1;self.up+=len(request);self.down+=len(response);self.opcodes[str(op)]+=1
        self.total.update(parts);self.components.update(predicted);self.stage[stage].update(predicted);self.tree[str(c.tree)].update(predicted)
        rop,rt,rs,rf,result=parse_frame(response)
        need((rop,rt,rs,rf)==(op,c.tree,seq,1),'response routing/replay')
        return result

    def snapshot(self):
        return dict(rpc=self.rpc_count,request_bytes=self.up,response_bytes=self.down,total_bytes=self.up+self.down,
                    components=dict(self.components),by_stage={k:dict(v) for k,v in self.stage.items()},
                    by_tree={k:dict(v) for k,v in self.tree.items()},opcode_counts=dict(self.opcodes),
                    transcript_sha256=self.transcript.hexdigest(),first_sequence=self.first_seq,next_sequence=self.seq,
                    independently_invoiced_rpcs=self.rpc_count,retained_event_count=len(self.events))

def server_storage(server):
    """Real serialized object content bytes, excluding Python allocator overhead."""
    comp=Counter()
    for item in server.buckets.values():
        comp['headers']+=len(item.header);comp['ciphertext_slots']+=sum(map(len,item.slots))
        comp['local_authentication']+=sum(map(len,item.local.values()));comp['bucket_tags']+=len(item.bucket_tag)
    comp['global_tags']=sum(map(len,server.global_tags.values()))
    return dict(components=dict(comp),total_bytes=sum(comp.values()),physical_bucket_records=len(server.buckets),
                scope='serialized object content; excludes Python/container indexing/allocator overhead')
