#!/usr/bin/env python3
"""A PRF-based encryption + keyed authentication-tree research profile.
The server has NO key and cannot generate new authentication tags. The client
verifies a complete opening before decrypting any object; it uploads tags for
changed tree nodes. HMAC-SHA-512 is a functional PRF instantiation, NOT a proved
numerical bound on real HMAC. This is an authenticated-container compiler test,
not a full encrypted ORAM implementation or a standardized AEAD suite.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import copy,hashlib,hmac,json,random

class Reject(Exception):pass

def enc(*parts:bytes)->bytes:
    return b''.join(len(x).to_bytes(8,'big')+x for x in parts)
def u(x:int,n=16)->bytes:return x.to_bytes(n,'big')

@dataclass(frozen=True)
class Record:
    aad:bytes
    ciphertext:bytes

class Server:
    """Untrusted storage: only ciphertexts and client-supplied PRF tags."""
    def __init__(self,records:list[Record],tags:dict[int,bytes]):
        self.records=copy.deepcopy(records);self.tags=dict(tags);self.N=len(records)
    def open(self,indices:set[int])->tuple[dict[int,Record],dict[int,bytes]]:
        witnesses=witness_indices(self.N,indices)
        return ({i:self.records[i] for i in indices},{i:self.tags[i] for i in witnesses})
    def put(self,records:dict[int,Record],tags:dict[int,bytes]):
        self.records.update(records) if isinstance(self.records,dict) else None
        for i,r in records.items():self.records[i]=r
        self.tags.update(tags)

def witness_indices(N:int,indices:set[int])->set[int]:
    if not indices or any(not 0<=i<N for i in indices):raise Reject('invalid public opening set')
    active={N+i for i in indices};w=set()
    while active!={1}:
        for p in active:
            if (p^1) not in active:w.add(p^1)
        active={p//2 for p in active}
    return w

class Client:
    def __init__(self,key:bytes,context:bytes,sizes:list[int]):
        if len(key)<64:raise ValueError('research profile uses a 512-bit key')
        if len(sizes)==0 or len(sizes)&(len(sizes)-1):raise ValueError('power-of-two test object count')
        self.key=key;self.ctx=context;self.sizes=sizes;self.N=len(sizes)
        self.nonce_counter=0;self.prf_calls=0;self.decryptions=0;self.root=b''
    def F(self,domain:bytes,*parts:bytes)->bytes:
        if self.prf_calls >= (1 << 96):raise OverflowError('public PRF query budget exhausted')
        self.prf_calls+=1
        return hmac.new(self.key,enc(domain,self.ctx,*parts),hashlib.sha512).digest()
    def stream(self,index:int,aad:bytes,nonce:bytes,length:int)->bytes:
        return b''.join(self.F(b'STREAM',u(index),aad,nonce,u(j,8)) for j in range((length+63)//64))[:length]
    def seal(self,index:int,aad:bytes,plaintext:bytes)->Record:
        if len(plaintext)!=self.sizes[index]:raise ValueError('fixed-length object required')
        if self.nonce_counter>=1<<128:raise OverflowError('nonce exhaustion')
        nonce=u(self.nonce_counter);self.nonce_counter+=1
        pad=self.stream(index,aad,nonce,len(plaintext))
        return Record(aad,nonce+bytes(a^b for a,b in zip(plaintext,pad)))
    def decrypt_verified(self,index:int,r:Record)->bytes:
        self.decryptions+=1;n=r.ciphertext[:16];ct=r.ciphertext[16:]
        return bytes(a^b for a,b in zip(ct,self.stream(index,r.aad,n,len(ct))))
    def leaf_tag(self,index:int,r:Record)->bytes:
        if len(r.ciphertext)!=self.sizes[index]+16:raise Reject('wrong fixed object length')
        return self.F(b'LEAF',u(index),r.aad,r.ciphertext)
    def node_tag(self,index:int,left:bytes,right:bytes)->bytes:
        if len(left)!=64 or len(right)!=64:raise Reject('wrong tag length')
        return self.F(b'NODE',u(index),left,right)
    def initialize(self,plains:list[bytes],aads:list[bytes])->Server:
        records=[self.seal(i,aads[i],v) for i,v in enumerate(plains)]
        tags={self.N+i:self.leaf_tag(i,r) for i,r in enumerate(records)}
        for i in range(self.N-1,0,-1):tags[i]=self.node_tag(i,tags[2*i],tags[2*i+1])
        self.root=tags[1];return Server(records,tags)
    def reconstruct(self,indices:set[int],records:dict[int,Record],witnesses:dict[int,bytes]):
        if set(records)!=indices or set(witnesses)!=witness_indices(self.N,indices):raise Reject('opening shape')
        tags=dict(witnesses)
        for i,r in records.items():tags[self.N+i]=self.leaf_tag(i,r)
        active={self.N+i for i in indices};updated={p:tags[p] for p in active}
        while active!={1}:
            parents={p//2 for p in active}
            for p in parents:tags[p]=self.node_tag(p,tags[2*p],tags[2*p+1]);updated[p]=tags[p]
            active=parents
        return tags[1],updated
    def verify(self,indices:set[int],opening):
        records,witnesses=opening
        root,_=self.reconstruct(indices,records,witnesses)
        if not hmac.compare_digest(root,self.root):raise Reject('not current authenticated state')
        return {i:self.decrypt_verified(i,records[i]) for i in sorted(indices)}
    def update(self,server:Server,indices:set[int],opening,values:dict[int,bytes],aads:dict[int,bytes]):
        self.verify(indices,opening)
        if set(values)!=indices or set(aads)!=indices:raise Reject('fixed write set required')
        records={i:self.seal(i,aads[i],values[i]) for i in sorted(indices)}
        root,tags=self.reconstruct(indices,records,opening[1])
        # This test models an online atomic trusted commit. It is NOT disk recovery.
        server.put(records,tags);self.root=root
        return len(tags)

def expect_reject(fn):
    try:fn()
    except Reject:return
    raise AssertionError('malformed opening accepted')

def run():
    N=32;sizes=[288 if i%2==0 else 64 for i in range(N)]
    client=Client(bytes(range(64)),b'PRF-PROFILE-v1',sizes)
    truth=[bytes([i])*sizes[i] for i in range(N)];aads=[u(i,4)+u(0) for i in range(N)]
    server=client.initialize(truth,aads);rng=random.Random(31337);nonces=set()
    for r in server.records:nonces.add(r.ciphertext[:16])
    oldroot=client.root;selected={0,2,4};oldopening=server.open(selected)
    olddata=[server.records[i].ciphertext for i in range(N) if i%2]
    vals={i:truth[i] for i in selected};vals[2]=b'X'*288
    client.update(server,selected,oldopening,vals,{i:aads[i] for i in selected})
    assert olddata==[server.records[i].ciphertext for i in range(N) if i%2]
    for i in selected:truth[i]=vals[i]
    for i in selected:
        assert server.records[i].ciphertext[:16] not in nonces;nonces.add(server.records[i].ciphertext[:16])
    before=client.decryptions;expect_reject(lambda:client.verify(selected,oldopening));assert client.decryptions==before
    current=client.root;client.root=oldroot
    assert client.verify(selected,oldopening)[0]==bytes([0])*288
    client.root=current
    rejection_tests=1;transactions=1;tag_uploads=0
    for t in range(1500):
        indices=set(rng.sample(range(N),rng.randint(1,8)));opening=server.open(indices)
        observed=client.verify(indices,opening)
        assert all(observed[i]==truth[i] for i in indices)
        # Corrupt a returned object, irrespective of whether it is a header/data/dummy.
        i=min(indices);records,wit=copy.deepcopy(opening)
        ct=records[i].ciphertext
        records[i]=Record(records[i].aad,ct[:-1]+bytes([ct[-1]^1]))
        before=client.decryptions;expect_reject(lambda:client.verify(indices,(records,wit)));assert client.decryptions==before;rejection_tests+=1
        # Public-set shape manipulation must also be rejected before decryption.
        records,wit=copy.deepcopy(opening);records.pop(i)
        before=client.decryptions;expect_reject(lambda:client.verify(indices,(records,wit)));assert client.decryptions==before;rejection_tests+=1
        vals={i:rng.randbytes(sizes[i]) for i in indices}
        tag_uploads+=client.update(server,indices,opening,vals,{i:aads[i] for i in indices})
        for i in indices:
            nonce=server.records[i].ciphertext[:16];assert nonce not in nonces;nonces.add(nonce);truth[i]=vals[i]
        transactions+=1
    assert client.verify(set(range(N)),server.open(set(range(N))))==dict(enumerate(truth))
    result=dict(transactions=transactions,malicious_rejections=rejection_tests,
        unique_nonce_count=len(nonces),verification_precedes_decryption=True,
        header_only_preserves_data=True,root_rollback_negative_control=True,
        server_has_no_prf_key=True,client_supplied_tag_uploads=tag_uploads,
        total_prf_calls=client.prf_calls,authentication_tag_bytes=64,nonce_bytes=16,
        limits='Container/compiler test only. HMAC-SHA-512 PRF advantage is an explicit computational assumption, not a certified 2^-128 number. Disk recovery and the full encrypted ORAM driver are not implemented here.')
    (Path(__file__).resolve().parent/'prf_profile_results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':run()
