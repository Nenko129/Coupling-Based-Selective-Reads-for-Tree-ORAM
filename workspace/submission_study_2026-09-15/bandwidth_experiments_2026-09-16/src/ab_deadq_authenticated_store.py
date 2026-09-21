"""Serialized Merkle row store for the DeadQ prototype (not an ORAM).

One serial client retains a root; the server keeps committed rows and an
uncommitted working tree. Every read/update opening is verified by the client.
No socket, durability, rollback recovery, or malicious-server availability is
claimed. The wire recorder belongs to the test transport, not trusted state.
"""
import hashlib
import hmac
import struct


class AuthenticationFailure(Exception):
    pass


def need(ok, why):
    if not ok:
        raise AuthenticationFailure(why)


def leaf_hash(index, value):
    return hashlib.sha256(b'DeadQ-row-v1\x00'+struct.pack('>II', index, len(value))+value).digest()


def node_hash(left, right):
    return hashlib.sha256(b'DeadQ-node-v1\x00'+left+right).digest()


def opening_root(index, value, siblings):
    tag=leaf_hash(index, value)
    for sibling in siblings:
        need(len(sibling)==32, 'proof element length')
        tag=node_hash(sibling, tag) if index&1 else node_hash(tag, sibling)
        index//=2
    need(index==0, 'proof too short')
    return tag


class MerkleRows:
    """Server-side object. Not reachable through the client API."""
    def __init__(self, rows):
        self.count=len(rows)
        self.size=1 << (self.count-1).bit_length()
        self.rows=list(rows)+[b'']*(self.size-self.count)
        self.tags=[b'']*(2*self.size)
        for i, row in enumerate(self.rows):self.tags[self.size+i]=leaf_hash(i, row)
        for i in range(self.size-1,0,-1):self.tags[i]=node_hash(self.tags[2*i],self.tags[2*i+1])

    @property
    def root(self):return self.tags[1]

    def proof(self,index):
        need(0<=index<self.count, 'row index')
        siblings=[];i=self.size+index
        while i>1:siblings.append(self.tags[i^1]);i//=2
        return self.rows[index],siblings

    def update(self,index,value):
        need(0<=index<self.count, 'row index')
        self.rows[index]=value;i=self.size+index;self.tags[i]=leaf_hash(index,value)
        while i>1:i//=2;self.tags[i]=node_hash(self.tags[2*i],self.tags[2*i+1])


class RowServer:
    def __init__(self,rows):
        self.committed=MerkleRows(rows);self.working=None;self.tx=0;self.step=0

    def exchange(self,request):
        op=request[:1]
        if op==b'B':
            need(len(request)==41 and self.working is None, 'begin framing/state')
            tx=struct.unpack('>Q',request[1:9])[0]
            need(tx>self.tx and request[9:]==self.committed.root, 'begin anchor')
            self.tx=tx;self.step=0
            self.working=MerkleRows(self.committed.rows[:self.committed.count])
            return b'b'+request[1:]
        need(self.working is not None and len(request)>=13, 'active transaction')
        tx,step=struct.unpack('>QI',request[1:13])
        need(tx==self.tx and step==self.step, 'transaction/sequence')
        if op==b'C':
            need(len(request)==45 and request[13:]==self.working.root, 'commit anchor')
            self.committed=self.working;self.working=None
            return b'c'+request[1:]
        need(op in (b'G',b'U') and len(request)>=17, 'row opcode/framing')
        index=struct.unpack('>I',request[13:17])[0]
        value,siblings=self.working.proof(index)
        reply=op.lower()+request[1:17]+struct.pack('>I',len(value))+value+b''.join(siblings)
        if op==b'G':need(len(request)==17, 'get framing')
        else:
            need(len(request)>=21, 'update framing')
            length=struct.unpack('>I',request[17:21])[0]
            need(length==len(request)-21, 'update length')
            self.working.update(index,request[21:]);reply+=self.working.root
        self.step+=1
        return reply


class WireRecorder:
    """Untrusted transport/test instrumentation, deliberately outside client."""
    def __init__(self,server):
        self.server=server;self.frames=[];self.reply_filter=None

    def exchange(self,request):
        response=self.server.exchange(request)
        if self.reply_filter is not None:response=self.reply_filter(request,response)
        self.frames.append((request,response))
        return response


class VerifiedRows:
    """Root-anchored serial transactions with no persistent directory cache."""
    def __init__(self,exchange,root,lengths):
        self.exchange=exchange;self.root=root;self.lengths=lengths
        self.depth=(lengths.count-1).bit_length()
        self.tx=0;self.step=0;self.work_root=None;self.dead=False

    def _rpc(self,request):
        need(not self.dead, 'permanent fail-stop')
        try:return self.exchange(request)
        except Exception:
            self.dead=True
            raise

    def begin(self):
        need(not self.dead and self.work_root is None,'serial client state')
        self.tx+=1;self.step=0
        request=b'B'+struct.pack('>Q',self.tx)+self.root
        try:
            need(hmac.compare_digest(self._rpc(request),b'b'+request[1:]),'begin response')
            self.work_root=self.root
        except Exception:self.dead=True;raise

    def row(self,index,new_value=None):
        need(not self.dead and self.work_root is not None,'active client transaction')
        try:
            length=self.lengths.length(index)
            op=b'G' if new_value is None else b'U'
            header=op+struct.pack('>QII',self.tx,self.step,index)
            request=header
            if new_value is not None:
                need(len(new_value)==length,'fixed row size')
                request+=struct.pack('>I',length)+new_value
            reply=self._rpc(request)
            tail=32 if new_value is not None else 0
            need(len(reply)==21+length+32*self.depth+tail,'exact opening length')
            need(reply[:17]==op.lower()+header[1:],'opening context')
            need(struct.unpack('>I',reply[17:21])[0]==length,'opening row size')
            old=reply[21:21+length];start=21+length
            proof=[reply[start+32*i:start+32*(i+1)] for i in range(self.depth)]
            need(hmac.compare_digest(opening_root(index,old,proof),self.work_root),'current Merkle opening')
            if new_value is not None:
                expected=opening_root(index,new_value,proof)
                need(hmac.compare_digest(reply[-32:],expected),'updated root')
                self.work_root=expected
            self.step+=1
            return old
        except Exception:self.dead=True;raise

    def commit(self):
        need(not self.dead and self.work_root is not None,'commit state')
        request=b'C'+struct.pack('>QI',self.tx,self.step)+self.work_root
        try:
            need(hmac.compare_digest(self._rpc(request),b'c'+request[1:]),'final commit response')
            self.root=self.work_root;self.work_root=None
        except Exception:self.dead=True;raise
