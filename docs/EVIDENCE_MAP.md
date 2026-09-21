# Claim-to-evidence map (r8.6)

Below, `E` abbreviates `workspace/TDSC_SOC3_审阅与投稿方案_2026-09-15/论文带宽实验_2026-09-16`
and `M` abbreviates `workspace/TDSC_SOC3_审阅与投稿方案_2026-09-15/Selective_通用组合与投稿实验准备_2026-09-16`.

| Evidence | Manuscript data | Source and replay |
|---|---|---|
| Tuned core comparison | table_01_tuned_main.csv | E/formal_tuned_plan.json, E/results; audit_tuned_reference.py |
| Scale and block-size slices | table_02_scale.csv; table_13_scale_raw_125.csv | M/论文实验章节完整证据_2026-09-16/source_evidence/receipts_scale_125; E/specs and E/src |
| Minimal IR/AB/frontend reuse | table_03_minimal_composition.csv; table_12_minimal_raw_120.csv | M/formal_plan.json; M/results/formal; M/src/run_minimal.py and run_frontend_minimal.py |
| Placement attribution | table_04_attribution_controls.csv | M full-probe vs selective arms; check_minimal_contract.py |
| Auxiliary optimization ablation | table_05_ablation.csv | E/formal_ablation_plan.json; audit_completed_ablation.py |
| Public workload windows | table_06_public_workloads.csv | E/datasets, E/formal_public_plan.json, E/src/public_trace.py and audit_completed_public.py |
| Accounted resources (not true peak memory) | table_07_resources.csv | E/src/audit_storage_components.py; saved storage receipts |
| Audit checks | table_08_audit_checks.csv | SOC3 audit receipts; M/results/minimal_contract_checks.json and frontend_reset_checks.json |
| Sensitivity and conditional studies | table_09_sensitivity_full.csv through table_11_ab_conditional_supplement.csv | Saved results in E; scope and failed runs retained |
| Core/component raw values | table_14_existing_core_components.csv | E/src/audit_completed_core_components.py |
| Path certified reference | table_15_classical_path_reference.csv | E/formal_classical_reference_plan.json; audit_tuned_reference.py |
| Recorded environment | table_16_environment.csv | Original measurement receipts; not the current packaging host |
| Fusion and parameterized proofs | paper_data/data/audit_receipts/core_*_proof.md | workspace/SOC3_audit_2026-09-15/proofs and audit |
| Host interface and composition | composition_contract.md, host_contract_checks.json, frontend_reset_checks.json, frontend_schedule_pairs.json in paper_data/data/audit_receipts | M/src; M/tools/check_frontend_reset.py; original per-arm frontend schedule digests |

All table filenames above are under `paper_data/data/`. The paper's
`evidence_index.json` is preserved byte-for-byte, including historical absolute
source paths. `provenance/source_inventory.json` maps the packaged files to their
original workspace-relative locations; do not try to access the author's D: drive.

The final evidence directory also contains figures, their input tables, and the
historical workbook. Older reports and the richer IR-DWB/AB-DeadQ/CB prototypes
are retained as exploratory context, not additional headline evidence. Formal
and pilot specifications, failures, and incomplete pressure runs remain separate.
