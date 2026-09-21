# Reproduction guide

## Reference environment

Use Python 3.12 and UTF-8 (`python -B -X utf8`). Core execution uses the Python
standard library. Optional plot regeneration uses matplotlib; legacy spreadsheet
generation used a workstation-specific JavaScript library and is not part of the
portable command set. CSV data and already-generated figures are included.
The recorded environments of the original runs are in table_16_environment.csv.
Measurement replay and statistics were validated on Windows. Original per-run
identity dictionaries use native Windows path separators; on Linux those string
keys can differ even when file contents match. This release preserves the original
hash-bound receipts and does not silently normalize them. Use Windows for the
validated measurement replay, and Linux/WSL for full numerical recomputation.
Cross-platform measurement replay is not part of the validated release scope.

Full numerical recomputation requires Linux/WSL, g++ and OpenMP:

```sh
python -B -X utf8 tools/reproduce.py core-full --out ../csoram-core-full
```

This invokes the original full-joint kernel and rational small-domain oracle,
including mutation and thread consistency checks. Historical reference execution
used g++ 9.5.0 and Python 3.12.3. Floating-point endpoints are checked exactly;
different toolchains may require a reviewed new numerical receipt. Do not weaken
the comparisons or reseal a certificate to make verification pass. Full numerical
rebuilding is substantially more expensive than `core-quick`.

## Rerunning an individual measurement

The original specs are executable inputs. For example:

```sh
python -B -X utf8 tools/reproduce.py replay-spec --out ../csoram-one-run --driver "submission_study_2026-09-15/selective_composition_2026-09-16/src/run_minimal.py" --spec "submission_study_2026-09-15/selective_composition_2026-09-16/specs/pilot/MIN_pilot_AB_depth_selective_B64_seed101.json"
```

Use `run_minimal.py` for minimal IR/AB specs and `run_frontend_minimal.py` for
minimal frontend specs. For the complete minimal matrix, enumerate the 120 specs
in its `formal_plan.json`, choosing the corresponding driver by family. Preserve
all seeds, initialization, warmup and measurement lengths. Do not replace formal
specs with smoke settings when reporting reproduced results.

For the broader bandwidth matrix, original plans and their dispatchers are in
the bandwidth experiment directory. Several execution revisions exist
(`run_core.py`, `run_fast.py`, `run_bulk_scale.py` and frontend drivers); use the
driver recorded by that plan/receipt. Merely switching to the fastest driver
changes source identity. Original code contents are preserved so the existing per-run hashes
and equivalence checks remain meaningful.

Historical dispatch scripts include machine-specific orchestration. Prefer the
portable single-spec wrapper or invoke a driver in a disposable workspace copy.
Do not execute old `seal`, `freeze`, `prepare`, `finalize`, or packaging scripts to
validate the frozen artifact: they are maintainer tools and may rewrite inputs.

## Original audit manifest and the public subset

This public release excludes external-paper snapshots and redundant archives.
The original `BUNDLE_MANIFEST.json` is retained, unmodified, for provenance, so
the old all-files `audit/run.py --mode verify` is NOT the public entry point.
Use `tools/reproduce.py`: it checks every release file, checks retained SOC3 files
against the original manifest, lists declared omissions, and calls the original
audit functions. Protocol code, numerical kernels, grids, original contracts,
and numerical witnesses are unchanged. This is not a verification of omitted
source-paper PDFs and not an external human audit.

## Public inputs

Public workload windows are derived from UMass repository Financial1 and
WebSearch1 traces. `datasets/download_receipt.json` records original URLs/hashes;
the processed windows and transform scripts are included. To re-extract from
original archives, use the verified downloader, then place the downloaded files
under `datasets/raw` in a disposable workspace copy. Preserve the download
receipt and attribution. Network access is only needed for that optional step.

## What the release validation covers

Read `provenance/validation_summary.json` for the actual commands run while
preparing this release. Hash validation, saved-result recomputation and small
encrypted replays are distinct from rerunning the complete matrix. Historical
full numerical witnesses are included; whether the expensive numerical rebuild
was rerun for this packaging step is reported explicitly.
