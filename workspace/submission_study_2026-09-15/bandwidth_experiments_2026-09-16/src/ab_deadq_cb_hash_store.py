"""Authenticated replacement from an old leaf hash, without old row payload.

P has the same update request body as U, but its response is context17,
old-leaf-hash32, siblings32*h, new-root32. The trusted old root authenticates
the old leaf; the client hashes its own new bytes to derive the new root.
"""
import hmac,struct
from ab_deadq_authenticated_store import RowServer,VerifiedRows,need,leaf_hash,node_hash,opening_root


def tag_root(index,tag,siblings):
    need(len(tag)==32,'leaf digest size')
    for sibling in siblings:
        need(len(sibling)==32,'sibling digest size')
        tag=node_hash(sibling,tag) if index&1 else node_hash(tag,sibling);index//=2
    need(index==0,'hash update proof depth')
    return tag


class HashRowServer(RowServer):
    def exchange(self,request):
        if request[:1]!=b'P':return super().exchange(request)
        need(self.working is not None and len(request)>=21,'hash update frame/state')
        tx,step,index,length=struct.unpack('>QIII',request[1:21])
        need(tx==self.tx and step==self.step and length==len(request)-21,'hash update context/length')
        old,siblings=self.working.proof(index);digest=leaf_hash(index,old)
        self.working.update(index,request[21:]);self.step+=1
        return b'p'+request[1:17]+digest+b''.join(siblings)+self.working.root


class HashVerifiedRows(VerifiedRows):
    def row(self,index,new_value=None):
        if new_value is None:return super().row(index)
        need(not self.dead and self.work_root is not None,'active hash update')
        try:
            length=self.lengths.length(index);need(len(new_value)==length,'fixed hash update row')
            header=b'P'+struct.pack('>QII',self.tx,self.step,index)
            request=header+struct.pack('>I',length)+new_value;reply=self._rpc(request)
            need(len(reply)==81+32*self.depth and reply[:17]==b'p'+header[1:],'hash update response context/length')
            old=reply[17:49];proof=[reply[49+32*i:81+32*i] for i in range(self.depth)]
            need(hmac.compare_digest(tag_root(index,old,proof),self.work_root),'old leaf opening')
            expected=opening_root(index,new_value,proof)
            need(hmac.compare_digest(expected,reply[-32:]),'hash update new root')
            self.work_root=expected;self.step+=1
            return None # Explicitly does not return/decrypt the old payload.
        except Exception:self.dead=True;raise
