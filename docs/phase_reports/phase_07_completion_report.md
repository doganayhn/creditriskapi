# PHASE 7 COMPLETION REPORT

## 1. Objective

Implement Phase 7 only: frozen XGBoost raw-margin Tree SHAP, signed feature lineage/aggregation, diagnostic local drivers and a versioned internal score with mathematically guarded additive score points. Complete the revised scope with TRAIN OOF score statistics unavailable under the owner's explicit no-retraining instruction.

## 2. Pre-Implementation Repository State

HEAD: `0f9b567db00f5d2dc3121e8c83ff59f79e8e7ca4`. Branch: `main`. Initial Git status was clean. Phase 6 was committed as `0f9b567 feat: add calibration and downstream model selection`. Phases 1–6 were COMPLETED; Phases 7–10 were NOT_STARTED. No new commit was created.

## 3. Documentation Reviewed

Reviewed AGENTS.md, PROJECT_RULES.md, ROADMAP.md, PHASE_STATUS.md, README.md, CHANGELOG.md; domain/problem definition and glossary; dataset decision/card, physical/quality contracts; leakage policy, feature engineering/modeling dataset; architecture/model governance; baseline, XGBoost and calibration reports; ADRs 001–005; report policy and historical Phase-1–6 context, with the latest Phase-6 calibration/governance outcome checked against the committed metadata. Reconciled the Phase-7 prompt with the explicit owner clarification on unavailable TRAIN OOF scores.

## 4. Selected Model / Calibration Contract

| Contract | Verified value |
| --- | --- |
| Dataset SHA-256 | `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933` |
| Feature engineering | `financial_features_v1` |
| Preprocessing | `train_median_scale_onehot_v1` |
| Preprocessor SHA-256 | `e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4` |
| Selected model | XGBoost, `xgboost-challenger-1.0.0` |
| Model artifact SHA-256 | `2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef` |
| Calibration | XGBoost `xgboost-calibration-1.0.0`, identity |
| Calibrator binary | None; identity path/hash are null |
| Transformed features | 103, exact Phase-3 names/order |
| TEST | Sealed; test_set_evaluated=false |

`XGBOOST_SELECTED_FOR_DOWNSTREAM` is unchanged. Logistic calibration remains identity as well. No selected model retraining, parameter tuning, calibration reselection or threshold optimization occurred.

## 5. SHAP Implementation

SHAP 0.51.0; public `shap.TreeExplainer`, `model_output="raw"`, `feature_perturbation="tree_path_dependent"`, `approximate=False`. Frozen training path counts supply background semantics; no background rows or explainer binary. Explained 4,500 VALIDATION rows × 103 transformed features, with dense materialization preserving XGBoost zero semantics. Version: `xgboost-shap-1.0.0`.

## 6. Raw Margin / Probability Validation

`sigmoid(raw_margin) ≈ raw_probability`. Maximum absolute error: 7.20322632652e-08; mean: 6.99643408433e-09. PASS against 1e-7 absolute tolerance. The native margin and positive-class probability were obtained independently.

## 7. SHAP Additivity Validation

`base + sum(SHAP) ≈ native raw margin`. Maximum absolute residual 4.25636244472e-06; mean 7.48812189057e-07; p50 5.16367435921e-07; p95 2.09110512515e-06; p99 2.653722986e-06. PASS against 1e-5. Independent assertions supplement SHAP's own check. Sigmoid of the SHAP-reconstructed margin also passed the documented link-error bound.

## 8. Feature Lineage Validation

103 unique transformed features → 45 source inputs → 7 families. Missing mappings: 0; identifier/target/demographic leakage count: 0. Exact Phase-3 trace reused. Source and family signed local totals preserve transformed totals; both maximum measured residuals were 0. Sources include engineered inputs; raw canonical origins remain traceable in the Phase-3 manifest.

## 9. Global SHAP — Transformed Features

| Rank | Feature | Mean absolute margin SHAP |
| --- | --- | ---: |
| 1 | `numeric__months_with_documented_delay` | 0.326189915 |
| 2 | `numeric__max_documented_delay` | 0.257720088 |
| 3 | `numeric__recent_documented_delay_flag` | 0.221549400 |
| 4 | `numeric__bill_amount_std` | 0.073593053 |
| 5 | `numeric__credit_limit` | 0.073320612 |
| 6 | `repayment__repayment_status_2005_09_status_2` | 0.073225777 |
| 7 | `repayment__repayment_status_2005_09_status_1` | 0.063872836 |
| 8 | `numeric__bill_amount_2005_09` | 0.056085503 |
| 9 | `numeric__bill_to_limit_2005_08` | 0.055891157 |
| 10 | `numeric__payment_amount_2005_04` | 0.054120229 |

## 10. Global SHAP — Source Features

| Rank | Feature | Mean absolute margin SHAP |
| --- | --- | ---: |
| 1 | `months_with_documented_delay` | 0.326189915 |
| 2 | `max_documented_delay` | 0.257720088 |
| 3 | `recent_documented_delay_flag` | 0.221549400 |
| 4 | `repayment_status_2005_09` | 0.153144796 |
| 5 | `bill_amount_std` | 0.073593053 |
| 6 | `credit_limit` | 0.073320612 |
| 7 | `bill_amount_2005_09` | 0.056085503 |
| 8 | `bill_to_limit_2005_08` | 0.055891157 |
| 9 | `payment_amount_2005_04` | 0.054120229 |
| 10 | `bill_to_limit_2005_09` | 0.053883630 |

## 11. Global SHAP — Feature Families

| Rank | Feature | Mean absolute margin SHAP |
| --- | --- | ---: |
| 1 | `delay_summary` | 0.713980984 |
| 2 | `payment_amount` | 0.207690520 |
| 3 | `bill_to_limit` | 0.190300417 |
| 4 | `repayment_status` | 0.157955354 |
| 5 | `bill_amount` | 0.145616367 |
| 6 | `credit_limit` | 0.073320612 |
| 7 | `payment_to_limit` | 0.040828456 |

Magnitude is computed after signed local aggregation, not by summing child mean absolute importance. Full artifacts also contain mean signed contribution, normalized magnitude and deterministic rank. The seven-family explanation grouping is separately documented and does not rewrite historical native-gain grouping.

## 12. SHAP vs Native XGBoost Gain

Top-ten overlap: 5/10. Shared: `numeric__max_documented_delay`, `numeric__months_with_documented_delay`, `numeric__recent_documented_delay_flag`, `repayment__repayment_status_2005_09_status_1` and `repayment__repayment_status_2005_09_status_2`. Gain measures training split-loss improvement; SHAP magnitude describes validation predictions under its perturbation semantics. Diagnostic comparison only; no feature/model selection changed. Optional rank correlation was not calculated.

## 13. Local Diagnostic Reason-Code Design

Sum signed transformed contributions into sources first. Return up to five positive risk-increasing and five negative risk-decreasing source drivers; descending magnitude within direction, ascending source-name tie break, zero contributions omitted. Full 45-source values remain available in memory because top-k excerpts alone do not reconstruct the full margin. Positive risk SHAP lowers score points. The schema carries model diagnostics without causal or regulatory adverse-action claims.

## 14. Probability / SHAP Semantics

`base margin + sum(SHAP margin contributions) ≈ raw model margin`. `sigmoid(raw margin) ≈ raw probability`. Current identity calibration makes `raw probability = reported probability`. SHAP values do NOT directly sum to raw probability or calibrated/reported probability. Native floating-point errors are reported rather than hidden.

## 15. Internal Risk Score Specification

Version `internal-risk-score-1.0.0`. Base score 600; base good:bad odds 50:1; PDO 20; factor 28.85390081777927; offset 487.1228762045055; epsilon 1e-12.

`S = offset + factor * ln((1-p)/p)`, using reported probability. Higher probability lowers score. Canonical score is continuous float64; optional nearest-integer display uses ties to even. Protect logarithms only with [epsilon, 1-epsilon], retain original probability and report clipping. No cosmetic score range, FICO equivalence, regulatory score or business policy.

## 16. Internal Score Mathematical Validation

50:1 odds maps to 600; 100:1 maps to 620; doubling adds exactly 20. Inverse ranking including ties passed on VALIDATION. `p = sigmoid((offset-S)/factor)` maximum round-trip error 4.4408920985e-16. AUC(p) = AUC(-score) = 0.7843044036157966, difference 0. Clipping count 0, rate 0. Monotonicity is strict on the unclipped domain; protected extreme tails may tie.

## 17. Internal Score Distribution

TRAIN OOF: **unavailable by explicit owner instruction**. Phase 6 retained aggregate OOF statistics only; exact nonlinear score statistics cannot be recovered without prohibited retraining. No in-sample TRAIN replacement was calculated.

VALIDATION actual statistics follow; std uses ddof=0 and quantiles use linear interpolation.

| Statistic | VALIDATION |
| --- | ---: |
| count | 4500.000000000 |
| mean | 531.965994162 |
| std | 32.514932554 |
| min | 434.265002489 |
| p01 | 450.022252303 |
| p05 | 462.192553232 |
| p10 | 477.538079919 |
| p25 | 515.908897069 |
| p50 | 538.732020518 |
| p75 | 555.132330983 |
| p90 | 568.334114236 |
| p95 | 573.737744033 |
| p99 | 582.518578344 |
| max | 592.724536947 |
| probability_clipping_count | 0.000000000 |
| probability_clipping_rate | 0.000000000 |

## 18. Score Decile Analysis

| Decile | N | Score min | Score max | Mean score | Mean reported PD | Observed default rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 450 | 568.381893 | 592.724537 | 574.963723 | 0.046032 | 0.040000 |
| 2 | 450 | 559.119492 | 568.328806 | 563.280623 | 0.066851 | 0.053333 |
| 3 | 450 | 551.568586 | 559.099719 | 555.266907 | 0.086337 | 0.097778 |
| 4 | 450 | 544.900646 | 551.527957 | 548.301918 | 0.107306 | 0.102222 |
| 5 | 450 | 538.746625 | 544.899692 | 541.783068 | 0.130913 | 0.146667 |
| 6 | 450 | 531.863720 | 538.717416 | 535.476678 | 0.157849 | 0.180000 |
| 7 | 450 | 522.477117 | 531.857029 | 527.631827 | 0.197604 | 0.206667 |
| 8 | 450 | 507.657330 | 522.470813 | 515.744772 | 0.271462 | 0.277778 |
| 9 | 450 | 477.541357 | 507.618544 | 496.193998 | 0.423490 | 0.422222 |
| 10 | 450 | 434.265002 | 477.508588 | 461.016428 | 0.707842 | 0.684444 |

All ten bins contain 450 rows; total 4,500. Stable descending-score sort breaks exact ties by original row position, then forms equal-count bins without duplication. Decile 1 has highest scores/lowest modeled risk; decile 10 has lowest scores/highest modeled risk. Rates increase in this sample, but perfect observed monotonicity is not required. These are diagnostic sample deciles, not risk bands.

## 19. Phase-6 Technical Threshold Equivalent

Frozen probability threshold 0.21430689096450806 maps to technical reference score 524.6086295466075. Source: `phase6_train_oof_max_ks_probability_threshold`. Read unchanged from Phase 6; no new optimization. This is explicitly NOT a business cutoff or underwriting decision.

## 20. SHAP → Score-Point Decomposition

With binary logistic output and identity calibration, `ln((1-p)/p) = -margin`, so `score = offset - factor * margin`.

`score_base = offset - factor * base_margin`; `score_point_i = -factor * shap_i`. Thus `score_base + sum(score_points) ≈ continuous score`. Positive default-risk SHAP gives negative points.

Maximum absolute score residual at transformed, source and family levels: 0.000121609856023 points, PASS against 1e-3. Mean residuals: transformed 2.17157377102e-05, source 2.17157377108e-05, family 2.17157377107e-05. Algebra is exact under the assumptions; native float32 probability/margin arithmetic produces the measured residuals.

## 21. Non-Identity Calibration Guard

The score decomposition method returns `score_point_decomposition_supported=false` without additive point arrays when calibration is non-identity, output is not raw margin, objective is not binary logistic or probability clipping occurs. V1 parameters are enforced. Synthetic tests confirm raw-margin SHAP remains usable and score-from-reported-probability remains possible independently. The current frozen local/CLI contract fails clearly on changed calibration until a new versioned integration is implemented; no unsupported approximation is returned.

## 22. Synthetic Local Explanation Validation

SYNTHETIC / DEMONSTRATION ONLY. Three fabricated 19-financial-field records: regular payments, recent documented delay and larger statements. All passed the frozen local explanation path and 45-source score reconstruction. Maximum synthetic score residuals: regular payments 2.70405007541e-6, recent delay 8.15800541432e-6, larger statements 4.33672248619e-5 points. They are not real people or copied validation rows; only synthetic pass/count/residual metadata was saved.

## 23. Test Set Status

TEST SET WAS NOT EVALUATED.

TEST SET REMAINS SEALED.

No TEST probability, SHAP, internal score, reason code or model performance metric was calculated. The required existing preparation command performs structural split/finite-matrix checks only. Phase-7 consumption discards TRAIN/TEST before feature transformation; synthetic isolation tests poison both branches to detect access.

## 24. Files Created

- `configs/explainability.yaml`
- `data/metadata/explainability_manifest.json`
- `data/metadata/internal_score_manifest.json`
- `data/metadata/internal_score_summary.json`
- `data/metadata/score_decile_analysis.csv`
- `data/metadata/shap_global_importance.json`
- `docs/decisions/006-explainability-and-internal-score.md`
- `docs/explainability_report.md`
- `docs/internal_risk_score.md`
- `docs/phase_reports/phase_07_completion_report.md`
- `src/credit_risk/explainability/__init__.py`
- `src/credit_risk/explainability/aggregation.py`
- `src/credit_risk/explainability/contract.py`
- `src/credit_risk/explainability/local.py`
- `src/credit_risk/explainability/reason_codes.py`
- `src/credit_risk/explainability/run.py`
- `src/credit_risk/explainability/score.py`
- `src/credit_risk/explainability/shap_explainer.py`
- `tests/test_explainability.py`

## 25. Files Modified

- `CHANGELOG.md`
- `PHASE_STATUS.md`
- `README.md`
- `ROADMAP.md`
- `docs/architecture.md`
- `docs/model_governance.md`
- `pyproject.toml`
- `src/credit_risk/modeling/contract.py`

The shared modeling adapter adds an optional validation-only path; its default historical behavior remains unchanged. No Phase-3 feature source or historical model/calibration implementation was altered.

## 26. Aggregate Metadata Artifacts

Five outputs under `data/metadata/`: explainability_manifest.json (versions/lineage/numerical validation), shap_global_importance.json (all transformed/source/family aggregates), internal_score_manifest.json (formula/identities/guards/threshold), internal_score_summary.json (VALIDATION distribution and explicit TRAIN OOF unavailability), score_decile_analysis.csv (ten aggregate VALIDATION rows). All record test_set_evaluated=false. No duplicate optional summary, real row-level artifacts or explainer binary.

## 27. Tests Executed

```powershell
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m credit_risk.explainability.run
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed artifacts
git diff -- docs/phase_reports/phase_01_completion_report.md
git diff -- docs/phase_reports/phase_02_completion_report.md
git diff -- docs/phase_reports/phase_03_completion_report.md
git diff -- docs/phase_reports/phase_04_completion_report.md
git diff -- docs/phase_reports/phase_05_completion_report.md
git diff -- docs/phase_reports/phase_06_completion_report.md
git diff -- data/metadata/baseline_model_manifest.json
git diff -- data/metadata/xgboost_model_manifest.json
git diff -- data/metadata/xgboost_search_results.csv
```

Also executed `.venv\Scripts\python.exe -m pytest tests/test_explainability.py -q`, dependency installation/checks, repeated Phase-7 CLI with byte-hash comparison, all-existing-metadata diff and nothing-staged checks. No historical modeling/calibration CLI was rerun in Phase 7.

## 28. Test Results

Final full suite: **269 passed, 0 failed, 0 skipped, 0 warnings**, 53.02 seconds. Includes 37 Phase-7 cases, including actual frozen-model VALIDATION integration. Targeted initial run: 30 passed / 1 failed (empty score input accepted); fixed explicit empty-input rejection, then 31/31 passed before six further cases were added. No failure remains.

`pip check`: No broken requirements found. Required download/preparation/explainability commands exited 0. `git diff --check` passed.

Exploratory SHAP 0.50.0 dry-run dependency resolution failed on Python 3.14 due to unavailable pinned llvmlite, without environment mutation. SHAP 0.51.0 installed successfully while preserving the existing numerical dependencies and Python >=3.11 project minimum; actual integration passed.

## 29. Real-Data Integration Validation

Verified UCI workbook SHA-256 and 30,000-row identity, unchanged Phase-3 feature/preprocessor artifacts, frozen model/calibration identities, 4,500 × 103 validation explanations, finite SHAP/score results and all reconstruction tolerances. Required preparation refitted/reproduced only the existing TRAIN preprocessing contract and preserved its artifact/metadata; the Phase-7 CLI itself performs no fitting. All nine Phase-6 XGBoost validation probability metrics matched exactly. No model tuning, training, calibration changes or TEST predictive evaluation.

## 30. Determinism / Reproducibility Validation

Repeated the final Phase-7 CLI with unchanged inputs, code, artifacts, configuration and runtime. All five aggregate outputs were **byte-identical**, including global ranks, numerical residuals, score summary/deciles, threshold score and manifests. No real row-level SHAP/score/reason files were persisted between runs. JSON rejects nonfinite values, keys are sorted and unchanged files retain content; CSV order/tie policy is deterministic. Reproducibility is verified on this runtime, not guaranteed across hardware/package changes.

## 31. Data / Git Privacy Validation

`git ls-files data/raw data/interim data/processed artifacts` returned only four .gitkeep placeholders. No real row-level SHAP, per-customer score, per-customer reason codes or TEST predictive outputs are tracked or newly persisted locally. Existing raw XLS and model/preprocessor binaries remain ignored. Phase-7 outputs are aggregate JSON/CSV only. Historical local Phase-6 tooling/logs were left untouched.

## 32. Known Limitations

Historical/static Taiwan credit-card data; no true OOT validation or invented regulatory/12-month horizon. Reused development validation does not establish generalization. SHAP is noncausal and correlated-feature attribution depends on the specified perturbation semantics. No fairness or regulatory explainability claim. The internal score is project-specific, not FICO or a lending policy. TRAIN OOF score distribution is unavailable. TEST evaluation remains pending.

## 33. Deviations From Prompt

The owner explicitly instructed: “Keep the no-retraining rule; report TRAIN OOF score statistics as unavailable and complete the other Phase 7 work.” Therefore the original TRAIN OOF score-summary criterion is shown unchecked and explicitly waived below; no synthetic or in-sample replacement is presented as OOF. All remaining requested Phase-7 scope is completed. No other material scope deviation.

## 34. Risks / Technical Debt

OOF score distribution cannot be reconstructed exactly from aggregate probability statistics. A future authorized experiment could calculate aggregate score diagnostics while OOF vectors exist in memory. Frozen artifacts require matching numerical runtime versions; the optional real-model test skips clearly if local ignored prerequisites are absent (it ran and passed here). Float32 native outputs require the stated numerical tolerances. Future non-identity calibration needs explicit consumer integration and cannot silently inherit additive score points. Seven explanation families refine historical gain grouping without changing that historical record. No production or compliance controls are implied.

## 35. Phase-8 Recommendations

Recommendations only: preserve independent model, calibration, explainability and score identities; expose declared units and unsupported-decomposition flags clearly; use trusted artifacts and privacy-aware audit design. Define any business policy separately with owner-supplied requirements. Phase 8 has NOT started; no API, PostgreSQL or lending-decision logic was implemented.

## 36. Reproduction Commands

With the existing trusted frozen model/preprocessor and current runtime:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m credit_risk.explainability.run
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
```

The explanation CLI fails on missing/mismatched frozen artifacts rather than training replacements. Do not rerun baseline, challenger or calibration CLIs merely to reproduce Phase 7.

## 37. Git Status

```text
 M CHANGELOG.md
 M PHASE_STATUS.md
 M README.md
 M ROADMAP.md
 M docs/architecture.md
 M docs/model_governance.md
 M pyproject.toml
 M src/credit_risk/modeling/contract.py
?? configs/explainability.yaml
?? data/metadata/explainability_manifest.json
?? data/metadata/internal_score_manifest.json
?? data/metadata/internal_score_summary.json
?? data/metadata/score_decile_analysis.csv
?? data/metadata/shap_global_importance.json
?? docs/decisions/006-explainability-and-internal-score.md
?? docs/explainability_report.md
?? docs/internal_risk_score.md
?? docs/phase_reports/phase_07_completion_report.md
?? src/credit_risk/explainability/__init__.py
?? src/credit_risk/explainability/aggregation.py
?? src/credit_risk/explainability/contract.py
?? src/credit_risk/explainability/local.py
?? src/credit_risk/explainability/reason_codes.py
?? src/credit_risk/explainability/run.py
?? src/credit_risk/explainability/score.py
?? src/credit_risk/explainability/shap_explainer.py
?? tests/test_explainability.py
```

Historical Phase-1–6 reports and Phase-4/5 experiment metadata have empty diffs; all existing tracked data/metadata files are unchanged. No customer-level output is added. Binaries remain ignored. Nothing staged. HEAD remains the Phase-6 commit; no commit was created.

## 38. Documentation Status

README, ROADMAP, PHASE_STATUS, CHANGELOG, architecture and model governance match implemented Phase 7. Added explainability report, internal-score specification, ADR 006 and this completion report. Phase 7 is COMPLETED under the explicit OOF-summary scope clarification; Phase 8 and Phases 9–10 remain NOT_STARTED. Historical completion reports are unchanged. Four independent model/calibration/explainability/score identities are documented.

## 39. Acceptance Criteria Checklist

Original Section-74 criteria copied below: 102 completed, one explicitly waived by the owner. The unchecked OOF item records unavailable data truthfully and does not block completion of the owner-revised scope.

- [x] Required repository documentation was reviewed.
- [x] Phase 6 is committed.
- [x] Repository was clean before implementation.
- [x] Dataset identity was verified.
- [x] Phase-3 feature/preprocessing identity was verified.
- [x] Selected downstream model identity was verified.
- [x] Selected model is the frozen XGBoost challenger.
- [x] XGBoost model artifact hash was verified.
- [x] Preprocessor artifact hash was verified.
- [x] Selected calibration version was verified.
- [x] Current calibration method is identity.
- [x] Underlying model was NOT retrained.
- [x] XGBoost hyperparameters were NOT retuned.
- [x] Calibration was NOT changed.
- [x] TEST remained sealed.
- [x] SHAP dependency was added with compatible version.
- [x] Tree SHAP is used.
- [x] SHAP explicitly explains raw model margin.
- [x] feature_perturbation semantics are explicit.
- [x] VALIDATION raw margin was obtained.
- [x] sigmoid(raw_margin) reproduces raw probability.
- [x] Probability reconstruction error is recorded.
- [x] SHAP values cover expected validation rows.
- [x] SHAP feature width = 103.
- [x] SHAP base + contributions reconstruct raw margin.
- [x] Additivity residual statistics are recorded.
- [x] All transformed feature names map to valid lineage.
- [x] Identifier is absent from explanations.
- [x] Target is absent from explanations.
- [x] Demographics are absent from explanations.
- [x] Source-level SHAP aggregation is implemented.
- [x] Source aggregation preserves signed local totals.
- [x] Feature-family aggregation is implemented.
- [x] Family aggregation preserves signed local totals.
- [x] Global transformed SHAP importance exists.
- [x] Global source SHAP importance exists.
- [x] Global family SHAP importance exists.
- [x] Global importance artifact contains no customer-level rows.
- [x] Native XGBoost gain comparison is diagnostic only.
- [x] Local reason-code logic is deterministic.
- [x] Local reason codes use source-level contributions.
- [x] Risk-increasing and risk-decreasing directions are correct.
- [x] Reason codes are not described as causal.
- [x] Reason codes are not described as regulatory adverse-action reasons.
- [x] Internal score version exists.
- [x] Internal score uses reported probability.
- [x] Base score = 600.
- [x] Base good-to-bad odds = 50.
- [x] PDO = 20.
- [x] Factor is calculated correctly.
- [x] Offset is calculated correctly.
- [x] 50:1 good-to-bad odds maps to score 600.
- [x] Doubling good-to-bad odds adds exactly 20 points.
- [x] Higher default probability produces lower score.
- [x] Inverse score-to-probability mapping works.
- [x] Numerical clipping policy is explicit.
- [x] No arbitrary cosmetic score range/clipping exists.
- [x] Score is explicitly not FICO.
- [x] Score is explicitly not regulatory.
- [x] Score is explicitly not a business-decision policy.
- [ ] TRAIN OOF aggregate score summary exists.
- [x] VALIDATION aggregate score summary exists.
- [x] Score decile analysis exists.
- [x] Score deciles contain no customer-level records.
- [x] Score ranking is inverse-equivalent to reported probability ranking.
- [x] ROC-AUC using -score matches probability ROC-AUC.
- [x] Phase-6 technical probability threshold is mapped to a technical reference score.
- [x] No new threshold was optimized.
- [x] Technical reference score is not described as business cutoff.
- [x] Exact SHAP-to-score-point derivation is implemented.
- [x] Score-point decomposition reconstructs internal score.
- [x] Positive default-risk SHAP contribution lowers score points.
- [x] Source-level score decomposition reconstructs score.
- [x] Non-identity calibration guard exists.
- [x] Non-identity guard disables unsupported exact score decomposition.
- [x] No claim is made that SHAP directly sums to probability.
- [x] No claim is made that SHAP directly sums to calibrated probability.
- [x] No customer-level SHAP matrices are tracked.
- [x] No customer-level reason codes are tracked.
- [x] No customer-level internal scores are tracked.
- [x] No TEST SHAP was calculated.
- [x] No TEST score was calculated.
- [x] No TEST model metrics were calculated.
- [x] explainability_manifest.json exists.
- [x] shap_global_importance.json exists.
- [x] internal_score_manifest.json exists.
- [x] internal_score_summary.json exists.
- [x] score_decile_analysis.csv exists.
- [x] Explainability report exists.
- [x] Internal score document exists.
- [x] ADR 006 exists.
- [x] Real-data Phase-7 workflow completed.
- [x] Full automated test suite passes.
- [x] pip check passes.
- [x] git diff --check passes.
- [x] Historical completion reports remain unchanged.
- [x] Historical Phase-4/5 experiment metadata remains unchanged.
- [x] README matches actual implementation.
- [x] Architecture documentation is updated.
- [x] Phase-7 completion report exists.
- [x] Phase 7 status is COMPLETED.
- [x] Phase 8 remains NOT_STARTED.
- [x] No Git commit was created automatically.

Waiver: “TRAIN OOF aggregate score summary exists.” Exact statistics are unavailable; the aggregate summary artifact records that unavailability and the no-retraining reason. Owner clarification quoted in Section 33 governs this exception.

## 40. Final Verdict

PHASE 7 COMPLETED
