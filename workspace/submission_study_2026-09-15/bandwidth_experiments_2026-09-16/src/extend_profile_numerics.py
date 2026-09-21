"""Extend a named numerical profile without replacing existing evidence."""
from common import *
from fractions import Fraction as F
from check_profile_numerics import linux
from audit_profile_grids import grid
import argparse, subprocess, time, math

NUM = PACKAGE / 'numerics'

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--profile', required=True)
    p.add_argument('--cap', type=int, required=True)
    p.add_argument('--poisson-cutoff', type=int, default=128)
    p.add_argument('--period', type=int, default=3)
    args = p.parse_args()
    gate = json.loads((NUM / 'exact_checks.json').read_text())
    assert gate['status'] == 'passed'
    assert gate['kernel_sha256'] == sha(NUM / 'ghost_profile.cpp')
    assert gate['binary_sha256'] == sha(NUM / 'ghost_profile')
    profile = NUM / 'profiles' / (args.profile + '.txt')
    spec = json.loads(profile.with_suffix('.json').read_text())
    H = len(spec['Z_root_to_leaf']); jobs = []; grids = []
    identity = dict(kernel_sha256=sha(NUM/'ghost_profile.cpp'), binary_sha256=sha(NUM/'ghost_profile'),
                    profile_sha256=sha(profile), profile_spec_sha256=sha(profile.with_suffix('.json')))
    dest = NUM / f'{args.profile}_c{args.cap}_m{args.poisson_cutoff}_audit.json'
    assert not dest.exists(), 'Do not overwrite an audited extension'
    for mode in ('up', 'next'):
        prefix = NUM / 'grids' / f'{args.profile}_{mode}_c{args.cap}_m{args.poisson_cutoff}'
        assert not prefix.with_suffix('.log').exists(), 'Inspect prior job/process before reuse'
        command = ['wsl', '--exec', linux(NUM/'ghost_profile'), str(args.cap), str(H),
                   str(args.poisson_cutoff), '1', mode, linux(prefix), linux(profile)]
        with prefix.with_suffix('.log').open('w', encoding='utf-8') as log:
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            save(NUM / f'{args.profile}_c{args.cap}_live.json', dict(
                identity=identity, pid=proc.pid, parent_pid=os.getpid(), command=command, started=time.time()))
            code = proc.wait()
        assert code == 0, f'Numerical job failed: {prefix}'
        meta_path = prefix.with_name(prefix.name+'_meta.json')
        meta = json.loads(meta_path.read_text())
        assert meta['rounding_self_test'] and meta['height'] == H
        assert meta['Z_root_to_leaf'] == spec['Z_root_to_leaf']
        assert list(map(F, meta['rate_root_to_leaf'])) == list(map(F, spec['lambda_root_to_leaf']))
        assert meta['seed_upper_root_to_leaf'] == [spec['seeds'][x]['upper_hex'] for x in spec['lambda_root_to_leaf']]
        values = grid(prefix.with_suffix('.csv'))
        assert set(values) == {(h, r) for h in range(1,H+1) for r in range(args.cap+1)}
        assert all(values[h,r] >= values[h,r+1] for h in range(1,H+1) for r in range(args.cap))
        grids.append(values)
        item = dict(mode=mode, prefix=str(prefix.relative_to(PACKAGE)), grid_sha256=sha(prefix.with_suffix('.csv')),
                    meta_sha256=sha(meta_path), log_sha256=sha(prefix.with_suffix('.log')))
        jobs.append(item); print(json.dumps(item), flush=True)
    assert args.period >= 1
    Q = 1 << 56; target = F(1, 1 << 132); offset = args.period-1
    value = lambda r: max(g[H,r] for g in grids)
    minimum = next((r+offset for r in range(args.cap+1) if Q*value(r) <= target), None)
    proposed = None if minimum is None else ((minimum+31)//32)*32
    def result(R):
        x = Q*value(R-offset)
        return dict(R=R, lifetime_bound_exact=str(x), lifetime_log2=math.log2(float(x)) if x else None,
                    admitted=x<=target)
    tested = [result(256)]
    if proposed is not None and proposed-offset <= args.cap: tested.append(result(proposed))
    report = dict(status='numerical_structure_audited', profile=args.profile, height=H, cap=args.cap,
                  poisson_cutoff=args.poisson_cutoff, period=args.period, identity=identity, jobs=jobs, offset=offset, Q=Q,
                  target_exact=str(target), minimum_R_within_grid=minimum, proposed_R_rounded32=proposed,
                  tested=tested, auditor_sha256=sha(__file__), protocol_closure=False, independent_third_party_audit=False)
    save(dest, report); print(json.dumps(report), flush=True)

if __name__ == '__main__': main()
