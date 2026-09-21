# 论文表图标题与引用顺序

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
