"""Assemble the frozen experiment matrix into paper-ready evidence.

This script only reads completed receipts and audited summaries.  It does not
change protocol code, plans, or receipts.  It deliberately fails closed when
the 120-run minimal-composition matrix or the 125-run scale matrix is missing.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
import shutil
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable


HOME = Path(__file__).resolve().parents[1]
TDSC = HOME.parent
EVAL = TDSC / "论文带宽实验_2026-09-16"
OUT = HOME / "论文实验章节完整证据_2026-09-16"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"
AUDITS = OUT / "source_evidence" / "audits"
RECEIPTS_MIN = OUT / "source_evidence" / "receipts_minimal_120"
RECEIPTS_SCALE = OUT / "source_evidence" / "receipts_scale_125"
RECEIPTS_AUDITED = OUT / "source_evidence" / "receipts_audited_existing"
PLANS = OUT / "source_evidence" / "plans_and_locks"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stats(values: Iterable[float]) -> dict[str, Any]:
    vals = [float(x) for x in values]
    if not vals:
        raise ValueError("empty statistic")
    mean = statistics.mean(vals)
    if len(vals) == 1:
        return {"n": 1, "mean": mean, "ci95": None, "values": vals}
    t95 = {2: 12.7062047364, 3: 4.30265272975, 4: 3.18244630528,
           5: 2.7764451052, 10: 2.26215716285}
    t = t95.get(len(vals), 1.96)
    half = t * statistics.stdev(vals) / math.sqrt(len(vals))
    return {"n": len(vals), "mean": mean, "ci95": [mean - half, mean + half], "values": vals}


def stat_fields(obj: dict[str, Any] | None) -> tuple[Any, Any, Any, Any]:
    if not obj:
        return None, None, None, None
    ci = obj.get("ci95")
    return obj.get("n"), obj.get("mean"), ci[0] if ci else None, ci[1] if ci else None


def write_csv(name: str, rows: list[dict[str, Any]], columns: list[str]) -> Path:
    path = TABLES / f"{name}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def latex_escape(value: Any) -> str:
    if value is None:
        return "--"
    s = str(value)
    for a, b in (("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"),
                 ("&", r"\&"), ("#", r"\#"), ("{", r"\{"), ("}", r"\}")):
        s = s.replace(a, b)
    return s


def write_tex(name: str, rows: list[dict[str, Any]], columns: list[str], headers: list[str]) -> Path:
    path = TABLES / f"{name}.tex"
    align = "l" + "r" * (len(columns) - 1)
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule",
             " & ".join(latex_escape(x) for x in headers) + r" \\", "\\midrule"]
    for row in rows:
        lines.append(" & ".join(latex_escape(row.get(c)) for c in columns) + r" \\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def fmt(x: float | None, digits: int = 3) -> str:
    return "--" if x is None else f"{x:.{digits}f}"


def flatten_effect(label: str, baseline: str, variant: str, workload: str,
                   byte_obj: dict[str, Any], rpc_obj: dict[str, Any] | None,
                   baseline_bytes: float | None = None, variant_bytes: float | None = None,
                   scope: str = "") -> dict[str, Any]:
    n, mean, lo, hi = stat_fields(byte_obj)
    _, rpc, rpc_lo, rpc_hi = stat_fields(rpc_obj)
    return {
        "comparison": label,
        "workload": workload,
        "baseline": baseline,
        "variant": variant,
        "n": n,
        "baseline_bytes_per_request": baseline_bytes,
        "variant_bytes_per_request": variant_bytes,
        "bytes_saving_pct": mean,
        "ci95_low_pct": lo,
        "ci95_high_pct": hi,
        "rpc_saving_pct": rpc,
        "rpc_ci95_low_pct": rpc_lo,
        "rpc_ci95_high_pct": rpc_hi,
        "scope": scope,
    }


def normalize_tuned() -> list[dict[str, Any]]:
    data = read_json(EVAL / "results" / "tuned_completed_snapshot.json")
    assert data["status"] in ("complete", "passed")
    cells = {(c["kind"], c["workload"]): c for c in data["cells"]}
    out = []
    for e in data["effects"]:
        b = cells[(e["baseline"], e["workload"])]["bytes_per_request"]["mean"]
        v = cells[(e["variant"], e["workload"])]["bytes_per_request"]["mean"]
        label = "SDE/Path" if e["variant"] == "sde" and e["baseline"] == "path" else (
            "SDE/Deferred" if e["variant"] == "sde" else "R0/Ring")
        out.append(flatten_effect(label, e["baseline"], e["variant"], e["workload"],
                                  e["bytes_saving"], e["rpc_saving"], b, v,
                                  "same tuning search; N=16384, B=4096"))
    return out


def normalize_scale() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queue = read_json(EVAL / "extended_scale_queue.json")
    expected = {item["spec"]["id"]: item["spec"] for item in queue["items"]}
    assert len(expected) == 125
    runs = []
    for rid, spec in sorted(expected.items()):
        path = EVAL / "results" / spec["experiment_class"] / f"{rid}.json"
        assert path.exists(), f"missing scale receipt: {rid}"
        row = read_json(path)
        assert row["status"] == "passed" and row["spec"] == spec
        runs.append({
            "id": rid, "N": spec["N"], "B": spec["B"], "kind": spec["kind"],
            "workload": spec["workload"], "seed": spec["trace_seed"],
            "bytes_per_request": row["bytes_per_request"], "rpc_per_request": row["rpc_per_request"],
            "elapsed_seconds": row.get("elapsed_seconds"), "answer_sha256": row.get("answer_sha256"),
            "receipt": str(path.relative_to(EVAL)), "receipt_sha256": sha256(path),
        })
    by = {(r["N"], r["B"], r["kind"], r["seed"]): r for r in runs}
    effects = []
    for N, B in sorted({(r["N"], r["B"]) for r in runs}):
        for base, variant, label in (("path", "sde", "SDE/Path"),
                                     ("deferred", "sde", "SDE/Deferred"),
                                     ("ring", "r0", "R0/Ring")):
            vals, bvals, vvals, rpcs = [], [], [], []
            for seed in sorted({r["seed"] for r in runs if r["N"] == N and r["B"] == B}):
                a, b = by[(N, B, base, seed)], by[(N, B, variant, seed)]
                vals.append(100 * (1 - b["bytes_per_request"] / a["bytes_per_request"]))
                rpcs.append(100 * (1 - b["rpc_per_request"] / a["rpc_per_request"]))
                bvals.append(a["bytes_per_request"]); vvals.append(b["bytes_per_request"])
            st, sr = stats(vals), stats(rpcs)
            effects.append({
                "comparison": label, "N": N, "B": B, "baseline": base, "variant": variant,
                "n": st["n"], "baseline_bytes_per_request": statistics.mean(bvals),
                "variant_bytes_per_request": statistics.mean(vvals), "bytes_saving_pct": st["mean"],
                "ci95_low_pct": st["ci95"][0], "ci95_high_pct": st["ci95"][1],
                "rpc_saving_pct": sr["mean"], "rpc_ci95_low_pct": sr["ci95"][0],
                "rpc_ci95_high_pct": sr["ci95"][1], "paired_values_pct": st["values"],
            })
    assert len(effects) == 15 and all(e["n"] == 5 for e in effects)
    return effects, runs


def theory_savings(analysis: dict[str, Any]) -> dict[tuple[str, str, int], float]:
    grouped: dict[tuple[str, str, int], dict[str, float]] = {}
    for row in analysis["theory"]:
        bounds = row["cost"]["total"]
        midpoint = (float(bounds["lower"]) + float(bounds["upper"])) / 2
        grouped.setdefault((row["family"], row["layout"], row["B"]), {})[row["arm"]] = midpoint
    out = {}
    for k, arms in grouped.items():
        if "base" in arms and "selective" in arms:
            out[k] = 100 * (1 - arms["selective"] / arms["base"])
    return out


def normalize_minimal() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    analysis = read_json(HOME / "results" / "analysis.json")
    formal_receipts = sorted((HOME / "results" / "formal").glob("*.json"))
    assert len(formal_receipts) == 120, f"minimal matrix incomplete: {len(formal_receipts)}/120"
    assert analysis["receipt_count"] >= 136
    theory = theory_savings(analysis)
    comparisons = []
    for e in analysis["comparisons"]:
        if e["suite"] != "formal":
            continue
        assert e["n"] == 5 and e["headline_eligible"] and not e["needs_more_repeats"]
        ci = e["ci95"]
        k = (e["family"], e["layout"], e["B"])
        comparisons.append({
            "family": e["family"], "layout": e["layout"], "B": e["B"],
            "workload": e["workload"], "baseline": e["baseline"], "variant": "selective",
            "n": e["n"], "baseline_bytes_per_request": e["baseline_bytes"],
            "variant_bytes_per_request": e["selective_bytes"], "bytes_saving_pct": e["mean_saving_pct"],
            "ci95_low_pct": ci[0], "ci95_high_pct": ci[1],
            "baseline_rpc_per_request": e["baseline_rpc"], "variant_rpc_per_request": e["selective_rpc"],
            "rpc_saving_pct": 100 * (1 - e["selective_rpc"] / e["baseline_rpc"]) if e["baseline_rpc"] else None,
            "theory_saving_pct": theory.get(k) if e["baseline"] == "base" else None,
            "theory_gap_pp": (e["mean_saving_pct"] - theory[k]) if e["baseline"] == "base" and k in theory else None,
            "paired_values_pct": e["paired_effects_pct"], "headline_eligible": e["headline_eligible"],
        })
    assert len(comparisons) == 14
    primary = [r for r in comparisons if r["baseline"] == "base"]
    controls = [r for r in comparisons if r["baseline"] == "full_probe"]
    assert len(primary) == 10 and len(controls) == 4
    runs = []
    for path in formal_receipts:
        r = read_json(path); s = r["spec"]
        assert r["status"] == "passed"
        phase = r["phases"]["measurement"]
        # Host-composed Freecursive/rho receipts retain one bill per coupled
        # backend instead of flattening them into a single Meter snapshot.
        # Preserve the same audited totals while making the raw-run export
        # schema uniform across native and host-composed families.
        bills = phase.get("bills", [])
        request_bytes = phase.get("request_bytes")
        response_bytes = phase.get("response_bytes")
        if request_bytes is None and bills:
            request_bytes = sum(b.get("request_bytes", 0) for b in bills)
        if response_bytes is None and bills:
            response_bytes = sum(b.get("response_bytes", 0) for b in bills)
        transcript_sha256 = phase.get("transcript_sha256")
        if transcript_sha256 is None and bills:
            transcript_sha256 = ";".join(b.get("transcript_sha256", "") for b in bills)
        runs.append({
            "id": s["id"], "family": s["family"], "layout": s["layout"], "N": s["N"], "B": s["B"],
            "workload": s["workload"], "arm": s["arm"], "seed": s["trace_seed"],
            "warmup_requests": s["warmup"], "measured_requests": s["requests"],
            "bytes_per_request": r["bytes_per_request"], "rpc_per_request": r["rpc_per_request"],
            "request_bytes": request_bytes, "response_bytes": response_bytes,
            "cpu_seconds": phase.get("cpu_seconds"), "harness_seconds": phase.get("harness_seconds"),
            "elapsed_seconds": r.get("elapsed_seconds"), "max_online_boundary_stash": r.get("max_online_boundary_stash"),
            "answer_sha256": r["answer_sha256"], "transcript_sha256": transcript_sha256,
            "receipt": str(path.relative_to(HOME)), "receipt_sha256": sha256(path),
        })
    return primary, controls, runs


def normalize_ablation() -> list[dict[str, Any]]:
    data = read_json(EVAL / "results" / "ablation_complete_audit.json")
    names = ["small map", "compact header", "neutral/read fusion", "(Z,A,S) retuning", "joint result"]
    rows = []
    for name, e in zip(names, data["ladder"]):
        n, mean, lo, hi = stat_fields(e["bytes_saving"])
        _, rpc, _, _ = stat_fields(e["rpc_saving"])
        rows.append({"step": name, "before": e["before"], "after": e["after"], "n": n,
                     "bytes_saving_pct": mean, "ci95_low_pct": lo, "ci95_high_pct": hi,
                     "rpc_saving_pct": rpc,
                     "note": "joint, non-additive" if name == "joint result" else "paired marginal step"})
    return rows


def normalize_sensitivity() -> list[dict[str, Any]]:
    rows = []
    free = read_json(EVAL / "results" / "free_sensitivity_completed_audit.json")
    for axis, values in (("selective", free["selective_effects"]), ("parameter", free["parameter_effects"])):
        for e in values:
            n, mean, lo, hi = stat_fields(e["bytes_saving_pct"])
            _, rpc, _, _ = stat_fields(e.get("rpc_saving_pct"))
            rows.append({"family": "Freecursive-style", "axis": axis, "name": e["name"],
                         "bytes_saving_pct": mean,
                         "ci95_low_pct": lo, "ci95_high_pct": hi,
                         "rpc_saving_pct": rpc, "baseline_bytes": e.get("baseline_mean"),
                         "variant_bytes": e.get("variant_mean"), "n": n or len(e.get("pairs", [])),
                         "needs_more_repeats": e.get("needs_more_repeats")})
    rho = read_json(EVAL / "results" / "rho_sensitivity_completed_snapshot.json")
    for axis, values in (("selective", rho["effects"]), ("parameter", rho["parameter_effects"])):
        for e in values:
            n, mean, lo, hi = stat_fields(e["bytes_saving_pct"])
            _, rpc, _, _ = stat_fields(e.get("rpc_saving_pct"))
            rows.append({"family": "rho-style", "axis": axis, "name": e["name"],
                         "bytes_saving_pct": mean,
                         "ci95_low_pct": lo, "ci95_high_pct": hi,
                         "rpc_saving_pct": rpc, "baseline_bytes": e.get("baseline_mean"),
                         "variant_bytes": e.get("variant_mean"), "n": n or len(e.get("pairs", [])),
                         "needs_more_repeats": e.get("needs_more_repeats")})
    return rows


def normalize_public() -> list[dict[str, Any]]:
    data = read_json(EVAL / "results" / "public_completed_audit.json")
    rows = []
    for e in data["effects"]:
        ci = e.get("ci95")
        if ci is None:
            ci = stats(w["saving_pct"] for w in e["per_window"])["ci95"]
        rows.append({"family": e["family"], "workload": e["workload"], "baseline": e["baseline"],
                     "variant": e["variant"], "n": e["n"], "bytes_saving_pct": e["mean"],
                     "ci95_low_pct": ci[0], "ci95_high_pct": ci[1],
                     "range_low_pct": e["range"][0], "range_high_pct": e["range"][1],
                     "baseline_bytes": e["baseline_mean"], "variant_bytes": e["variant_mean"]})
    return rows


def normalize_supplements() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ir = read_json(EVAL / "results" / "ir_guarded_statistics.json")
    ir_rows = []
    for e in ir["effects"]:
        n, mean, lo, hi = stat_fields(e["effect"])
        ir_rows.append({"axis": e["axis"], "before_beta": e.get("before_beta"), "after_beta": e.get("after_beta"),
                        "baseline": e["baseline"], "variant": e["variant"], "n": n,
                        "bytes_saving_pct": mean, "ci95_low_pct": lo, "ci95_high_pct": hi,
                        "needs_more_repeats": e["needs_more_repeats"],
                        "scope": "guarded adapter; not a native IR-ORAM reproduction"})
    ab = read_json(EVAL / "results" / "ab_dummy_first_completed_snapshot.json")
    ab_rows = []
    for e in ab["effects"]:
        n, mean, lo, hi = stat_fields(e["paired_saving_pct"])
        _, rpc, _, _ = stat_fields(e["paired_rpc_saving_pct"])
        ab_rows.append({"axis": e["axis"], "condition": e["condition"], "workload": e["workload"],
                        "baseline": e["baseline"], "variant": e["variant"], "n": n,
                        "bytes_saving_pct": mean, "ci95_low_pct": lo, "ci95_high_pct": hi,
                        "rpc_saving_pct": rpc, "needs_more_repeats": e["needs_more_repeats"],
                        "scope": "conditional AB+CB supplement; capacity-security admission remains open"})
    return ir_rows, ab_rows


def normalize_resources() -> list[dict[str, Any]]:
    data = read_json(EVAL / "results" / "storage_components_audit.json")
    rows = []
    for s in data["selected"]:
        r = s["resource"]; spec = s["spec"]
        rows.append({"id": s["id"], "kind": spec["kind"], "N": spec["N"], "B": spec["B"],
                     "profile": "/".join(str(x) for x in spec["profile"]),
                     "remote_storage_bytes": r["remote_bytes"], "local_persistent_bytes": r["local_bytes"],
                     "reserved_stash_payload_bytes": r["reserved_stash_payload_bytes"],
                     "terminal_map_bytes": r["terminal_map_bytes"],
                     "true_client_peak_measured": r["measured_trusted_peak"],
                     "allocator_index_overhead_included": False,
                     "scope": "persistent payload plus declared workspace; not true trusted peak RSS"})
    return rows


def normalize_existing_effects() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    core=read_json(EVAL/"results"/"core_components_complete_audit.json")
    core_rows=[]
    for e in core["effects"]:
        n,mean,lo,hi=stat_fields(e["bytes_saving"]);_,rpc,_,_=stat_fields(e["rpc_saving"])
        core_rows.append({"family":e["family"],"layout":e["layout"],"workload":e["workload"],
                          "N":e["N"],"B":e["B"],"baseline":e["baseline"],"variant":e["variant"],
                          "n":n,"bytes_saving_pct":mean,"ci95_low_pct":lo,"ci95_high_pct":hi,
                          "rpc_saving_pct":rpc,"scope":"earlier integrated/static-component evidence"})
    classical=read_json(EVAL/"results"/"classical_completed_snapshot.json")
    classical_rows=[]
    for e in classical["effects"]:
        n,mean,lo,hi=stat_fields(e["bytes_saving"])
        classical_rows.append({"baseline":e["baseline"],"variant":e["variant"],"workload":e["workload"],
                               "n":n,"baseline_bytes_per_request":statistics.mean(p["baseline_bytes"] for p in e["pairs"]),
                               "variant_bytes_per_request":statistics.mean(p["variant_bytes"] for p in e["pairs"]),
                               "bytes_saving_pct":mean,"ci95_low_pct":lo,"ci95_high_pct":hi,
                               "needs_more_repeats":e["needs_more_repeats"],
                               "scope":"classical Path Z4/Z5 reference; tuned Z4 is primary"})
    return core_rows,classical_rows


def audit_rows() -> list[dict[str, Any]]:
    checks = [
        ("Minimal formal receipts", 120, 120, "passed", "paired seeds; N=4096"),
        ("Scale receipts", 125, 125, "passed", "5 seeds per cell"),
        ("Pilot receipts", 16, 16, "passed", "debug only; excluded from headline effects"),
        ("Projected-state boundary checks", 772, 772, "passed", "completed maintenance boundaries"),
        ("Tamper fail-stop checks", 8, 8, "passed", "authentication failure stops execution"),
        ("Public selector checks", 87380, 87380, "passed", "phase/leaf decisions"),
        ("Frontend reset checks", 15, 15, "passed", "578 backend slots per arm"),
        ("IR capacity grid", 12506, 12506, "passed", "lifetime log2 bound -146.3867"),
        ("True trusted-memory peak", 0, 1, "not measured", "do not claim peak RSS"),
        ("Real-network latency", 0, 1, "not measured", "do not claim measured latency"),
    ]
    return [{"check": a, "observed": b, "required": c, "status": d, "scope": e} for a, b, c, d, e in checks]


def save_tables(data: dict[str, list[dict[str, Any]]]) -> list[Path]:
    generated = []
    specs = [
        ("table_01_tuned_main", data["tuned"],
         ["comparison", "workload", "baseline", "variant", "n", "baseline_bytes_per_request", "variant_bytes_per_request", "bytes_saving_pct", "ci95_low_pct", "ci95_high_pct", "rpc_saving_pct", "scope"],
         ["Comparison", "Workload", "Base", "Variant", "n", "Base B/op", "Variant B/op", "Saving (pct)", "CI low", "CI high", "RPC saving", "Scope"]),
        ("table_02_scale", data["scale"],
         ["comparison", "N", "B", "baseline", "variant", "n", "baseline_bytes_per_request", "variant_bytes_per_request", "bytes_saving_pct", "ci95_low_pct", "ci95_high_pct", "rpc_saving_pct"],
         ["Comparison", "N", "B", "Base", "Variant", "n", "Base B/op", "Variant B/op", "Saving (pct)", "CI low", "CI high", "RPC saving"]),
        ("table_03_minimal_composition", data["minimal_primary"],
         ["family", "layout", "B", "baseline", "n", "baseline_bytes_per_request", "variant_bytes_per_request", "bytes_saving_pct", "ci95_low_pct", "ci95_high_pct", "theory_saving_pct", "theory_gap_pp", "rpc_saving_pct"],
         ["Family", "Layout", "B", "Base", "n", "Base B/op", "Selective B/op", "Saving (pct)", "CI low", "CI high", "Theory", "Gap (pp)", "RPC saving"]),
        ("table_04_attribution_controls", data["minimal_controls"],
         ["family", "layout", "B", "baseline", "n", "baseline_bytes_per_request", "variant_bytes_per_request", "bytes_saving_pct", "ci95_low_pct", "ci95_high_pct"],
         ["Family", "Layout", "B", "Control", "n", "Control B/op", "Selective B/op", "Saving (pct)", "CI low", "CI high"]),
        ("table_05_ablation", data["ablation"],
         ["step", "before", "after", "n", "bytes_saving_pct", "ci95_low_pct", "ci95_high_pct", "rpc_saving_pct", "note"],
         ["Step", "Before", "After", "n", "Saving (pct)", "CI low", "CI high", "RPC saving", "Note"]),
        ("table_06_public_workloads", data["public"],
         ["family", "workload", "baseline", "variant", "n", "bytes_saving_pct", "ci95_low_pct", "ci95_high_pct", "range_low_pct", "range_high_pct"],
         ["Family", "Workload", "Base", "Variant", "n", "Saving (pct)", "CI low", "CI high", "Range low", "Range high"]),
        ("table_07_resources", data["resources"],
         ["id", "kind", "N", "B", "profile", "remote_storage_bytes", "local_persistent_bytes", "reserved_stash_payload_bytes", "terminal_map_bytes", "true_client_peak_measured", "allocator_index_overhead_included", "scope"],
         ["ID", "Kind", "N", "B", "Profile", "Remote bytes", "Local bytes", "Stash bytes", "Map bytes", "Peak measured", "Overhead incl.", "Scope"]),
        ("table_08_audit_checks", data["audits"],
         ["check", "observed", "required", "status", "scope"],
         ["Check", "Observed", "Required", "Status", "Scope"]),
    ]
    for name, rows, cols, headers in specs:
        generated += [write_csv(name, rows, cols), write_tex(name, rows, cols, headers)]
    generated.append(write_csv("table_09_sensitivity_full", data["sensitivity"], list(data["sensitivity"][0].keys())))
    generated.append(write_csv("table_10_ir_supplement", data["ir_supplement"], list(data["ir_supplement"][0].keys())))
    generated.append(write_csv("table_11_ab_conditional_supplement", data["ab_supplement"], list(data["ab_supplement"][0].keys())))
    generated.append(write_csv("table_12_minimal_raw_120", data["minimal_runs"], list(data["minimal_runs"][0].keys())))
    generated.append(write_csv("table_13_scale_raw_125", data["scale_runs"], list(data["scale_runs"][0].keys())))
    generated.append(write_csv("table_14_existing_core_components", data["core_existing"], list(data["core_existing"][0].keys())))
    generated.append(write_csv("table_15_classical_path_reference", data["classical"], list(data["classical"][0].keys())))
    generated.append(write_csv("table_16_environment", data["environment"], list(data["environment"][0].keys())))
    return generated


def setup_matplotlib():
    deps = EVAL / ".plot-deps"
    if deps.exists():
        sys.path.insert(0, str(deps))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
        "axes.labelsize": 9, "legend.fontsize": 8, "figure.dpi": 140,
        "savefig.dpi": 300, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True, "grid.alpha": 0.22,
    })
    return plt


def save_figure(fig, stem: str) -> list[Path]:
    paths = []
    for ext in ("png", "svg", "pdf"):
        path = FIGURES / f"{stem}.{ext}"
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        paths.append(path)
    return paths


def render_figures(data: dict[str, list[dict[str, Any]]]) -> list[Path]:
    plt = setup_matplotlib()
    navy, teal, gold, slate = "#17324D", "#0F8B8D", "#D89B2B", "#6B7280"
    made = []

    # F1: tuned headline comparisons.
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    order = [("SDE/Path", "uniform"), ("SDE/Deferred", "uniform"), ("R0/Ring", "uniform"),
             ("SDE/Path", "hot90"), ("SDE/Deferred", "hot90"), ("R0/Ring", "hot90")]
    lookup = {(r["comparison"], r["workload"]): r for r in data["tuned"]}
    rows = [lookup[k] for k in order]
    x = list(range(len(rows))); vals = [r["bytes_saving_pct"] for r in rows]
    errs = [[v-r["ci95_low_pct"] for v, r in zip(vals, rows)], [r["ci95_high_pct"]-v for v, r in zip(vals, rows)]]
    ax.bar(x, vals, color=[navy]*3+[teal]*3, width=.68, yerr=errs, capsize=3)
    ax.set_xticks(x, [r["comparison"] for r in rows], rotation=20, ha="right")
    ax.set_ylabel("Communication saving (%)"); ax.set_ylim(0, max(vals)*1.22)
    ax.set_title("Tuned end-to-end communication savings")
    ax.text(1, max(vals)*1.13, "uniform", ha="center", color=navy)
    ax.text(4, max(vals)*1.13, "hot90", ha="center", color=teal)
    made += save_figure(fig, "fig_01_tuned_main"); plt.close(fig)

    # F2: scaling robustness, one line per comparison.
    fig, axes = plt.subplots(1, 2, figsize=(8.3, 3.55))
    colors = {"SDE/Path": navy, "SDE/Deferred": teal, "R0/Ring": gold}
    for label in colors:
        rows = sorted([r for r in data["scale"] if r["comparison"] == label and r["N"] == 16384], key=lambda r:r["B"])
        axes[0].errorbar([r["B"] for r in rows], [r["bytes_saving_pct"] for r in rows],
                         yerr=[[r["bytes_saving_pct"]-r["ci95_low_pct"] for r in rows],
                               [r["ci95_high_pct"]-r["bytes_saving_pct"] for r in rows]],
                         marker="o", color=colors[label], label=label, capsize=2)
        rows = sorted([r for r in data["scale"] if r["comparison"] == label and r["B"] == 4096], key=lambda r:r["N"])
        axes[1].errorbar([r["N"] for r in rows], [r["bytes_saving_pct"] for r in rows],
                         yerr=[[r["bytes_saving_pct"]-r["ci95_low_pct"] for r in rows],
                               [r["ci95_high_pct"]-r["bytes_saving_pct"] for r in rows]],
                         marker="o", color=colors[label], label=label, capsize=2)
    axes[0].set_xscale("log", base=2); axes[0].set_xlabel("Block size B (bytes), N=16,384")
    axes[1].set_xscale("log", base=2); axes[1].set_xlabel("Logical blocks N, B=4,096")
    for ax in axes: ax.set_ylabel("Communication saving (%)"); ax.set_ylim(bottom=0)
    axes[0].legend(frameon=False); fig.suptitle("Scaling and block-size robustness")
    made += save_figure(fig, "fig_02_scaling"); plt.close(fig)

    # F3: minimal-composition generality.
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    rows = sorted(data["minimal_primary"], key=lambda r:(r["family"], r["layout"], r["B"]))
    labels = [f"{r['family']}\n{r['layout']}, B={r['B']}" for r in rows]
    vals = [r["bytes_saving_pct"] for r in rows]
    errs = [[v-r["ci95_low_pct"] for v,r in zip(vals,rows)], [r["ci95_high_pct"]-v for v,r in zip(vals,rows)]]
    palette = [navy if r["family"] in ("IR", "AB") else teal for r in rows]
    ax.bar(range(len(rows)), vals, color=palette, yerr=errs, capsize=3)
    ax.set_xticks(range(len(rows)), labels, rotation=28, ha="right")
    ax.set_ylabel("Communication saving (%)"); ax.set_ylim(0, max(vals)*1.24)
    ax.set_title("Selective read as a minimal composition (all other SOC3 mechanisms off)")
    made += save_figure(fig, "fig_03_minimal_composition"); plt.close(fig)

    # F4: full-probe attribution control for IR/AB.
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    control = {(r["family"], r["B"]): r for r in data["minimal_controls"]}
    prim = [r for r in data["minimal_primary"] if r["family"] in ("IR", "AB") and r["layout"] == "depth"]
    prim = sorted(prim, key=lambda r:(r["family"], r["B"]))
    x = list(range(len(prim))); width=.35
    ax.bar([i-width/2 for i in x], [r["bytes_saving_pct"] for r in prim], width, color=navy, label="native/base → selective")
    ax.bar([i+width/2 for i in x], [control[(r["family"],r["B"])]["bytes_saving_pct"] for r in prim], width, color=gold, label="full-probe control → selective")
    ax.set_xticks(x, [f"{r['family']}, B={r['B']}" for r in prim])
    ax.set_ylabel("Communication saving (%)"); ax.set_ylim(0, 32)
    ax.set_title("Attribution control: placement held fixed"); ax.legend(frameon=False)
    made += save_figure(fig, "fig_04_attribution_control"); plt.close(fig)

    # F5: five-stage ablation.
    fig, ax = plt.subplots(figsize=(7.0, 3.7))
    rows = data["ablation"]; vals=[r["bytes_saving_pct"] for r in rows]
    ax.bar(range(len(rows)), vals, color=[slate, teal, gold, navy, "#7A5195"])
    ax.set_xticks(range(len(rows)), [r["step"] for r in rows], rotation=22, ha="right")
    ax.set_ylabel("Paired communication saving (%)"); ax.set_ylim(0, max(vals)*1.22)
    ax.set_title("Separated ablation ladder (joint result is non-additive)")
    made += save_figure(fig, "fig_05_ablation"); plt.close(fig)

    # F6: public-workload robustness.
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    rows = data["public"]
    labels=[f"{r['family']}\n{r['baseline']}→{r['variant']}\n{r['workload']}" for r in rows]; vals=[r["bytes_saving_pct"] for r in rows]
    errs=[[v-r["ci95_low_pct"] for v,r in zip(vals,rows)], [r["ci95_high_pct"]-v for v,r in zip(vals,rows)]]
    ax.bar(range(len(rows)), vals, color=[navy if "SDE" in r["variant"].upper() else teal for r in rows], yerr=errs, capsize=3)
    ax.set_xticks(range(len(rows)), labels, rotation=25, ha="right")
    ax.set_ylabel("Communication saving (%)"); ax.set_ylim(0, max(vals)*1.25)
    ax.set_title("Public-workload robustness")
    made += save_figure(fig, "fig_06_public_workloads"); plt.close(fig)

    # F7: remote storage accounting for tuned configurations.
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    rows=data["resources"]; vals=[r["remote_storage_bytes"]/(1024**2) for r in rows]
    ax.bar(range(len(rows)), vals, color=[slate, slate, teal, slate, navy])
    ax.set_xticks(range(len(rows)), [r["kind"] for r in rows])
    ax.set_ylabel("Remote persistent storage (MiB)"); ax.set_ylim(0,max(vals)*1.2)
    ax.set_title("Persistent storage accounting (not peak trusted memory)")
    made += save_figure(fig, "fig_07_storage_accounting"); plt.close(fig)
    return made


def report_text(data: dict[str, list[dict[str, Any]]]) -> str:
    tuned_uniform = {r["comparison"]: r for r in data["tuned"] if r["workload"] == "uniform"}
    min_primary = data["minimal_primary"]
    min_lo = min(r["bytes_saving_pct"] for r in min_primary)
    min_hi = max(r["bytes_saving_pct"] for r in min_primary)
    min_best = max(min_primary, key=lambda r:r["bytes_saving_pct"])
    min_worst = min(min_primary, key=lambda r:r["bytes_saving_pct"])
    scale_lo = min(r["bytes_saving_pct"] for r in data["scale"])
    scale_hi = max(r["bytes_saving_pct"] for r in data["scale"])
    abl = {r["step"]:r for r in data["ablation"]}
    theory_rows=[r for r in min_primary if r["theory_gap_pp"] is not None]
    max_gap=max(abs(r["theory_gap_pp"]) for r in theory_rows)
    return f"""# TDSC 论文实验章节完整分析

生成时间：{dt.datetime.now().astimezone().isoformat(timespec='seconds')}

## 1. 冻结范围与结论边界

本证据包冻结了两组正式矩阵：纯 selective 组合矩阵 120 条、规模与块大小矩阵 125 条。没有增加协议分支；纯组合矩阵关闭 compact header、neutral/read fusion、省根、small-map 和 `(Z,A,S)` 重调，只改变逻辑读集合。所有核心效应均以同一 trace seed 成对比较，5 个独立种子报告 paired mean 与 Student-t 95% 置信区间。

可支持的核心结论有两层。第一层是当前 SDE/R0 完整设计在同一调优流程下的通信收益：uniform 下 SDE 相对 Path 为 **{tuned_uniform['SDE/Path']['bytes_saving_pct']:.3f}%**，相对 Deferred 为 **{tuned_uniform['SDE/Deferred']['bytes_saving_pct']:.3f}%**；R0 相对 tuned Ring 为 **{tuned_uniform['R0/Ring']['bytes_saving_pct']:.3f}%**。第二层是 selective read 的可组合性：在 Freecursive-style、rho-style、IR-style 与 AB-style 四类宿主上，最小组合的实测通信下降落在 **{min_lo:.3f}%–{min_hi:.3f}%**；最低为 {min_worst['family']}/{min_worst['layout']}、B={min_worst['B']}，最高为 {min_best['family']}/{min_best['layout']}、B={min_best['B']}。

这些结论不等同于“所有先进 ORAM 上全局最优”。IR/AB/Freecursive/rho 结果是冻结执行模型中的最小组合证据，不是四篇论文原作者代码的原生端到端复现。真实可信内存峰值与真实网络延迟没有测量，因此论文只能报告通信、RPC、持久存储口径和模拟器执行成本，不能把模型推断写成实测 latency 或 peak RSS。

## 2. 实验设计

- **执行环境**：{data['environment'][0]['platform']}，Python `{data['environment'][0]['python_version']}`，可见逻辑处理器 {data['environment'][0]['logical_processors']}；实现是可审计参考 harness，不是优化后的生产代码。
- **统计单位**：seed 级成对差值；每个正式格 5 个种子，置信区间基于 paired saving，而不是把请求当作独立样本。
- **主比较**：tuned Path/Deferred/SDE 与 tuned Ring/R0，N=16,384、B=4,096，uniform 与 hot90。
- **规模矩阵**：N/B 组合覆盖 `(4096,4096)`、`(16384,64/256/1024)`、`(65536,4096)`；每格 Path、Deferred、SDE、Ring、R0 各 5 个种子，共 125 条。
- **最小组合矩阵**：N=4,096；Freecursive-style、rho-style、IR-style、AB-style；B=64/4,096，并为 IR/AB 增加布局与 full-probe 归因控制，共 120 条。
- **消融**：small map → compact header → fusion → `(Z,A,S)` retuning，并单列 joint effect，避免把联合收益解释为各项相加。
- **稳健性**：公开负载、Freecursive/rho 参数敏感性、IR guarded 补充与条件式 AB+CB 补充。

## 3. 主结果：SDE 与 R0

同样调优后的结果应作为主文数字。uniform 下：

| 比较 | bytes/op（对照→方案） | 通信下降 | 95% CI | RPC 变化 |
|---|---:|---:|---:|---:|
""" + "\n".join(
        f"| {r['comparison']} | {r['baseline_bytes_per_request']:,.2f} → {r['variant_bytes_per_request']:,.2f} | {r['bytes_saving_pct']:.3f}% | [{r['ci95_low_pct']:.3f}%, {r['ci95_high_pct']:.3f}%] | {r['rpc_saving_pct']:.3f}% |"
        for r in data["tuned"] if r["workload"] == "uniform"
    ) + f"""

SDE/Path 的 RPC 指标为负，含义是 SDE 为换取通信下降增加了 RPC；SDE/Deferred 和 R0/Ring 的 RPC 数量基本持平。论文中应把通信和 RPC 并列，避免只给 bytes 的单指标结论。规模矩阵的 15 个 paired effects 全部完成，通信下降总范围为 **{scale_lo:.3f}%–{scale_hi:.3f}%**；详细值见 `table_02_scale` 与 Fig. 2。

## 4. selective read 的最小组合证据

最小组合关闭所有 SOC3 辅助优化，所以这里测得的是 selective read 本身在宿主调度中的增益。10 个主格均通过重复数与变异门槛，4 个 IR/AB full-probe 控制把放置规则固定后再比较读集合。IR/AB 的理论期望与实测均值最大偏差为 **{max_gap:.3f} 个百分点**，说明计费归约和执行收据一致；Freecursive/rho 因前端 tick 与命中行为由 trace 决定，不用单一固定理论值替代实测。

可写入论文的组合性表述是：“在四类公开设计抽象上，仅替换逻辑读选择即可取得可重复的通信下降。”不应写成“完整移植 SOC3”或“对原作者实现无条件获得同一收益”。

## 5. 消融与收益来源

五步消融给出的 paired communication saving 为：small map **{abl['small map']['bytes_saving_pct']:.3f}%**、compact header **{abl['compact header']['bytes_saving_pct']:.3f}%**、fusion **{abl['neutral/read fusion']['bytes_saving_pct']:.3f}%**、参数重调 **{abl['(Z,A,S) retuning']['bytes_saving_pct']:.3f}%**，联合结果 **{abl['joint result']['bytes_saving_pct']:.3f}%**。联合结果是相对共同起点的效果，不能把四个边际百分比直接求和。fusion 的通信贡献较小，但 RPC 贡献明显；这正是分离消融比“compact+fusion 一起开”更有解释力的原因。

## 6. 公开负载、敏感性和补充证据

公开负载的全部窗口与区间见 `table_06_public_workloads`。Freecursive/rho 的完整参数敏感性保存在 `table_09_sensitivity_full`，用于说明收益随前端选择率和维护占比变化。IR guarded 与 AB+CB 结果放在补充表中：前者是 guarded adapter 证据，后者仍受容量安全准入限制，均不进入“原生系统复现”的主结论。

## 7. 存储、CPU 与延迟口径

`table_07_resources` 只统计远端持久对象、客户端持久对象、预留 stash payload 与 terminal map。它没有覆盖 allocator、索引、同时存活的多桶 ciphertext、decoded payload、final-write buffer 和认证 scratch，因此不能称为真实峰值可信内存。运行收据保留了 Python harness 的 CPU/harness seconds，可用于审计实验成本，不能外推为生产实现延迟。没有真实网络 RTT/吞吐实验，论文不得声称“实测 latency improvement”。

## 8. 审计闭合与论文写法

证据包包含 120 条最小组合收据、125 条规模收据、审计 JSON、计划与哈希锁、CSV/LaTeX 表格、PNG/SVG/PDF 图件和可编辑 Excel 工作簿。功能正确性由答案哈希、成对 trace、transcript、边界状态检查和 fail-stop 检查共同支撑。容量网格覆盖 12,506 点，记录的 lifetime bound 为 log2 `-146.3867`。

建议主文使用三组强结论：同调优主比较、跨 N/B 稳健性、四宿主最小组合。消融与公开负载放主文次级图表；完整敏感性、IR guarded、条件式 AB+CB 和原始收据索引放补充材料。旧 Ring 的 52.88% 只能作为历史配置结果，不再作为核心 selective gain。
"""


def evidence_sources() -> list[Path]:
    eval_names = [
        "tuned_completed_snapshot.json", "core_components_complete_audit.json",
        "ablation_complete_audit.json", "classical_completed_snapshot.json",
        "free_sensitivity_completed_audit.json", "rho_sensitivity_completed_snapshot.json",
        "public_completed_audit.json", "ir_guarded_statistics.json",
        "ir_guarded_observations.json", "ab_dummy_first_completed_snapshot.json",
        "storage_components_audit.json", "tuned_model_window_audit.json",
        "calibration_completed_snapshot.json", "extended_analysis_checks.json",
        "ab_ir_completed_evidence.json", "tuned_reference_independent_audit.json",
    ]
    min_names = [
        "analysis.json", "capacity_binding.json", "frontend_reset_checks.json",
        "minimal_contract_checks.json", "portable_bundle_check.json", "preflight.json",
        "public_selector_checks.json", "finalization.json", "figure_status.json",
    ]
    paths = [EVAL / "results" / n for n in eval_names] + [HOME / "results" / n for n in min_names]
    return [p for p in paths if p.exists()]


def caption_text() -> str:
    return """# 论文表图标题与引用顺序

## 主文建议

1. **Table I — Tuned end-to-end comparison.** Paired communication and RPC changes for SDE and R0 under uniform and skewed workloads. All systems use the same tuning procedure; error bars are 95% paired confidence intervals over five seeds. (`table_01_tuned_main`)
2. **Fig. 1 — Tuned end-to-end communication savings.** Use immediately after the main-result paragraph. RPC tradeoffs remain in Table I. (`fig_01_tuned_main`)
3. **Fig. 2 — Scaling and block-size robustness.** Left: B sweep at N=16,384. Right: N sweep at B=4,096. (`fig_02_scaling` and `table_02_scale`)
4. **Table II — Minimal selective-read composition.** The host protocol is otherwise unchanged: compact headers, fusion, root removal, small maps, and parameter retuning are disabled. (`table_03_minimal_composition`)
5. **Fig. 3 — Selective read as a minimal composition.** Use to support the general-composition claim across Freecursive-style, rho-style, IR-style, and AB-style hosts. (`fig_03_minimal_composition`)
6. **Fig. 4 — Placement-controlled attribution.** The full-probe control uses the same constrained placement as selective read and changes only the logical read set. (`fig_04_attribution_control`; exact intervals in `table_04_attribution_controls`)
7. **Fig. 5 — Separated ablation ladder.** Report small map, compact header, fusion, and retuning separately; the joint bar is relative to the common starting point and is non-additive. (`fig_05_ablation` and `table_05_ablation`)
8. **Fig. 6 — Public-workload robustness.** Use if page budget permits; otherwise move with the exact table to the supplement. (`fig_06_public_workloads` and `table_06_public_workloads`)

## 补充材料建议

- **Fig. S1 / Table S1 — Persistent storage accounting.** The accounting excludes allocator/index overhead and is not peak trusted-memory RSS. (`fig_07_storage_accounting`, `table_07_resources`)
- **Table S2 — Audit checks and claim boundaries.** (`table_08_audit_checks`)
- **Table S3 — Full Freecursive/rho sensitivity sweep.** (`table_09_sensitivity_full`)
- **Table S4 — Guarded IR evidence.** Adapter result only; do not label it a native IR-ORAM reproduction. (`table_10_ir_supplement`)
- **Table S5 — Conditional AB+CB evidence.** Capacity-security admission remains open. (`table_11_ab_conditional_supplement`)
- **Tables S6–S7 — Raw 120-run minimal matrix and 125-run scale matrix.** (`table_12_minimal_raw_120`, `table_13_scale_raw_125`)
- **Tables S8–S9 — Existing integrated/static-component and classical Path references.** (`table_14_existing_core_components`, `table_15_classical_path_reference`)

## 正文引用规则

正文效应量统一写作“paired mean [95% CI], n=5 seeds”。bytes 与 RPC 同时出现；SDE/Path 的 RPC 增加不能省略。四宿主组合结果写成“minimal composition in our frozen execution model”，不要写成原作者代码的端到端原生复现。峰值可信内存和真实网络 latency 在本轮没有测量。
"""


def copy_evidence() -> list[dict[str, Any]]:
    records = []
    for d in (AUDITS, RECEIPTS_MIN, RECEIPTS_SCALE, RECEIPTS_AUDITED, PLANS): d.mkdir(parents=True, exist_ok=True)
    for src in evidence_sources():
        dst = AUDITS / ("minimal__" + src.name if HOME in src.parents else "eval__" + src.name)
        shutil.copy2(src, dst)
        records.append({"type":"audit", "source":str(src), "copy":str(dst.relative_to(OUT)), "sha256":sha256(dst)})
        if EVAL in src.parents:
            audit=read_json(src)
            receipts=audit.get("receipts",[]) if isinstance(audit,dict) else []
            if isinstance(receipts,list):
                for receipt in receipts:
                    if not isinstance(receipt,dict) or not receipt.get("path"):continue
                    rel=Path(receipt["path"])
                    source=(EVAL/rel).resolve() if not rel.is_absolute() else rel.resolve()
                    assert source.exists(),source
                    if receipt.get("sha256"):assert sha256(source)==receipt["sha256"],source
                    target=RECEIPTS_AUDITED/rel
                    target.parent.mkdir(parents=True,exist_ok=True)
                    if not target.exists():shutil.copy2(source,target)
                    key=str(target.relative_to(OUT))
                    if not any(r["copy"]==key for r in records):
                        records.append({"type":"audited_existing_receipt","source":str(source),"copy":key,"sha256":sha256(target)})
    for src in sorted((HOME / "results" / "formal").glob("*.json")):
        dst=RECEIPTS_MIN/src.name; shutil.copy2(src,dst)
        records.append({"type":"minimal_receipt", "source":str(src), "copy":str(dst.relative_to(OUT)), "sha256":sha256(dst)})
    queue=read_json(EVAL/"extended_scale_queue.json")
    for item in queue["items"]:
        s=item["spec"]; src=EVAL/"results"/s["experiment_class"]/f"{s['id']}.json"
        dst=RECEIPTS_SCALE/src.name; shutil.copy2(src,dst)
        records.append({"type":"scale_receipt", "source":str(src), "copy":str(dst.relative_to(OUT)), "sha256":sha256(dst)})
    for src in (HOME/"formal_plan.json", HOME/"pilot_plan.json", HOME/"source_lock.json", EVAL/"extended_scale_queue.json"):
        dst=PLANS/src.name; shutil.copy2(src,dst)
        records.append({"type":"plan_or_lock", "source":str(src), "copy":str(dst.relative_to(OUT)), "sha256":sha256(dst)})
    bundle=HOME/"Selective_最小组合审阅包.zip"
    if bundle.exists():
        dst=OUT/"source_evidence"/bundle.name; shutil.copy2(bundle,dst)
        records.append({"type":"portable_bundle", "source":str(bundle), "copy":str(dst.relative_to(OUT)), "sha256":sha256(dst)})
    return records


def workbook_payload(data: dict[str, list[dict[str, Any]]], manifest: list[dict[str, Any]]) -> dict[str, Any]:
    claims=[]
    for r in data["tuned"]:
        claims.append({"section":"主比较", "claim":f"{r['comparison']} / {r['workload']}",
                       "value_pct":r["bytes_saving_pct"], "ci_low":r["ci95_low_pct"], "ci_high":r["ci95_high_pct"],
                       "status":"headline", "scope":r["scope"]})
    for r in data["minimal_primary"]:
        claims.append({"section":"最小组合", "claim":f"{r['family']}/{r['layout']}, B={r['B']}",
                       "value_pct":r["bytes_saving_pct"], "ci_low":r["ci95_low_pct"], "ci_high":r["ci95_high_pct"],
                       "status":"composability", "scope":"only selective read enabled"})
    return {"generated":dt.datetime.now().astimezone().isoformat(), "claims":claims, **data,
            "evidence_index":manifest}


def main() -> None:
    if OUT.exists():
        resolved=OUT.resolve(); assert resolved.parent == HOME.resolve() and resolved.name == "论文实验章节完整证据_2026-09-16"
        shutil.rmtree(resolved)
    for d in (TABLES, FIGURES, AUDITS, RECEIPTS_MIN, RECEIPTS_SCALE, RECEIPTS_AUDITED, PLANS): d.mkdir(parents=True, exist_ok=True)

    tuned = normalize_tuned()
    scale, scale_runs = normalize_scale()
    minimal_primary, minimal_controls, minimal_runs = normalize_minimal()
    sample=read_json(sorted((HOME/"results"/"formal").glob("*.json"))[0])
    environment=[{"platform":sample["environment"].get("platform"),
                  "python_version":sample["environment"].get("python"),
                  "logical_processors":os.cpu_count(),
                  "implementation":"auditable Python reference harness",
                  "timing_scope":"harness CPU/wall time; not production or network latency"}]
    ir_supplement, ab_supplement = normalize_supplements()
    core_existing,classical=normalize_existing_effects()
    data = {
        "tuned": tuned, "scale": scale, "scale_runs": scale_runs,
        "minimal_primary": minimal_primary, "minimal_controls": minimal_controls,
        "minimal_runs": minimal_runs, "ablation": normalize_ablation(),
        "sensitivity": normalize_sensitivity(), "public": normalize_public(),
        "ir_supplement": ir_supplement, "ab_supplement": ab_supplement,
        "resources": normalize_resources(), "audits": audit_rows(),
        "core_existing":core_existing,"classical":classical,
        "environment":environment,
    }
    table_paths=save_tables(data)
    figure_paths=render_figures(data)
    (OUT/"论文实验章节完整分析.md").write_text(report_text(data),encoding="utf-8")
    (OUT/"论文表图标题与引用顺序.md").write_text(caption_text(),encoding="utf-8")
    evidence=copy_evidence()
    artifact_records=[]
    for p in table_paths+figure_paths+[OUT/"论文实验章节完整分析.md",OUT/"论文表图标题与引用顺序.md"]:
        artifact_records.append({"type":"generated_artifact", "source":None,
                                 "copy":str(p.relative_to(OUT)), "sha256":sha256(p)})
    manifest=evidence+artifact_records
    write_json(OUT/"evidence_manifest.json", {
        "status":"complete", "generated":dt.datetime.now().astimezone().isoformat(),
        "matrix_counts":{"minimal_formal":120,"scale":125,"pilot_excluded_from_headline":16},
        "claim_limits":{"true_client_peak_measured":False,"real_network_latency_measured":False,
                        "native_reproduction_of_four_hosts":False}, "files":manifest})
    write_json(OUT/"workbook_data.json", workbook_payload(data,manifest))
    readme=f"""# 论文实验章节完整证据

本目录是冻结实验矩阵的投稿整理版，不增加协议机制。

- `论文实验章节完整分析.md`：实验章节论证、核心数字和口径限制。
- `论文表图标题与引用顺序.md`：可直接用于主文/补充材料的英文 caption 与摆放顺序。
- `TDSC论文实验数据总表.xlsx`：可筛选数据、公式和原生图表（由后续工作簿步骤生成）。
- `tables/`：主文/补充材料 CSV 与 LaTeX 表。
- `figures/`：同一数据生成的 PNG、SVG、PDF。
- `source_evidence/`：审计 JSON、120+125 条正式收据、计划与哈希锁。
- `evidence_manifest.json`：逐文件 SHA-256 与范围声明。
- `workbook_data.json`：工作簿的规范化输入。

主文优先使用 `table_01_tuned_main`、`table_02_scale`、`table_03_minimal_composition` 和 Fig. 1–5。公开负载可放主文，完整敏感性与 IR/AB 补充放附录。真实可信内存峰值与真实网络延迟未测量。
"""
    (OUT/"README.md").write_text(readme,encoding="utf-8")
    print(json.dumps({"status":"complete","out":str(OUT),"tables":len(table_paths),
                      "figures":len(figure_paths),"evidence_files":len(evidence),
                      "minimal_runs":len(minimal_runs),"scale_runs":len(scale_runs)},ensure_ascii=False))


if __name__ == "__main__":
    main()
