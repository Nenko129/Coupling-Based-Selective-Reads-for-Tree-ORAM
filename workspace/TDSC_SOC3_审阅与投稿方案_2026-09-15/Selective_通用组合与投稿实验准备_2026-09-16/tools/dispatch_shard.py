"""Parallel orchestration for the frozen formal plan.

Shards are disjoint by plan index.  This file changes no experiment input and
does not write the canonical queue_state.json; the canonical serial dispatcher
is run once after all shards to validate every receipt and mark completion.
"""

from pathlib import Path
import argparse
import json
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from minimal_runtime import HOME, identity


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shards", type=int, required=True)
    args = p.parse_args()
    assert 0 <= args.shard < args.shards

    plan = json.loads((HOME / "formal_plan.json").read_text(encoding="utf-8"))["specs"]
    frozen = json.loads((HOME / "source_lock.json").read_text(encoding="utf-8"))
    assert frozen["source_hashes"] == identity()
    selected = [(i, s) for i, s in enumerate(plan) if i % args.shards == args.shard]
    state = HOME / "results" / "shards" / f"shard_{args.shard:02d}_of_{args.shards:02d}.json"
    completed = []
    for index, spec in selected:
        out = HOME / "results" / "formal" / f"{spec['id']}.json"
        if out.exists():
            row = json.loads(out.read_text(encoding="utf-8"))
            assert row["status"] == "passed" and row["spec"] == spec
            completed.append({"index": index, "id": spec["id"], "status": "reused"})
            continue
        assert frozen["source_hashes"] == identity()
        cmd = [sys.executable, "-B", "-X", "utf8", str(HOME / "src" / spec["driver"]),
               "--spec", str(HOME / "specs" / "formal" / f"{spec['id']}.json")]
        log = HOME / "logs" / "shards" / f"{spec['id']}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as stream:
            child = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT, cwd=str(HOME))
            write(state, {"stage": "running", "shard": args.shard, "shards": args.shards,
                          "index": index, "id": spec["id"], "child_pid": child.pid,
                          "completed": len(completed), "assigned": len(selected), "time": time.time()})
            code = child.wait()
        if code:
            write(state, {"stage": "failed", "shard": args.shard, "index": index,
                          "id": spec["id"], "returncode": code, "log": str(log), "time": time.time()})
            raise SystemExit(code)
        row = json.loads(out.read_text(encoding="utf-8"))
        assert row["status"] == "passed" and row["spec"] == spec
        completed.append({"index": index, "id": spec["id"], "status": "passed"})
    write(state, {"stage": "complete", "shard": args.shard, "shards": args.shards,
                  "completed": len(completed), "assigned": len(selected), "rows": completed,
                  "time": time.time()})
    print(json.dumps({"shard": args.shard, "completed": len(completed), "assigned": len(selected)}))


if __name__ == "__main__":
    main()
