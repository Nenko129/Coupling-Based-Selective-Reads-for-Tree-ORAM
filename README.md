# Coupling-Based Selective Reads for Tree ORAM

Experimental artifact accompanying the r8.6 submission by Siyuan Ma, Taoteng Liao,
Xinyuan Huang, Tingquan Li, and Yanlong Wen (corresponding author).

This repository contains the experimental implementations, fixed specifications,
input traces, original measurements, numerical certificates, verification tools,
and the 16 CSV tables used by the manuscript. It documents a reusable selective
read/placement principle, with SDE-Path and R0-Ring instantiations and restricted
IR/AB components and Freecursive-style/ρ-style adapters.

## Start here

Windows with Python **3.12** is the validated measurement-replay environment. The verification and replay commands
below use only its standard library. Run from this directory:

```sh
python -B -X utf8 tools/reproduce.py verify
python -B -X utf8 tools/reproduce.py smoke --out ../csoram-smoke
python -B -X utf8 tools/reproduce.py audit-results --out ../csoram-statistics
python -B -X utf8 tools/reproduce.py core-quick --out ../csoram-core-quick
```

Every output directory must be new and outside this repository. Replay and
statistics commands reconstruct the historical workspace there before executing historical tools,
so original results are not overwritten. Allow roughly 1 GB of free disk space
per copy. On Windows, use a short checkout path (for example `D:/csoram`) because
historical paths are restored only in the external replay workspace.
Use Linux/WSL for the optional numerical rebuild. Historical measurement receipts
contain Windows path strings in source-identity dictionaries; the measurement
replay/statistics commands are validated on Windows, not claimed portable across
operating systems. See the reproduction guide.

- `verify`: hashes the release and checks retained SOC3 files against the original
  frozen manifest; explicitly reports excluded external snapshots.
- `smoke`: checks host coupling and frontend resets, then reruns two encrypted
  pilot cases and compares code hashes, input traces, answers, bytes, and RPCs
  with their original receipts. It is a small reproducibility check, not a rerun
  of the complete experimental matrix.
- `audit-results`: independently recomputes core/component, ablation, tuned and
  certified-reference accounting plus minimal-composition statistics from saved
  results. This checks recorded measurements, not fresh executions of all runs.
- `core-quick`: executes fusion and integrated-artifact checks, exact Poisson
  seed validation, certificate boundary rejection, and original source identity
  checks using the original audit functions.

## English file and directory names

All published paths use ASCII English names. Historical source code, receipts,
and proof notes retain their exact contents and original SHA256 identities.
`provenance/path_migration.json` records the reversible old/new path mapping.
Use `tools/reproduce.py` instead of executing historical drivers in place: it
restores their original layout only in an external, disposable workspace.
Two redundant historical review ZIPs were omitted; their extracted experiments
and receipts remain available. See `docs/PATH_MIGRATION.md`.

## Contents

| Location | Contents |
|---|---|
| `paper_data/data/` | Exact r8.6 CSV tables and claim-to-evidence index |
| `docs/EVIDENCE_MAP.md` | Where manuscript results come from |
| `docs/REPRODUCING.md` | Full run entry points, certificate rebuilding, dependencies |
| `workspace/SOC3_audit_2026-09-15/` | Frozen protocol, fusion, certificate kernels, proofs and audit receipts |
| `workspace/selective_oram_final_chain_2026-09-11/` | Original reduction and authenticated implementation dependencies |
| `workspace/submission_study_2026-09-15/bandwidth_experiments_2026-09-16/` | Main experiment engines, specifications, traces, receipts and historical diagnostics |
| `workspace/submission_study_2026-09-15/selective_composition_2026-09-16/` | Minimal IR/AB and frontend experiments; final paper evidence tables/figures |
| `provenance/` | Original source hashes, declared omissions, packaging validation |
| `MANIFEST.json` | SHA256 identity of every delivered file except this manifest |

## Interpretation and scope

The primary measured metric is **authenticated application-frame communication**
in an in-process client/server harness. TCP/TLS traffic, real network latency,
production CPU speedup, and true enclave peak memory were not measured. Historical
process timing is not client-only deployment performance.

IR/AB reuse results concern the specified static allocation components.
Freecursive/ρ reuse concerns declared frontend adapters and their schedule
contracts; it is not a complete native-system security claim. The Z7/A6 numerical
certificate covers h ≤ 24 (L ≤ 23) within its stated parameters.

Historical failed, pilot, pressure, and exploratory runs are retained to avoid
selective reporting. They must not be pooled into formal averages. Old READMEs
describe the state at their writing date; the r8.6 tables and the evidence map
are the guide to the submitted claims. The detailed supplementary proofs remain
part of the manuscript submission; original proof notes are also included here.

## Public trace provenance

Synthetic input traces and the processed public workload windows used in the
experiments are included. Original third-party trace archives and source-paper
PDFs are excluded. Their URLs, attribution, and original hashes are retained.
See `THIRD_PARTY_NOTICES.md` and the optional verified downloader:

```sh
python -B -X utf8 tools/fetch_trace_sources.py --out ../csoram-trace-sources
```

## Citation, contact, and licensing

See `CITATION.cff`. This is a submission artifact; it has no assigned publication
DOI. Contact: Yanlong Wen, `wenyl@nankai.edu.cn`.

No new software license is selected by this packaging step. Existing notices
remain in force; authors should choose the intended code/data licenses when
publishing. See `LICENSE_STATUS.md`. The manuscript repository URL will be added
after the authors provide the public repository address.
