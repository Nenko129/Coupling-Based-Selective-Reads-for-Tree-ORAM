"""CB/DeadQ level with payload-free authentication of overwritten slots."""
from ab_deadq_cb_level import CBRoutedLevel,provision_cb
from ab_deadq_authenticated_store import WireRecorder,need
from ab_deadq_cb_hash_store import HashRowServer,HashVerifiedRows


class HashCBLevel(CBRoutedLevel):
    def _set(self,i,value):
        if i<=self.g.queue_row:return super()._set(i,value)
        # Only freshly sealed slot/header rows reach this branch. Their burned
        # nonces imply a different byte string, so no old-value equality read
        # is necessary. HashVerifiedRows verifies replacement against old root.
        need(len(value)==self.g.length(i),'fresh encrypted row length')
        self.cache[i]=value;self.dirty.add(i)


def replace_provisioned(old,oldwire):
    """Only during trusted initial provisioning, before any RPC transaction."""
    need(old.rows.tx==0 and not oldwire.frames,'upgrade only at provisioning')
    g=old.g;client=HashCBLevel(None,g,old.key,old.domain,old.next_nonce,old.placement)
    rows=oldwire.server.committed.rows[:g.count];wire=WireRecorder(HashRowServer(rows))
    client.rows=HashVerifiedRows(wire.exchange,wire.server.committed.root,g)
    return client,wire


def provision_hash_cb(*args,**kwargs):return replace_provisioned(*provision_cb(*args,**kwargs))
