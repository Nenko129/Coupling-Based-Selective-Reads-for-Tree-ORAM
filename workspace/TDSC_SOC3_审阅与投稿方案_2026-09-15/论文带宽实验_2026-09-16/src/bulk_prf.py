"""Exact HMAC stream evaluation using PBKDF2's one-iteration block primitive.

This is not password derivation: the key is the unchanged 64-byte research key.
For j>=1, PBKDF2 with c=1 outputs HMAC(key, salt || uint32be(j)).
Taking salt=prefix||uint32be(0) gives prefix||uint64be(j) exactly.
Block zero is evaluated separately. Logical PRF accounting is unchanged.
"""
import hashlib,hmac
from fast_prf import make_fast_prf

def make_bulk_prf(engine):
    Base=make_fast_prf(engine)
    class BulkPRF(Base):
        def stream(self,ctx,oid,aad,nonce,n):
            count=(n+63)//64
            # Preserve scalar boundary failures and C API length restrictions.
            if count<4 or self.calls+count>(1<<96) or (count-1)*64>0x7fffffff:
                return super().stream(ctx,oid,aad,nonce,n)
            prefix=engine.encode(b'STREAM',ctx,oid,aad,nonce)+engine.ui(8,8)
            if len(prefix)+4>0x7fffffff:
                return super().stream(ctx,oid,aad,nonce,n)
            first=hmac.digest(self.key,prefix+bytes(8),'sha512')
            rest=hashlib.pbkdf2_hmac('sha512',self.key,prefix+bytes(4),1,(count-1)*64)
            self.calls+=count;self.max_input=max(self.max_input,len(prefix)+8)
            return (first+rest)[:n]
    return BulkPRF
