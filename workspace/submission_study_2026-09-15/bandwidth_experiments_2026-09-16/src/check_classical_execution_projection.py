"""Independent logical-placement oracle for the frozen Path/Ring execution.

Diagnostic executions, not performance samples or a security proof by testing.
All wrappers are instance-local in this process; no frozen/live source changes.
"""
from common import *
from collections import Counter
from dataclasses import asdict
import types
import optimized_oram as e
from meter import StreamingTransport


def route(leaf, height):
    result = [1]
    for bit in range(height - 1, -1, -1):
        result.append(2 * result[-1] + ((leaf >> bit) & 1))
    return tuple(result)


def reverse_bits(value, width):
    return int(f'{value:0{width}b}'[::-1], 2)


class LogicalOracle:
    def __init__(self, config):
        self.c = config
        self.records = {}  # address -> uid, leaf, payload, bucket; bucket 0 = stash
        self.t = self.g = self.uid = 0
        self.max_stash = 0

    def write_path(self, leaf):
        nodes = route(leaf, self.c.L)
        pool = {a: r for a, r in self.records.items() if r[3] == 0 or r[3] in nodes}
        untouched = {a: r for a, r in self.records.items() if a not in pool}
        for bucket in nodes[::-1]:
            eligible = sorted((a for a in pool if bucket in route(pool[a][1], self.c.L)),
                              key=lambda a: pool[a][0])[:self.c.Z]
            for a in eligible:
                uid, label, data, _ = pool.pop(a)
                untouched[a] = (uid, label, data, bucket)
        untouched.update({a: (r[0], r[1], r[2], 0) for a, r in pool.items()})
        self.records = untouched

    def access(self, address, oldleaf, newleaf, previous, updated):
        old = self.records.get(address)
        assert previous == (old[2] if old else bytes(self.c.B))
        if old:
            assert old[1] == oldleaf
            assert old[3] == 0 or old[3] in route(oldleaf, self.c.L)
        if self.c.kind == 'path':
            opened = route(oldleaf, self.c.L)
            self.records = {a: (r[0], r[1], r[2], 0 if r[3] in opened else r[3])
                            for a, r in self.records.items()}
        self.uid += 1
        self.records[address] = (self.uid, newleaf, updated, 0)
        self.t += 1
        if self.c.kind == 'path':
            self.write_path(oldleaf)
            self.g += 1
        elif self.t % self.c.A == 0:
            self.write_path(reverse_bits(self.g % (1 << self.c.L), self.c.L))
            self.g += 1
        self.max_stash = max(self.max_stash, sum(r[3] == 0 for r in self.records.values()))


def decoded(tree, inspector):
    c = tree.c
    records = {a: (r.uid, r.leaf, r.payload, 0) for a, r in tree.stash.items()}
    headers = {}
    for (index, bucket), stored in tree.io.server.buckets.items():
        if index != c.tree:
            continue
        public = stored.header[:e.PUBLIC]
        header = e.Header.decode(c, public, inspector.decrypt(tree.ctx, tree.oid(bucket), public,
                                                             stored.header[e.PUBLIC:]))
        headers[bucket] = header
        assert len(header.live) <= c.Z
        for slot, desc in header.live.items():
            assert desc.address not in records
            assert bucket in route(desc.leaf, c.L)
            data = inspector.decrypt(tree.ctx, tree.oid(bucket, slot), e.ui(header.w), stored.slots[slot])
            records[desc.address] = (desc.uid, desc.leaf, data, bucket)
    assert len(headers) == (1 << (c.L + 1)) - 1
    return records, headers


def attach(tree, key):
    oracle = LogicalOracle(tree.c)
    inspector = e.PRF(key)  # never consume the executing client's counters
    counters = Counter()
    expected_openings = []
    opening = tree.open_path

    def open_path(self, leaf, depths, stage):
        assert tuple(depths) == tuple(range(self.c.L + 1))
        expected_openings.append((stage, leaf))
        return opening(leaf, depths, stage)

    tree.open_path = types.MethodType(open_path, tree)
    neutral = tree.neutral

    def neutral_checked(self, view, bucket):
        before, headers = decoded(self, inspector)
        old = headers[bucket]
        assert old.count == self.c.S
        clocks = self.t, self.g, self.uid
        neutral(view, bucket)
        after, headers = decoded(self, inspector)
        new = headers[bucket]
        assert before == after and clocks == (self.t, self.g, self.uid)
        assert new.gamma == old.gamma and new.w == old.w + 1 and new.v == old.v + 1
        assert new.count == new.used == 0
        counters['neutral_identity'] += 1

    tree.neutral = types.MethodType(neutral_checked, tree)
    fused = tree.fused_logical

    def fused_checked(self, view, address):
        before, headers = decoded(self, inspector)
        early = [b for b in view.headers if headers[b].count == self.c.S]
        clocks = self.t, self.g, self.uid
        old = fused(view, address)
        after, current = decoded(self, inspector)
        expected = dict(before)
        target = expected.pop(address, None)
        assert after == expected and clocks == (self.t, self.g, self.uid)
        assert (old is None) == (target is None)
        if old:
            assert (old.uid, old.leaf, old.payload) == target[:3]
        for b in early:
            assert current[b].gamma == headers[b].gamma
            assert current[b].count == current[b].used.bit_count() == 1
        counters['fused_logical_projection'] += 1
        counters['fused_early_buckets'] += len(early)
        return old

    tree.fused_logical = types.MethodType(fused_checked, tree)

    def observe(event, index, data, state):
        if event != 'access':
            return
        address, oldleaf, newleaf, previous, updated = data
        prior_g = oracle.g
        oracle.access(*data)
        actual, headers = decoded(tree, inspector)
        assert actual == oracle.records, (tree.c, oracle.t, 'placement divergence')
        assert (tree.t, tree.g, tree.uid) == (oracle.t, oracle.g, oracle.uid)
        wanted = [('path' if tree.c.kind == 'path' else 'logical', oldleaf)]
        if tree.c.kind == 'ring' and oracle.t % tree.c.A == 0:
            wanted.append(('evict', reverse_bits(prior_g % (1 << tree.c.L), tree.c.L)))
        assert expected_openings == wanted
        expected_openings.clear()
        counters['access_boundaries'] += 1
        counters['scheduled_evictions'] += len(wanted) - 1

    tree.observer = observe
    return oracle, counters


def value(a, version, size):
    return (a.to_bytes(4, 'big') + version.to_bytes(4, 'big')) * (size // 8)


def single(kind, z, a, s, fused):
    key = b'C' * 64
    c = e.Config(kind, 5, 40, 16, z, a, s, 128, 0, True, fused)
    p = e.PRF(key); server = e.Server([c]); io = StreamingTransport(server)
    tree = e.Tree(c, p, io); tree.initialize()
    oracle, counts = attach(tree, key)
    labels = [p.initial(c.context(), x, c.L) for x in range(c.N)]
    truth = {}
    # Forced leaf collisions exercise nonempty stash and saturated paths.
    for step in range(120):
        target = step if step < c.N else ((step - c.N) % 5 if step < 80 else (step * 17) % c.N)
        fresh = 0 if step < 80 else ((step * 11) % (1 << c.L))
        before = truth.get(target, bytes(c.B)); after = value(target, step, c.B)
        answer = tree.access(target, labels[target], fresh, lambda _: after)
        assert answer == before
        truth[target] = after; labels[target] = fresh
    return dict(config=asdict(c),mode='forced_collision_single_tree',checks=dict(counts),
                max_boundary_stash=oracle.max_stash,oracle_state_sha256=digest([
                    [x, r[0], r[1], r[2].hex(), r[3]] for x, r in sorted(oracle.records.items())]))


def recursive(kind, z, a, s, fused):
    key = b'R' * 64
    ns = (17, 5, 2)
    configs = [e.Config(kind, max(1, (n - 1).bit_length()), n, 16, z, a, s, 128, j, True, fused)
               for j, n in enumerate(ns)]
    old_transport = e.Transport
    e.Transport = StreamingTransport
    try:
        model = e.RecursiveORAM(configs, key)
        checks = [attach(t, key) for t in model.trees]
        model.initialize(lambda a: value(a, 0, 16))
        assert [t.t for t in model.trees] == [sum(ns[:j+1]) for j in range(3)]
        truth = [0] * ns[0]
        for step in range(80):
            target = (step * 7 if step < 40 else step // 3) % ns[0]
            update = None if step % 3 == 0 else value(target, step + 1, 16)
            answer = model.access(target, update)
            assert answer == value(target, truth[target], 16)
            if update is not None: truth[target] = step + 1
        assert [t.t for t in model.trees] == [sum(ns[:j+1]) + 80 for j in range(3)]
        return dict(configs=[asdict(c) for c in configs],mode='three_recursive_layers',
                    checks=[dict(c) for _, c in checks],clocks=[t.t for t in model.trees],
                    max_boundary_stash=[o.max_stash for o, _ in checks])
    finally:
        e.Transport = old_transport


def main():
    identity = source_identity()
    profiles = [('path', 4, 3, 3), ('path', 5, 3, 3),
                ('ring', 4, 3, 1), ('ring', 4, 3, 3),
                ('ring', 7, 6, 1), ('ring', 7, 6, 6), ('ring', 7, 6, 9)]
    rows = []
    for kind, z, a, s in profiles:
        for fused in ((True,) if kind == 'path' else (False, True)):
            pair = [single(kind, z, a, s, fused), recursive(kind, z, a, s, fused)]
            rows.extend(pair)
            print(json.dumps(dict(kind=kind,Z=z,A=a,S=s,fused=fused,completed_cases=len(rows))),flush=True)
    assert source_identity() == identity
    totals = Counter()
    for r in rows:
        for x in (r['checks'] if isinstance(r['checks'], list) else [r['checks']]): totals.update(x)
    assert totals['neutral_identity'] > 0 and totals['fused_early_buckets'] > 0
    assert max(r['max_boundary_stash'] for r in rows if r['mode'].startswith('forced')) > 0
    save(PACKAGE/'results/classical_execution_projection_checks.json', dict(status='passed',
         rows=rows,totals=dict(totals),source_hashes=identity,checker_sha256=sha(__file__),
         execution_cases=len(rows),scope='honest successful logical occupancy and payload projection; all concrete bucket owners',
         sampled_checks_are_not_proof=True,performance_samples=False,full_security_admission=False,
         excluded=['malicious transcripts and PRF advantage','heterogeneous/CB/IR-local-hit protocols',
                   'capacity theorem parameter admission','exhaustive arbitrary-length execution']))
    print(json.dumps(dict(status='passed',cases=len(rows),totals=dict(totals))),flush=True)


if __name__ == '__main__': main()
