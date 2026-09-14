# PHASE 6 COMPLETION REPORT

## 1. Objective

Implement TRAIN-only calibration assessment for both fixed models, select the downstream development model from frozen VALIDATION results, and derive technical thresholds from TRAIN OOF probabilities. Phase 6 only.

## 2. Pre-Implementation Repository State

HEAD: `2cfc64de0f044e910038282fda6c0fd7060f36ec`, branch `main`, clean working tree. Phase 5 was committed as `feat: add xgboost credit risk challenger`. Phases 1–5 were COMPLETED; Phases 6–10 were NOT_STARTED. Phase 6 was set IN_PROGRESS during implementation. No Phase-7 functionality or predictive TEST evaluation existed.

## 3. Documentation Reviewed

Required root governance/status/roadmap/README/changelog; architecture, problem definition, dataset card, data contract, quality, leakage, governance, glossary, feature engineering, modeling dataset and baseline/XGBoost reports; ADRs 001–004; historical completion reports 01–05; dataset/split/feature/preprocessing and both model manifests/metrics plus model comparison. Existing configs, data/features/modeling code and tests informed implementation. Earlier-phase review context was retained, with focused Phase-6 rereads and contract verification. The current phase prompt controls scope and supersedes the roadmap's former risk-band wording.

## 4. Modeling Contract Verification

- Dataset: UCI Default of Credit Card Clients; SHA-256 `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.
- Target: default_next_month; 30,000 rows, seed-42 stratified 70/15/15; TRAIN 21,000, VALIDATION 4,500. TEST's 4,500 count is structural metadata only.
- Split: sorted_id_two_stage_stratified_v1; features: financial_features_v1; preprocessing: train_median_scale_onehot_v1.
- Preprocessor SHA-256: `e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4`; canonical width 103.
- Logistic: logistic-baseline-1.0.0; artifact SHA-256 `a05feadd329d36515f3e66f3ca984af52401d90702a7fea2bf3f71834c2fa07c`.
- XGBoost: xgboost-challenger-1.0.0; artifact SHA-256 `2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef`.
- Fixed configurations and selected XGBoost search row were verified; canonical raw validation metrics reproduce prior metadata within 1e-12. TEST remains sealed.

## 5. Calibration Design

Five stratified shuffled TRAIN folds, seed 42, fit fresh preprocessing and a fixed estimator on 16,800 rows and predict only the 4,200 held-out rows. Both models cover every TRAIN row exactly once without fitting that row in its OOF model. The full-TRAIN preprocessor is never reused inside OOF folds.

A second five-fold TRAIN-only CV compares identity, nonnegative-slope sigmoid and increasing isotonic mappings. Minimum mean Brier selects the winner; log loss then identity/sigmoid/isotonic simplicity break ties within absolute 1e-12. ECE is diagnostic. Winners fit all TRAIN OOF pairs, and both mappings are frozen before canonical VALIDATION scoring. No VALIDATION/TEST fitting or calibration selection occurs.

Sigmoid uses expit(a × logit(clip(p, 1e-6, 1−1e-6)) + b), a >= 0, public SciPy L-BFGS-B and explicit convergence checks. Clipping protects logit only. Isotonic clips outside its fitted input range. No underlying hyperparameter search occurs inside Phase-6 calibration.

## 6. Logistic OOF Calibration Analysis

| Method | Mean Brier | Mean log loss | Mean ECE | Mean probability | Observed rate |
| --- | --- | --- | --- | --- | --- |
| identity | 0.135268217 | 0.433354449 | 0.016267314 | 0.221232584 | 0.221190476 |
| sigmoid | 0.135308670 | 0.433406317 | 0.017875025 | 0.221210692 | 0.221190476 |
| isotonic | 0.135268863 | 0.438716831 | 0.015874677 | 0.221152876 | 0.221190476 |

Selected method: **identity**. Its Brier advantage over isotonic is approximately 6.46e-7, exceeding the fixed numerical tolerance but not implying a large practical difference. Isotonic's lower ECE does not override worse Brier/log loss.

## 7. XGBoost OOF Calibration Analysis

| Method | Mean Brier | Mean log loss | Mean ECE | Mean probability | Observed rate |
| --- | --- | --- | --- | --- | --- |
| identity | 0.133056404 | 0.424541222 | 0.017325550 | 0.221100844 | 0.221190476 |
| sigmoid | 0.133090807 | 0.424657060 | 0.017950380 | 0.221203823 | 0.221190476 |
| isotonic | 0.133212151 | 0.431312938 | 0.016834178 | 0.221154065 | 0.221190476 |

Selected method: **identity**. Both non-identity candidates worsen Brier and log loss; isotonic's modest ECE improvement is not the selection objective.

## 8. Final Calibration Mapping

| Model | Calibration version | Method | TRAIN OOF fit rows | Binary path / SHA-256 |
| --- | --- | --- | --- | --- |
| Logistic | logistic-calibration-1.0.0 | identity | 21,000 | null / null |
| XGBoost | xgboost-calibration-1.0.0 | identity | 21,000 | null / null |

Both are versioned metadata-only decisions. No fitted transformation was applied to either reported probability.

## 9. Logistic Validation — Raw Probability Metrics

| Metric | Value |
| --- | --- |
| ROC-AUC | 0.765638177 |
| Average Precision | 0.519684092 |
| KS | 0.405350576 |
| Gini | 0.531276353 |
| Brier | 0.138791607 |
| Log loss | 0.441318621 |
| ECE | 0.016085905 |
| Mean probability | 0.219725065 |
| Observed positive rate | 0.221111111 |

## 10. Logistic Validation — Reported Probability Metrics

| Metric | Value |
| --- | --- |
| ROC-AUC | 0.765638177 |
| Average Precision | 0.519684092 |
| KS | 0.405350576 |
| Gini | 0.531276353 |
| Brier | 0.138791607 |
| Log loss | 0.441318621 |
| ECE | 0.016085905 |
| Mean probability | 0.219725065 |
| Observed positive rate | 0.221111111 |

Reported minus raw: exactly zero for all nine metrics. Identity preserves the original probabilities and rankings.

## 11. XGBoost Validation — Raw Probability Metrics

| Metric | Value |
| --- | --- |
| ROC-AUC | 0.784304404 |
| Average Precision | 0.556211932 |
| KS | 0.424438885 |
| Gini | 0.568608807 |
| Brier | 0.135284871 |
| Log loss | 0.428826621 |
| ECE | 0.011402129 |
| Mean probability | 0.219568509 |
| Observed positive rate | 0.221111111 |

## 12. XGBoost Validation — Reported Probability Metrics

| Metric | Value |
| --- | --- |
| ROC-AUC | 0.784304404 |
| Average Precision | 0.556211932 |
| KS | 0.424438885 |
| Gini | 0.568608807 |
| Brier | 0.135284871 |
| Log loss | 0.428826621 |
| ECE | 0.011402129 |
| Mean probability | 0.219568509 |
| Observed positive rate | 0.221111111 |

Reported minus raw: exactly zero for all nine metrics. Identity preserves the original probabilities and rankings.

## 13. Reliability Analysis

Ten quantile bins requested and ten nonempty bins observed in all four model/probability series; 40 aggregate CSV rows. Duplicate quantile boundaries collapse, ties stay together in the right bin and empty bins are omitted. ECE weights each absolute mean-probability/observed-rate gap by bin count. Constant synthetic predictions correctly produce one bin.

Logistic's largest gap is 0.047873 in bin 10: mean 0.716762 versus observed 0.668889; bin 6 underpredicts 0.145370 versus 0.180000. XGBoost's largest gap is 0.023397 in bin 10: 0.707842 versus 0.684444; bin 6 is 0.157849 versus 0.180000. Logistic counts are 450 except bins 8/9 with 447/453; XGBoost counts are all 450.

Reported reliability equals raw reliability. ECE remains 0.016085905 for Logistic and 0.011402129 for XGBoost. Mean probabilities are within 0.00155 of prevalence 0.221111. Selected mappings create no additional ties or exact endpoints; OOF and validation each contain zero exact 0/1 probabilities for both models.

OOF/validation means are 0.221233/0.219725 for Logistic and 0.221101/0.219569 for XGBoost; standard deviations are 0.195710/0.195350 and 0.197294/0.197299. These aggregate diagnostics reveal no large central distribution discrepancy, without constituting a formal shift test. Optional calibration-intercept/slope diagnostics are omitted; required reliability/Brier/log-loss/ECE results remain available.

## 14. Final Logistic vs XGBoost Comparison

| Reported metric | Logistic | XGBoost | XGBoost − Logistic |
| --- | --- | --- | --- |
| ROC-AUC | 0.765638177 | 0.784304404 | 0.018666227 |
| Average Precision | 0.519684092 | 0.556211932 | 0.036527841 |
| KS | 0.405350576 | 0.424438885 | 0.019088309 |
| Gini | 0.531276353 | 0.568608807 | 0.037332454 |
| Brier | 0.138791607 | 0.135284871 | -0.003506736 |
| Log loss | 0.441318621 | 0.428826621 | -0.012492000 |
| ECE | 0.016085905 | 0.011402129 | -0.004683776 |

## 15. Paired Bootstrap Comparison

| XGBoost − Logistic | 95% percentile CI |
| --- | --- |
| roc_auc | 0.011856616 to 0.026106355 |
| average_precision | 0.022063804 to 0.048515345 |
| brier_score | -0.004897304 to -0.002226468 |
| log_loss | -0.016846047 to -0.008589428 |

Seed 42; 1,000 requested, 1,000 successful, zero single-class skips. Both models and all four metrics use identical VALIDATION row draws with replacement. These are percentile intervals conditional on the frozen models and development sample.

## 16. Downstream Model Selection

**XGBOOST_SELECTED_FOR_DOWNSTREAM**

The deterministic rule requires AUC/AP no lower and Brier/log loss no higher, with at least one strict improvement. XGBoost strictly improves all four. No subjective override occurred. This is NOT final untouched-test confirmation or production approval. The result agrees with the prior discrimination comparison.

## 17. Probability Semantics

raw_probability is the underlying classifier's positive-class output. A calibration mapping converts that output into reported_probability. Here calibration_method=identity for both models, so reported_probability = raw_probability; no transformed calibrated probability is claimed.

The event is the public dataset's next-month default payment. It is not Basel, IFRS 9, regulatory, 12-month or verified 90-DPD PD, a FICO score or a bank credit score. Identity selection does not establish perfect calibration.

## 18. Technical Threshold Analysis

Selected model: XGBoost. TRAIN OOF max-KS threshold: **0.21430689096450806**; source train_oof_max_ks. Highest finite threshold wins ties within 1e-12; ROC's +infinity sentinel is excluded. The TRAIN-only grid contains 0.05 through 0.95 in 0.05 steps plus this threshold, totaling 20 rows.

| Metric | TRAIN OOF selected threshold | VALIDATION frozen threshold | VALIDATION reference 0.50 |
| --- | --- | --- | --- |
| threshold | 0.214306891 | 0.214306891 | 0.500000000 |
| predicted_positive_count | 6766 | 1427 | 545 |
| predicted_positive_rate | 0.322190476 | 0.317111111 | 0.121111111 |
| tn | 12664 | 2715 | 3317 |
| fp | 3691 | 790 | 188 |
| fn | 1570 | 358 | 638 |
| tp | 3075 | 637 | 357 |
| precision | 0.454478274 | 0.446391030 | 0.655045872 |
| recall | 0.662002153 | 0.640201005 | 0.358793970 |
| specificity | 0.774319780 | 0.774607703 | 0.946362340 |
| f1 | 0.538953641 | 0.526011561 | 0.463636364 |
| false_positive_rate | 0.225680220 | 0.225392297 | 0.053637660 |
| false_negative_rate | 0.337997847 | 0.359798995 | 0.641206030 |

The same frozen TRAIN-derived threshold is evaluated on VALIDATION; no validation threshold search occurred. Reference remains exactly 0.50. This is NOT a business/lending cut-off. No lending actions or risk bands exist.

## 19. SHAP / Calibration Boundary

Future SHAP explanations of the underlying model must not automatically be claimed to sum to the calibrated/reported probability. Identity alone does not establish the output units or probability-space additivity of a future explainer. No SHAP or internal score implementation exists.

## 20. Files Created

- `configs/calibration.yaml`
- `data/metadata/calibration_manifest.json`
- `data/metadata/calibration_metrics.json`
- `data/metadata/calibration_reliability.csv`
- `data/metadata/phase6_model_selection.json`
- `data/metadata/threshold_analysis.csv`
- `docs/calibration_report.md`
- `docs/decisions/005-calibration-and-model-selection.md`
- `docs/phase_reports/phase_06_completion_report.md`
- `src/credit_risk/modeling/calibration.py`
- `src/credit_risk/modeling/calibration_metrics.py`
- `src/credit_risk/modeling/calibrators.py`
- `src/credit_risk/modeling/experiment_metadata.py`
- `src/credit_risk/modeling/thresholds.py`
- `tests/test_calibration.py`
- `tests/test_experiment_metadata.py`

## 21. Files Modified

- `CHANGELOG.md`
- `PHASE_STATUS.md`
- `README.md`
- `ROADMAP.md`
- `docs/architecture.md`
- `docs/baseline_model_report.md`
- `docs/leakage_policy.md`
- `docs/model_governance.md`
- `docs/modeling_dataset.md`
- `docs/xgboost_model_report.md`
- `src/credit_risk/modeling/baseline.py`
- `src/credit_risk/modeling/xgboost_challenger.py`

Pre-commit governance correction: comparison against the pre-Phase-6 HEAD showed only added broad provenance hashes, timestamps, a resulting baseline-manifest link change and fit/score timing changes in the three historical experiment files. Their original HEAD bytes were restored. Dataset, configuration, preprocessing, model artifacts and predictive results did not change.

The baseline and challenger now use explicit model-specific provenance module lists and a shared publication guard. Unchanged experiment identity, predictive outputs and non-timing CV results preserve every original metadata byte, including historical source hashes, timestamps and timing fields. A changed identity/result fails before metadata publication and requires an explicit new experiment record. The original source hashes describe the historical experiment, not the current reproducing code.

No calibration, metric, model-selection, threshold-selection or existing test implementation was changed. Eleven governance regression tests were added. Contextual documentation was corrected only where it previously described historical metadata refreshes. Historical completion reports 01–05 remain unchanged.

## 22. Calibration Artifacts

Both actual mappings are identity: binary paths and SHA-256 values are null, with decision/version metadata in calibration_manifest.json. No real-data calibrator binary was produced.

Synthetic sigmoid and isotonic mappings serialize under temporary artifact paths, reload with transformed probabilities matching within absolute 1e-12, and reject checksum corruption. Local artifact path convention is artifacts/calibration/<version>_<sha256>.joblib, covered by Git ignore. No calibrator/model/preprocessor binary is tracked.

## 23. Metadata / Manifests

- calibration_manifest.json: both model/data identities, fixed calibration versions, fold coverage, candidate CV metrics, selected mappings, settings and implementation hashes.
- calibration_metrics.json: raw/reported VALIDATION metrics, deltas and aggregate probability distributions for both models.
- calibration_reliability.csv: 40 aggregate model/probability/bin records with counts, ranges, means, prevalence and gaps.
- phase6_model_selection.json: reported comparison, paired bootstrap, downstream selection and frozen threshold/reference metrics.
- threshold_analysis.csv: 20 TRAIN OOF technical threshold rows.

All five record test_set_evaluated=false. Customer probabilities, predictions and matrices are not exported.

## 24. Tests Executed

Exact required workflow and verification commands executed:

```powershell
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m credit_risk.modeling.baseline
.venv\Scripts\python.exe -m credit_risk.modeling.xgboost_challenger
.venv\Scripts\python.exe -m credit_risk.modeling.calibration > artifacts/phase6_execution.log
.venv\Scripts\python.exe -m pytest tests/test_calibration.py -q
.venv\Scripts\python.exe -m credit_risk.modeling.calibration > artifacts/phase6_repeat.log
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
```

Additional checks compared SHA-256 for all five outputs across real runs, checked ignored artifact/data paths, checked new-file trailing whitespace, inspected HEAD/branch and reviewed code for prohibited later-phase functionality. Ignored execution logs contain aggregates only.

Pre-commit governance verification additionally executed:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_experiment_metadata.py -q
.venv\Scripts\python.exe -m credit_risk.data.download > artifacts/governance_download.log
.venv\Scripts\python.exe -m credit_risk.features.prepare > artifacts/governance_prepare.log
.venv\Scripts\python.exe -m credit_risk.modeling.baseline > artifacts/governance_baseline.log
.venv\Scripts\python.exe -m credit_risk.modeling.xgboost_challenger > artifacts/governance_xgboost.log
.venv\Scripts\python.exe artifacts/verify_phase6_governance.py > artifacts/governance_phase6.log
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff -- data/metadata/baseline_model_manifest.json
git diff -- data/metadata/xgboost_model_manifest.json
git diff -- data/metadata/xgboost_search_results.csv
git diff --check
git status --short --untracked-files=all
```

The ignored local verification harness invokes the unchanged calibration CLI module through runpy, substituting only its threshold-selection helper with the already reviewed value 0.21430689096450806. It reruns OOF calibration and assessment, applies the frozen threshold, and asserts unchanged reviewed outputs. It does not execute max-KS selection/optimization again. No verification harness or execution log is tracked.


## 25. Test Results

- Initial focused Phase-6 suite: **39 passed** in 19.57 seconds.
- New focused governance suite: **11 passed** in 12.21 seconds.
- Final full suite: **232 passed**, **0 failed**, **0 skipped** in 55.42 seconds; no pytest warnings reported.
- pip check: **No broken requirements found.**
- Required historical real-data CLIs and governance Phase-6 verification: successful, exit 0.
- git diff --check: passed; no whitespace errors.
- All three requested historical experiment metadata diffs: **EMPTY**; bytes equal HEAD after real reproduction.
- New-file trailing-whitespace checks and historical completion-report integrity checks: passed.
- All Phase-6 predictive/calibration results, selected model and approved threshold remain unchanged; TEST remains sealed.

## 26. Real-Data Integration Validation

The official UCI data and existing Phase-3/4/5 workflows reproduced successfully. Both models generated 21,000 OOF probabilities with exactly-one coverage. Fold widths were 103/103/103/100/102, reflecting fold-local category discovery. Logistic converged in 858/876/876/751/912 iterations; XGBoost used the fixed 350 rounds per fold.

Both identity selections, all validation metrics, 1,000 paired bootstrap replicates, downstream XGBoost selection and frozen threshold assessment completed on the real data. No TEST predictive processing occurred.

The pre-commit governance rerun reproduced those same results while reusing the approved threshold without optimization. Historical baseline/XGBoost manifests and search results remained byte-identical to HEAD after the historical CLIs and Phase-6 verification completed.

## 27. Determinism / Reproducibility Validation

Before the governance correction, two complete real Phase-6 runs produced byte-identical contents for all five metadata outputs, including the retained manifest timestamp, selection results and threshold. Synthetic OOF generation for both model types and paired bootstrap also reproduced exactly.

| Output | Repeated SHA-256 |
| --- | --- |
| calibration_manifest.json | 63d913865e2a3a4f2f22369c3b21d46475677badfbaf612be5c91cc4dfe6aa15 |
| calibration_metrics.json | 83bbe4c69eb8c5a797cd49b72b56ef0dc6b802628e4d831165f3fa51fe1ce823 |
| calibration_reliability.csv | 80753d9543002bb6f9d8e01016aab909fc38fb90d6e310002103ccec190c5107 |
| phase6_model_selection.json | 2c3e810f941c926692eb5bd256ee3edba558a1406278af6c8ff813931a8b898d |
| threshold_analysis.csv | 4745fac20c2939c43cd1d98d7dc8e1b2ea12273859fbe50a6c03dd521c06e74a |

After the governance correction, the four Phase-6 result files (metrics, reliability, model selection and thresholds) remain byte-identical to the reviewed outputs, with the same hashes above. The current Phase-6 manifest changes only implementation_sha256 and generated_at to record the governance source update; all calibration identities, OOF/CV results, methods and fitted mapping details remain unchanged. Its updated SHA-256 is `027aa2db25918518ad85eff62e016241e378a7baadd889acd11d85a3173802a8`. This current pre-commit Phase-6 provenance update does not alter historical Phase-4/5 records.

Runtime: Python 3.14.6, sklearn 1.8.0, XGBoost 3.2.0. Reproducibility across other runtimes/hardware is not guaranteed. Historical search elapsed times are not deterministic. Original tracked timing values are now preserved on identical reproduction. Governance tests verify both unchanged bytes and modification times, exclusion of unrelated modules, and rejection of dataset/configuration/preprocessing/artifact/metric/CV-result changes before any metadata write.

## 28. Test Set Status

**TEST SET WAS NOT EVALUATED.**

**TEST SET REMAINS SEALED.**

No raw test probabilities, calibrated test probabilities, test predictions, test calibration/reliability metrics, test threshold metrics or test bootstrap were produced. Earlier structural preparation does not constitute predictive evaluation.

## 29. Known Limitations

Historical Taiwan data, unresolved category semantics and no verified event-level scoring timestamps remain. This stratified random split is not out-of-time validation. Demographic exclusion does not prove fairness. Quantile ECE depends on binning, and small calibration-CV differences need not generalize. No regulatory or production readiness is claimed.

## 30. Deviations From Prompt

The prompt both prohibits retraining/tuning underlying models and explicitly requires running their training CLIs. The mandated Phase-4/5 commands were run as reproduction of the unchanged historical experiment, including the existing Phase-5 search. This did not introduce a new search configuration, change selected parameters or change model bytes/metrics. The Phase-6 calibration implementation itself performs no hyperparameter search.

Identity metadata-only artifacts and omission of optional intercept/slope diagnostics are explicitly permitted by the prompt. No other functional deviations.

## 31. Risks / Technical Debt

The required second-level CV is not fully nested end-to-end evaluation: underlying OOF models have overlapping training samples, and prior XGBoost parameter selection already used TRAIN. Threshold diagnostics can be optimistic because the final mapping fits all OOF labels. VALIDATION is a reused development set; bootstrap intervals omit retraining/model-selection and deployment-shift uncertainty.

The tiny Logistic identity/isotonic Brier difference is resolved by the predeclared numerical rule, not practical significance. Candidate isotonic log loss worsened for both models; this is disclosed rather than hidden. No selected transformation worsens validation metrics because identity was retained.

The historical metadata mutation issue is resolved: new provenance uses explicit module lists; unchanged reproduction retains original historical bytes and timings. Legacy source hashes remain deliberately unchanged because they identify the original experiment. A genuine identity/result mismatch requires an explicit new record and fails rather than silently updating the historical path. Runtime pinning and ignored artifact reconstruction remain operational dependencies. Native/local joblib artifacts must be trusted; checksums do not make untrusted pickle safe.

## 32. Phase-7 Recommendations

When separately authorized after owner review/checkpoint, load the selected XGBoost plus its identity calibration version, explicitly validate SHAP output units/additivity, preserve transformed-feature lineage and independently document any internal-score mapping. Keep probability, explanation, score and business policy separate. Recommendations only; Phase 7 remains NOT_STARTED.

## 33. Reproduction Commands

With the existing verified environment and local prerequisites:

```powershell
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.features.prepare
.venv\Scripts\python.exe -m credit_risk.modeling.baseline
.venv\Scripts\python.exe -m credit_risk.modeling.xgboost_challenger
.venv\Scripts\python.exe -m credit_risk.modeling.calibration
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
git diff --check
```

The calibration CLI also accepts --project-root PATH. Earlier model CLIs reconstruct prerequisites and preserve historical metadata on unchanged reproduction. For this governance verification, the local harness shown in Section 24 reused the already reviewed threshold; no threshold optimization was repeated.

## 34. Git Status

12 existing files modified and 16 new files untracked; no staging or commit performed. HEAD remains the Phase-5 commit.

```text
 M CHANGELOG.md
 M PHASE_STATUS.md
 M README.md
 M ROADMAP.md
 M docs/architecture.md
 M docs/baseline_model_report.md
 M docs/leakage_policy.md
 M docs/model_governance.md
 M docs/modeling_dataset.md
 M docs/xgboost_model_report.md
 M src/credit_risk/modeling/baseline.py
 M src/credit_risk/modeling/xgboost_challenger.py
?? configs/calibration.yaml
?? data/metadata/calibration_manifest.json
?? data/metadata/calibration_metrics.json
?? data/metadata/calibration_reliability.csv
?? data/metadata/phase6_model_selection.json
?? data/metadata/threshold_analysis.csv
?? docs/calibration_report.md
?? docs/decisions/005-calibration-and-model-selection.md
?? docs/phase_reports/phase_06_completion_report.md
?? src/credit_risk/modeling/calibration.py
?? src/credit_risk/modeling/calibration_metrics.py
?? src/credit_risk/modeling/calibrators.py
?? src/credit_risk/modeling/experiment_metadata.py
?? src/credit_risk/modeling/thresholds.py
?? tests/test_calibration.py
?? tests/test_experiment_metadata.py
```

The baseline_model_manifest.json, xgboost_model_manifest.json and xgboost_search_results.csv diffs against HEAD are EMPTY. Each is also byte-identical to its HEAD blob after actual reproduction.

git ls-files under data/raw, data/interim, data/processed and artifacts returns only their four .gitkeep placeholders. Raw dataset, processed customer rows, OOF/validation customer probabilities, matrices, split assignments and preprocessor/model/calibrator binaries are not tracked. Verification scripts/logs remain ignored. No commit was created.

## 35. Documentation Status

README, CHANGELOG, PHASE_STATUS, ROADMAP, architecture, model governance, modeling dataset, leakage policy and contextual baseline/XGBoost reports now reflect Phase 6. Calibration report, ADR 005 and this completion report exist. Historical phase reports 01–05 remain unchanged. The pre-commit governance correction is recorded here and in the affected contextual documentation; scientific results and methodology are preserved.

Current Completed Phase: Phase 6. Next Phase: Phase 7. Phases 1–6 are COMPLETED; Phases 7–10 remain NOT_STARTED. Owner technical review and any fixes precede the owner's Git commit; no automatic continuation.

## 36. Acceptance Criteria Checklist

- [x] Required project documentation was reviewed first.
- [x] Phase-2 dataset identity was verified.
- [x] Phase-3 split/feature/preprocessing identities were verified.
- [x] Phase-4 Logistic identity was verified.
- [x] Phase-5 XGBoost identity was verified.
- [x] TEST remained sealed.
- [x] Logistic TRAIN OOF probabilities were generated.
- [x] XGBoost TRAIN OOF probabilities were generated.
- [x] Every TRAIN row received exactly one OOF prediction per model.
- [x] No OOF row was scored by a model trained on that row.
- [x] Preprocessing was fitted inside each OOF fold.
- [x] Full-TRAIN fitted preprocessor was not reused inside OOF calibration folds.
- [x] Calibration candidates include identity.
- [x] Calibration candidates include sigmoid.
- [x] Calibration candidates include isotonic.
- [x] Calibrator selection uses TRAIN only.
- [x] Project VALIDATION is not used to select calibration method.
- [x] TEST is not used to select calibration method.
- [x] Calibration-selection CV is implemented.
- [x] Brier is primary calibration-selection metric.
- [x] Log loss is secondary tie-break metric.
- [x] Simplicity tie-break is deterministic.
- [x] Logistic selected calibration method is recorded.
- [x] XGBoost selected calibration method is recorded.
- [x] Final Logistic calibrator was fit only using TRAIN OOF probabilities.
- [x] Final XGBoost calibrator was fit only using TRAIN OOF probabilities.
- [x] VALIDATION was not used to fit calibrators.
- [x] TEST was not used to fit calibrators.
- [x] Validation raw Logistic metrics were measured.
- [x] Validation reported Logistic metrics were measured.
- [x] Validation raw XGBoost metrics were measured.
- [x] Validation reported XGBoost metrics were measured.
- [x] Brier score was measured.
- [x] Log loss was measured.
- [x] ECE was measured.
- [x] Reliability aggregate tables were generated.
- [x] Mean probability and observed prevalence were compared.
- [x] Calibration/discrimination metric deltas were recorded.
- [x] Calibration was not presented as a discrimination technique.
- [x] Reported probabilities remain explicitly non-regulatory.
- [x] Downstream model selection rule is deterministic.
- [x] Phase-6 model-selection artifact exists.
- [x] No subjective model-selection override occurred.
- [x] Paired bootstrap comparison uses frozen VALIDATION only.
- [x] Paired bootstrap does not use TEST.
- [x] Calibration manifest exists.
- [x] Calibration metrics artifact exists.
- [x] Calibration reliability artifact exists.
- [x] Calibration artifact(s) are versioned.
- [x] Non-identity calibrator artifact(s) serialize/reload correctly.
- [x] Calibrator binary artifacts are not tracked in Git.
- [x] Technical max-KS threshold is derived from TRAIN OOF only.
- [x] VALIDATION is not used to choose threshold.
- [x] Reference threshold remains 0.50.
- [x] Threshold trade-off table exists.
- [x] Train-derived threshold was evaluated unchanged on VALIDATION.
- [x] Threshold is not described as lending/business policy.
- [x] No APPROVE/DECLINE/MANUAL_REVIEW logic exists.
- [x] No arbitrary LOW/MEDIUM/HIGH risk bands were created.
- [x] No SHAP implementation exists.
- [x] SHAP/calibration semantic boundary is documented.
- [x] No internal credit score exists.
- [x] No Phase-7 functionality was implemented.
- [x] No customer-level OOF probabilities are tracked.
- [x] No customer-level validation probabilities are tracked.
- [x] No customer-level matrices are tracked.
- [x] Real UCI Phase-6 workflow completed successfully.
- [x] Full automated test suite passes.
- [x] pip check passes.
- [x] git diff --check passes.
- [x] Historical completion reports remain unchanged.
- [x] README matches actual implementation.
- [x] Architecture documentation is updated.
- [x] Phase-6 completion report exists.
- [x] Phase 6 status is COMPLETED.
- [x] Phase 7 remains NOT_STARTED.
- [x] No Git commit was created automatically.

Identity artifact criteria are fulfilled by versioned metadata; non-identity serialization/reload is verified on synthetic sigmoid/isotonic mappings, with no unnecessary real-data binary.

## 37. Final Verdict

PHASE 6 COMPLETED
