# PHASE 5 COMPLETION REPORT

## 1. Objective

Build a nonlinear XGBoost challenger, select its parameters through TRAIN-only fold-safe CV and compare it with the stored Logistic Regression baseline on VALIDATION. Preserve raw probability semantics and sealed TEST. No final production model is selected.

## 2. Pre-Implementation Repository State

HEAD: `15ab71f`, branch `main`. Working tree was clean. Phase 4 was committed as `feat: add logistic regression credit risk baseline`. Phases 1–4 were COMPLETED; Phases 5–10 were NOT_STARTED. Baseline metadata/artifacts were available and reproduced. No Phase-6+ functionality existed. TEST had not been predictively evaluated.

## 3. Documentation Reviewed

Reviewed root governance, rules, roadmap, status, README and changelog; domain, architecture, dataset, quality, leakage, governance, glossary, feature and modeling documentation; baseline report; ADRs 001–003; historical Phase-1/2/3/4 reports; configuration, data/features/modeling code, tests and aggregate metadata. Inspected Git history/state and verified baseline reproduction.

Checked official XGBoost [package compatibility](https://pypi.org/project/xgboost/3.2.0/), [sparse/dense semantics](https://xgboost.readthedocs.io/en/release_3.2.0/faq.html) and [native serialization guidance](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/saving_model.html).

## 4. Modeling Contract Verification

- Dataset SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.
- Split: `sorted_id_two_stage_stratified_v1`; seed 42, stratified 70/15/15.
- Feature engineering: `financial_features_v1`.
- Preprocessing: `train_median_scale_onehot_v1`.
- Preprocessor SHA-256: `e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4`.
- Final transformed width: 103.
- TRAIN: 21,000 rows; VALIDATION: 4,500 rows.
- TEST: 4,500 rows from Phase-3 metadata, sealed.
- Baseline: `logistic-baseline-1.0.0`.

Raw/Phase-3 identities, code/runtime versions, lineage, exclusions, shapes and finite matrices are verified. Baseline metadata is loaded, checked against these identities and verified through artifact-based probability/metric reproduction. No hard-coded baseline metrics are used.

## 5. XGBoost Specification

Model version: `xgboost-challenger-1.0.0`. Library: **xgboost 3.2.0**. Estimator: XGBClassifier. Invariants: objective=binary:logistic, eval_metric=logloss, tree_method=hist, device=cpu, random_state=42, n_jobs=1, canonical scale_pos_weight=1.0.

Version 3.2.0 supports Python >=3.10 and preserves the project's >=3.11 requirement; the newer 3.4.1 requires >=3.12. Existing numerical dependencies were not changed.

## 6. Cross-Validation Design

TRAIN-only RandomizedSearchCV with **24 candidates and four shuffled stratified folds**, seed 42. Every CV fit creates fresh Phase-3 preprocessing; the full-TRAIN fitted artifact is never passed into CV. Stateless financial engineering is reused beforehand.

The wrapper discards sklearn's y argument before unsupervised fitting, preserving the original target-rejection guard. Tests inspect actual fold memberships, train medians and a holdout-only category in fitted vocabularies.

Score ROC-AUC and Average Precision; use n_jobs=1, error_score=raise and return_train_score=False. A callable refit applies the required deterministic AUC/AP/simplicity selection rule. No accuracy selection, project-validation fitting or early stopping occurs.

Dense materialization preserves the same transformed values and zeros; XGBoost would treat absent CSR entries as missing. This is a storage adaptation, not a feature/preprocessing change.

## 7. Hyperparameter Search Space

The authoritative definition is configs/xgboost.yaml; the seed remains in shared base configuration.

| Parameter | Candidates |
| --- | --- |
| colsample_bytree | 0.8, 0.9, 1 |
| gamma | 0, 0.1, 0.5 |
| learning_rate | 0.03, 0.05, 0.08, 0.1 |
| max_depth | 2, 3, 4, 5 |
| min_child_weight | 1, 3, 5, 10 |
| n_estimators | 200, 350, 500, 700 |
| reg_alpha | 0, 0.1, 0.5 |
| reg_lambda | 1, 5, 10 |
| subsample | 0.8, 0.9, 1 |

## 8. Hyperparameter Search Results

**24 candidates × 4 folds = 96 candidate CV fits.** Search performs one additional winner refit; final canonical and sensitivity models add two fits, totaling **99 XGBoost fits per workflow**.

Winner: zero-based candidate **21**, rank 1. Mean CV AUC **0.787520370**, std **0.008418025**. Mean CV AP **0.561642645**, std **0.008710672**.

| Parameter | Selected value |
| --- | --- |
| colsample_bytree | 1 |
| gamma | 0.5 |
| learning_rate | 0.03 |
| max_depth | 3 |
| min_child_weight | 10 |
| n_estimators | 350 |
| reg_alpha | 0.5 |
| reg_lambda | 5 |
| subsample | 0.9 |

| Rank | Candidate | Mean CV AUC | Mean CV AP |
| --- | --- | --- | --- |
| 1 | 21 | 0.787520370 | 0.561642645 |
| 2 | 19 | 0.787416339 | 0.563835147 |
| 3 | 0 | 0.786576146 | 0.559736492 |
| 4 | 3 | 0.786173059 | 0.556879238 |
| 5 | 1 | 0.785988771 | 0.554904339 |

Select greatest mean CV AUC; machine-epsilon ties use greater AP, smaller depth, fewer estimators, then greater reg_lambda/reg_alpha/gamma in that order. Remaining ties use earlier sampled candidate. Candidate 19's higher AP does not override candidate 21's greater AUC.

CSV mean_test_* fields mean CV fold-holdout scores, never the sealed project TEST partition. Measured timings do not select the winner.

## 9. Canonical Challenger Training

Fit a new XGBClassifier using the selected parameters and scale_pos_weight=1.0 on full TRAIN only. Use the verified Phase-3 fitted preprocessor representation, materialized densely with identical values and feature order.

No preprocessing or model refit on train+validation, no early stopping, no validation fitting and no TEST scoring. The search-refitted pipeline is not the serialized canonical artifact.

## 10. Train Metrics

| Metric | TRAIN |
| --- | --- |
| ROC-AUC | 0.811032912 |
| Average Precision | 0.602438553 |
| KS | 0.467348085 |
| Gini | 0.622065824 |
| Brier score | 0.127919859 |
| Log loss | 0.408690994 |
| Mean raw probability | 0.221109911 |
| Observed positive rate | 0.221190476 |
| TN | 15544 |
| FP | 811 |
| FN | 2823 |
| TP | 1822 |
| PRECISION | 0.691986327 |
| RECALL | 0.392249731 |
| SPECIFICITY | 0.950412718 |
| F1 | 0.500687002 |

## 11. Validation Metrics

| Metric | VALIDATION |
| --- | --- |
| ROC-AUC | 0.784304404 |
| Average Precision | 0.556211932 |
| KS | 0.424438885 |
| Gini | 0.568608807 |
| Brier score | 0.135284871 |
| Log loss | 0.428826621 |
| Mean raw probability | 0.219568509 |
| Observed positive rate | 0.221111111 |
| TN | 3317 |
| FP | 188 |
| FN | 638 |
| TP | 357 |
| PRECISION | 0.655045872 |
| RECALL | 0.358793970 |
| SPECIFICITY | 0.946362340 |
| F1 | 0.463636364 |

**REFERENCE THRESHOLD = 0.50**, using raw_probability >= 0.50. It is a diagnostic, not an optimized threshold or business policy. Confusion matrix order: [[TN, FP], [FN, TP]]. AP is Average Precision, not trapezoidal PR-AUC; KS=max(TPR−FPR), Gini=2×AUC−1. Metric implementation is reused from Phase 4.

## 12. Train vs Validation Assessment

TRAIN minus VALIDATION: AUC **0.026728508**, AP **0.046226620**, KS **0.042909200**. Training Brier/log loss are lower by 0.007365013/0.020135627. There is measurable fitting optimism, without near-perfect training discrimination or validation collapse. Validation AUC is close to the winning CV mean. No claim of absent overfitting is made.

Selected learning_rate=0.03 is at the low search edge; min_child_weight=10, reg_alpha=0.5 and gamma=0.5 are at upper edges. With depth 3 and lambda 5, these favor restrained capacity and are not pathological values. Search was not expanded after seeing validation results.

## 13. Class-Imbalance Sensitivity

TRAIN negative/positive counts: **16,355 / 4,645**. Weighted scale_pos_weight: **3.5209903121636166**. Fit one temporary weighted model with the same selected parameters and assess VALIDATION only.

| Metric | Canonical | Weighted |
| --- | --- | --- |
| ROC-AUC | 0.784304404 | 0.781754134 |
| Average Precision | 0.556211932 | 0.554985546 |
| KS | 0.424438885 | 0.421881160 |
| Gini | 0.568608807 | 0.563508269 |
| Brier score | 0.135284871 | 0.179989109 |
| Log loss | 0.428826621 | 0.544844855 |
| Mean raw probability | 0.219568509 | 0.422024017 |
| Observed positive rate | 0.221111111 | 0.221111111 |
| TN | 3317 | 2762 |
| FP | 188 | 743 |
| FN | 638 | 370 |
| TP | 357 | 625 |
| PRECISION | 0.655045872 | 0.456871345 |
| RECALL | 0.358793970 | 0.628140704 |
| SPECIFICITY | 0.946362340 | 0.788017118 |
| F1 | 0.463636364 | 0.528988574 |

Weighting raises recall but lowers precision/specificity and shifts mean probability from 0.2196 to 0.4220, versus observed prevalence 0.2211. AUC/AP decrease slightly; Brier/log loss worsen substantially. It changes probability scale, not calibration.

**The weighted model is NOT canonical and is NOT serialized.** No SMOTE, oversampling or undersampling occurs.

## 14. Logistic Regression Baseline Comparison

Baseline metrics are loaded from stored Phase-4 metadata and verified against the baseline artifact. Both models use the same VALIDATION rows and 103 transformed values.

| Metric | Logistic | XGBoost | XGB − Logistic |
| --- | --- | --- | --- |
| ROC-AUC | 0.765638177 | 0.784304404 | 0.018666227 |
| Average Precision | 0.519684092 | 0.556211932 | 0.036527841 |
| KS | 0.405350576 | 0.424438885 | 0.019088309 |
| Gini | 0.531276353 | 0.568608807 | 0.037332454 |
| Brier score | 0.138791607 | 0.135284871 | -0.003506736 |
| Log loss | 0.441318621 | 0.428826621 | -0.012492000 |
| Mean raw probability | 0.219725065 | 0.219568509 | -0.000156556 |
| Observed positive rate | 0.221111111 | 0.221111111 | 0 |
| TN | 3323 | 3317 | -6 |
| FP | 182 | 188 | 6 |
| FN | 645 | 638 | -7 |
| TP | 350 | 357 | 7 |
| PRECISION | 0.657894737 | 0.655045872 | -0.002848865 |
| RECALL | 0.351758794 | 0.358793970 | 0.007035176 |
| SPECIFICITY | 0.948074180 | 0.946362340 | -0.001711840 |
| F1 | 0.458415193 | 0.463636364 | 0.005221170 |

Discrimination improves; lower Brier/log loss also favor the canonical challenger here, without establishing calibration. Fixed-threshold precision/specificity decrease slightly, while recall/F1 increase.

## 15. Paired Bootstrap Comparison

1,000 validation row resamples with replacement, seed 42, identical indices for both models. **1,000 successful replicates; 0 single-class skips.**

- Delta ROC-AUC percentile 95% CI: **[0.011856616, 0.026106355]**.
- Delta AP percentile 95% CI: **[0.022063804, 0.048515345]**.

Both intervals are positive on this sample. They condition on fitted models and omit training, search and population-shift uncertainty. No per-customer probabilities are saved. TEST is not bootstrapped.

## 16. Provisional Discrimination Status

**XGBOOST_LEADS_ON_VALIDATION_DISCRIMINATION**

Both VALIDATION AUC and AP exceed the baseline. The deterministic point-estimate rule sets this status; it is **not final production-model selection**. final_model_selected=false. Final selection is deferred to Phase-6 calibration analysis and later requirements.

## 17. Probability Semantics

Probabilities are **raw / uncalibrated** model probabilities of source-defined next-month default payment. They are not regulatory, Basel/IFRS 9, 12-month or verified 90-DPD PD, FICO or a bank credit score. Calibration belongs to Phase 6 and is not implemented.

## 18. Feature Importance Diagnostic

| Transformed feature | Gain | Normalized gain | Split count |
| --- | --- | --- | --- |
| numeric__max_documented_delay | 684.840210 | 0.338041 | 31 |
| numeric__recent_documented_delay_flag | 466.965149 | 0.230496 | 29 |
| numeric__months_with_documented_delay | 150.493820 | 0.074285 | 104 |
| repayment__repayment_status_2005_09_status_1 | 104.348236 | 0.051507 | 34 |
| repayment__repayment_status_2005_09_status_2 | 37.988525 | 0.018751 | 63 |
| numeric__payment_amount_max | 32.181496 | 0.015885 | 41 |
| numeric__bill_amount_max | 28.933823 | 0.014282 | 23 |
| repayment__repayment_status_2005_06_status_-1 | 28.839813 | 0.014235 | 4 |
| repayment__repayment_status_2005_07_status_-1 | 25.912405 | 0.012790 | 10 |
| numeric__bill_amount_mean | 17.737389 | 0.008755 | 50 |

All 103 names are represented, including zero importance for unused fields. Native f0…f102 identifiers map to validated Phase-3 names and source lineage. The three documented-delay summaries account for approximately 64.28% of normalized gain. Their sources are permitted history fields; this does not verify snapshot timing or establish causality.

Gain is mean training loss reduction per split using a feature, normalized across feature gains. It is an aggregate split diagnostic, not total model-performance attribution, SHAP, a customer reason or regulatory adverse-action explanation. Correlation, category sparsity and split opportunities affect interpretation.

## 19. Test Set Status

**TEST SET WAS NOT EVALUATED. TEST SET REMAINS SEALED.**

No test probabilities, predictions or performance metrics were generated. TEST did not enter CV, early stopping, class weighting, bootstrap or model choice. All relevant Phase-5 outputs record test_set_evaluated=false.

## 20. Files Created

Thirteen new Git-visible files:

- configs/xgboost.yaml
- src/credit_risk/modeling/search.py
- src/credit_risk/modeling/comparison.py
- src/credit_risk/modeling/xgboost_challenger.py
- tests/test_xgboost.py
- data/metadata/xgboost_search_results.csv
- data/metadata/xgboost_model_manifest.json
- data/metadata/xgboost_metrics.json
- data/metadata/model_comparison.json
- data/metadata/xgboost_feature_importance.json
- docs/decisions/004-xgboost-challenger.md
- docs/xgboost_model_report.md
- docs/phase_reports/phase_05_completion_report.md

The native model was additionally created under ignored artifacts/models.

## 21. Files Modified

Eleven existing files: pyproject.toml, CHANGELOG.md, PHASE_STATUS.md, README.md, ROADMAP.md, docs/architecture.md, docs/baseline_model_report.md, docs/decisions/README.md, docs/leakage_policy.md, docs/model_governance.md and docs/modeling_dataset.md.

The baseline model report receives only a Phase-5 context link; its technical measurements remain unchanged. Existing data/features/baseline implementation, shared configuration, prior aggregate metadata and historical completion reports remain unchanged.

## 22. Model Artifact

Path: `artifacts/models/xgboost-challenger-1.0.0_2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef.json`.

Format: **XGBoost native JSON**, produced with XGBClassifier.save_model.

SHA-256: `2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef`.

Native reload reproduces TRAIN and VALIDATION raw probabilities within absolute tolerance **1e-12**. The artifact is ignored and untracked. Only trusted locally generated XGBoost models may be loaded; checksum identity does not make arbitrary external files safe.

## 23. Metadata / Manifests

- xgboost_model_manifest.json: dataset/split/feature/preprocessor identity, runtime/config/code provenance, model settings, selected candidate/parameters, search counts/scores, native artifact identity and TEST sealing.
- xgboost_metrics.json: canonical TRAIN/VALIDATION metrics, gaps, raw semantics, fixed threshold and separately labeled weighted VALIDATION sensitivity.
- xgboost_search_results.csv: all 24 candidates, ranks, parameters, CV means/stds, measured fit/score times and selection flag.
- model_comparison.json: stored baseline/canonical validation metrics, deltas, paired intervals, provisional status and final_model_selected=false.
- xgboost_feature_importance.json: all transformed names, source/type/family, gain, normalized gain and split count.

No customer records, assignments, matrices or per-customer probabilities/predictions are exported.

## 24. Tests Executed

```powershell
.venv\Scripts\python.exe -m pip index versions xgboost
.venv\Scripts\python.exe -m pip install --dry-run xgboost==3.2.0
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m credit_risk.modeling.baseline
.venv\Scripts\python.exe -m credit_risk.modeling.xgboost_challenger
.venv\Scripts\python.exe -m pytest tests/test_xgboost.py -q
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed artifacts
git diff -- docs/phase_reports/phase_01_completion_report.md
git diff -- docs/phase_reports/phase_02_completion_report.md
git diff -- docs/phase_reports/phase_03_completion_report.md
git diff -- docs/phase_reports/phase_04_completion_report.md
```

Additional Python stdin verification repeated run_challenger(Path.cwd()), compared all aggregate JSON bytes exactly and compared search CSV values exactly after excluding measured fit/score times. Additional checks verified dependency Python compatibility, previous metadata diffs, artifact ignore status, local Markdown links and whitespace.

## 25. Test Results

**182 passed, 0 failed, 0 skipped, no warnings**, in **22.96 seconds**. This includes 160 existing tests and 22 new Phase-5 cases. The targeted suite also passed all 22 tests in 13.99 seconds. No failed test runs occurred.

pip check: **No broken requirements found.** Git diff whitespace and documentation checks pass. Historical reports and prior metadata remain unchanged. Automated tests use synthetic rows/mocks, with no live network or real-customer dependency.

## 26. Real-Data Integration Validation

The pinned XLS was verified; Phase-3 preparation reproduced unchanged metadata. The required baseline CLI reproduced its existing model/metrics. The full challenger workflow completed on real UCI TRAIN/VALIDATION data: contract checks, 96 CV fits, deterministic selection, canonical fit, sensitivity, stored-baseline comparison, paired bootstrap, native importance and serialization verification.

TEST remained sealed. No customer outputs were saved.

## 27. Determinism / Reproducibility Validation

A second complete real run reproduced the selected candidate/parameters, every CV score, final metrics, importance, comparison status, native model SHA-256 and all aggregate JSON bytes exactly. Only measured fit/score timings differ.

Each run used 96 CV fits plus three full-TRAIN fits. Two deliberate reproducibility runs therefore executed **192 CV fits and six other XGBoost fits**, without expanding the 24-candidate search. Synthetic tests also verify seeded model output, paired bootstrap and native round-trip consistency.

Fixed source, code, settings, seed and recorded environment support this local result. Bitwise reproducibility across XGBoost/compiler/platform versions is not claimed.

## 28. Known Limitations

Historical Taiwan population, static cohorts, undocumented repayment codes, timing assumptions, proxies and correlated features remain. No true out-of-time validation, fairness certification, regulatory compliance or production readiness is established.

The search is bounded and not exhaustive; fitting optimism exists. Paired intervals omit training/search/population-shift uncertainty. Native gain is not local explanation. Dense materialization suits this dataset but requires reconsideration for much larger populations. Transitive dependencies are recorded but not fully locked.

## 29. Deviations From Prompt

No search-space, candidate-count or scope reduction.

Two technical adaptations implement the requested semantics: callable refit enforces the explicit AUC/AP/simplicity tie rule, and dense materialization preserves Phase-3 zero values for XGBoost. The learned feature representation is unchanged. These decisions and the extra search-refit count are documented.

## 30. Risks / Technical Debt

Future calibration must respect prior use of project VALIDATION for model comparison; TEST cannot become a selection tool. Weighting changes probability scale and is not a calibration method. Excluding demographics does not remove proxies.

Phase-3 contracts remain deliberately pinned and require review before definition/runtime changes. Local model loading requires trusted storage. The native model records prediction state while the manifest records training settings. Timing columns are observational and not deterministic. The version/digest artifact layout follows the Phase-4/5 prompts and ADRs rather than the older generic experiment-directory example.

## 31. Phase-6 Recommendations

After owner review, commit and an explicit Phase-6 request, assess probability calibration and model trade-offs. Carry the unweighted XGBoost challenger forward as the provisional discrimination leader while retaining Logistic Regression as a comparator. Preserve test sealing and separate calibration, probability reporting and business-policy identities.

Recommendations only. **No calibration was implemented; Phase 6 is NOT_STARTED.**

## 32. Reproduction Commands

From the repository root, using the documented environment:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m credit_risk.modeling.baseline
.venv\Scripts\python.exe -m credit_risk.modeling.xgboost_challenger
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --untracked-files=all
git ls-files data/raw data/interim data/processed artifacts
```

CLIs accept --project-root PATH. Baseline reproduction precedes challenger comparison; a baseline rerun may refresh its broad implementation-provenance listing as modeling modules are added, without changing model parameters/probabilities. Historical reports are never rewritten. Search timing fields may change. No notebook is required.

## 33. Git Status

**11 tracked files modified; 13 new Git-visible files untracked. Nothing staged.** Raw/interim/processed/artifacts tracking contains only .gitkeep markers.

Raw dataset, processed customer rows, customer probabilities/predictions, transformed matrices, split assignments, fitted preprocessor, Logistic binary and native XGBoost artifact are not tracked. Historical Phase-1/2/3/4 reports remain unchanged.

HEAD remains `15ab71f`. **No commit was created.**

## 34. Documentation Status

XGBoost report, ADR 004, five aggregate outputs and this completion report exist. Current README, architecture, governance, leakage, data-consumer documentation, changelog and phase records reflect Phase 5.

Phases 1–5 are COMPLETED. Phases 6–10 are NOT_STARTED. Current Completed Phase: Phase 5. Next Phase: Phase 6, not started. No calibration, SHAP, risk bands, internal score, lending policy, API, database, Docker or MLflow was implemented.

## 35. Acceptance Criteria Checklist

- [x] Required project documentation was reviewed first.
- [x] Phase-2 dataset identity was verified.
- [x] Phase-3 split identity was verified.
- [x] Phase-3 feature/preprocessing identity was verified.
- [x] Phase-4 baseline identity was verified.
- [x] Baseline metrics are loaded from tracked metadata.
- [x] XGBoost is the only new predictive model family introduced.
- [x] XGBClassifier uses binary:logistic.
- [x] tree_method=hist.
- [x] centralized random seed is used.
- [x] n_jobs=1.
- [x] canonical scale_pos_weight=1.0.
- [x] Hyperparameter search uses TRAIN only.
- [x] Hyperparameter search uses stratified CV.
- [x] CV preprocessing is fitted inside each fold.
- [x] Pre-fitted full-TRAIN preprocessor is NOT used inside CV.
- [x] Validation is not used for hyperparameter fitting.
- [x] TEST is not used for hyperparameter fitting.
- [x] Controlled randomized search completed.
- [x] Actual candidate count is documented.
- [x] Actual CV fold count is documented.
- [x] Actual total fit count is documented.
- [x] Search results artifact exists.
- [x] Canonical challenger was fit on full TRAIN only.
- [x] Canonical challenger uses selected CV parameters.
- [x] Canonical challenger uses scale_pos_weight=1.0.
- [x] TRAIN probabilities were generated.
- [x] VALIDATION probabilities were generated.
- [x] TEST probabilities were NOT generated.
- [x] TEST predictions were NOT generated.
- [x] TEST metrics were NOT generated.
- [x] test_set_evaluated=false is recorded everywhere relevant.
- [x] TRAIN ROC-AUC was measured.
- [x] VALIDATION ROC-AUC was measured.
- [x] TRAIN Average Precision was measured.
- [x] VALIDATION Average Precision was measured.
- [x] TRAIN KS was measured.
- [x] VALIDATION KS was measured.
- [x] TRAIN Gini was measured.
- [x] VALIDATION Gini was measured.
- [x] TRAIN Brier was measured.
- [x] VALIDATION Brier was measured.
- [x] TRAIN log loss was measured.
- [x] VALIDATION log loss was measured.
- [x] Reference threshold is exactly 0.50.
- [x] Threshold was not optimized.
- [x] Threshold was not described as business policy.
- [x] Weighted sensitivity experiment was performed separately.
- [x] Weighted sensitivity did not replace canonical model.
- [x] No SMOTE / oversampling / undersampling was performed.
- [x] Logistic-vs-XGBoost validation comparison exists.
- [x] Metric deltas were calculated.
- [x] Paired bootstrap comparison exists.
- [x] Paired bootstrap does not use TEST.
- [x] Provisional discrimination status was generated deterministically.
- [x] No final production champion was declared.
- [x] Native gain feature importance was generated.
- [x] Feature importance maps correctly to transformed names.
- [x] Feature importance is not presented as SHAP.
- [x] No SHAP implementation exists.
- [x] No calibration implementation exists.
- [x] No business decision engine exists.
- [x] No risk bands exist.
- [x] No internal credit score exists.
- [x] XGBoost native model artifact was serialized locally.
- [x] Model artifact SHA-256 was recorded.
- [x] Reloaded artifact reproduces probabilities.
- [x] XGBoost model artifact is not tracked in Git.
- [x] xgboost_model_manifest.json exists.
- [x] xgboost_metrics.json exists.
- [x] xgboost_search_results.csv exists.
- [x] model_comparison.json exists.
- [x] xgboost_feature_importance.json exists.
- [x] XGBoost ADR exists.
- [x] XGBoost model report exists.
- [x] Real UCI Phase-5 experiment completed.
- [x] Full automated test suite passes.
- [x] pip check passes.
- [x] git diff --check passes.
- [x] No customer-level predictions are tracked.
- [x] No customer-level matrices are tracked.
- [x] Historical completion reports remain unchanged.
- [x] README matches actual implementation.
- [x] Architecture documentation is updated.
- [x] Phase-5 completion report exists.
- [x] Phase 5 status is COMPLETED.
- [x] Phase 6 remains NOT_STARTED.
- [x] No Git commit was created automatically.

## 36. Final Verdict

PHASE 5 COMPLETED
