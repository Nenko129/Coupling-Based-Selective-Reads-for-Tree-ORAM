"""Byte-equivalent HMAC-prefix reuse and C-level XOR for the research harness.

The PRF, its inputs, nonce allocation and primitive accounting are unchanged.
No alternative cipher or proxy cost model is introduced.
"""
import hashlib, hmac


def make_fast_prf(engine):
    Base = engine.PRF

    class FastPRF(Base):
        def stream(self, ctx, oid, aad, nonce, n):
            count = (n + 63) // 64
            # Keep exact partial progress and exception order at public bounds.
            if count <= 0 or self.calls + count > (1 << 96) or count > (1 << 64):
                return super().stream(ctx, oid, aad, nonce, n)
            prefix = engine.encode(b'STREAM', ctx, oid, aad, nonce) + engine.ui(8, 8)
            state = hmac.new(self.key, prefix, hashlib.sha512)
            blocks = []
            for j in range(count):
                block = state.copy()
                block.update(engine.ui(j, 8))
                blocks.append(block.digest())
            self.calls += count
            self.max_input = max(self.max_input, len(prefix) + 8)
            return b''.join(blocks)[:n]

        def seal(self, ctx, oid, aad, plain):
            if self.nonces >= (1 << 128):
                raise engine.Overflow('nonce capacity')
            nonce = engine.ui(self.nonces)
            self.nonces += 1
            stream = self.stream(ctx, oid, aad, nonce, len(plain))
            return nonce + (int.from_bytes(plain, 'big') ^ int.from_bytes(stream, 'big')).to_bytes(len(plain), 'big')

        def decrypt(self, ctx, oid, aad, ct):
            engine.need(len(ct) >= engine.NONCE, 'ciphertext length')
            self.decryptions += 1
            body = ct[engine.NONCE:]
            stream = self.stream(ctx, oid, aad, ct[:engine.NONCE], len(body))
            return (int.from_bytes(body, 'big') ^ int.from_bytes(stream, 'big')).to_bytes(len(body), 'big')

    return FastPRF
