# Probability calibration and downstream selection — Phase 6

## Scope and frozen contracts

Both fixed models use the verified UCI next-month default-payment target and the existing seed-42 stratified 70/15/15 split. TRAIN has 21,000 rows; VALIDATION has 4,500. TEST remains sealed. Dataset SHA-256: `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`. Split: sorted_id_two_stage_stratified_v1; features: financial_features_v1; preprocessing: train_median_scale_onehot_v1. Canonical model width is 103.

Logistic version: logistic-baseline-1.0.0, L2 C=1, class_weight=None, lbfgs. XGBoost version: xgboost-challenger-1.0.0, CPU hist, scale_pos_weight=1, n_jobs=1, seed 42; fixed selected parameters remain colsample_bytree=1, gamma=0.5, learning_rate=0.03, max_depth=3, min_child_weight=10, n_estimators=350, reg_alpha=0.5, reg_lambda=5 and subsample=0.9. Phase 6 performs no hyperparameter search. Required earlier-phase CLI reproduction used the unchanged historical configuration and reproduced both artifact hashes and metrics. The pre-commit governance fix restores original historical metadata and preserves its provenance, timestamps and search timings on identical reproduction.

## Calibration design

Five stratified shuffled TRAIN folds generate exactly one OOF raw probability per row and model. Each fold fits a fresh Phase-3 preprocessor and fixed estimator on 16,800 rows, then scores only its 4,200 held-out rows. No full-TRAIN fitted preprocessor enters these folds. Fold feature widths are 103/103/103/100/102, reflecting fold-local category discovery. Logistic converged in 858/876/876/751/912 iterations; each XGBoost fold used 350 rounds.

A separate five-fold TRAIN-only CV compares identity, sigmoid and isotonic on OOF probability/label pairs. Each mapping is fitted without its own probability holdout. Minimum mean Brier selects the method; absolute tolerance 1e-12 permits log-loss and then identity/sigmoid/isotonic simplicity tie breaks. ECE is diagnostic only. The winner is fitted on all 21,000 TRAIN OOF pairs. Both final mappings are frozen before canonical VALIDATION scoring or assessment.

Identity preserves p exactly. Sigmoid uses expit(a × logit(clip(p, 1e-6, 1−1e-6)) + b), constrained to a >= 0 with public SciPy L-BFGS-B. Numerical clipping protects logit only and does not redefine raw probability. Isotonic is increasing with clipping outside its fitted input range. See [ADR 005](decisions/005-calibration-and-model-selection.md) for optimizer, tie and lifecycle details.

## Logistic TRAIN OOF selection

| Method | Mean Brier | Mean log loss | Mean ECE | Mean probability | Observed rate |
| --- | --- | --- | --- | --- | --- |
| identity | 0.135268217 | 0.433354449 | 0.016267314 | 0.221232584 | 0.221190476 |
| sigmoid | 0.135308670 | 0.433406317 | 0.017875025 | 0.221210692 | 0.221190476 |
| isotonic | 0.135268863 | 0.438716831 | 0.015874677 | 0.221152876 | 0.221190476 |

Selected: **identity**. Isotonic's Brier is worse by 6.459244e-7, exceeding the fixed tolerance. This is a very small practical difference, not strong statistical evidence. Isotonic improves ECE slightly but worsens log loss; neither overrides the declared primary metric.

## XGBoost TRAIN OOF selection

| Method | Mean Brier | Mean log loss | Mean ECE | Mean probability | Observed rate |
| --- | --- | --- | --- | --- | --- |
| identity | 0.133056404 | 0.424541222 | 0.017325550 | 0.221100844 | 0.221190476 |
| sigmoid | 0.133090807 | 0.424657060 | 0.017950380 | 0.221203823 | 0.221190476 |
| isotonic | 0.133212151 | 0.431312938 | 0.016834178 | 0.221154065 | 0.221190476 |

Selected: **identity**. Sigmoid and isotonic worsen mean Brier and log loss. Isotonic slightly improves ECE, but that is not the selection objective.

## Versioned final mappings

| Model | Calibration version | Method | TRAIN OOF fit rows | Binary path / SHA-256 |
| --- | --- | --- | --- | --- |
| Logistic | logistic-calibration-1.0.0 | identity | 21,000 | null / null |
| XGBoost | xgboost-calibration-1.0.0 | identity | 21,000 | null / null |

No probability transformation or real-data calibrator binary was created. Non-identity mappings use content-addressed trusted joblib artifacts under ignored artifacts/calibration; synthetic sigmoid/isotonic serialization, reload equality at absolute tolerance 1e-12 and corruption rejection pass.

## Logistic VALIDATION

| Metric | Raw | Reported | Reported − raw |
| --- | --- | --- | --- |
| ROC-AUC | 0.765638177 | 0.765638177 | 0.000000000 |
| Average Precision | 0.519684092 | 0.519684092 | 0.000000000 |
| KS | 0.405350576 | 0.405350576 | 0.000000000 |
| Gini | 0.531276353 | 0.531276353 | 0.000000000 |
| Brier | 0.138791607 | 0.138791607 | 0.000000000 |
| Log loss | 0.441318621 | 0.441318621 | 0.000000000 |
| ECE | 0.016085905 | 0.016085905 | 0.000000000 |
| Mean probability | 0.219725065 | 0.219725065 | 0.000000000 |
| Observed positive rate | 0.221111111 | 0.221111111 | 0.000000000 |

## XGBoost VALIDATION

| Metric | Raw | Reported | Reported − raw |
| --- | --- | --- | --- |
| ROC-AUC | 0.784304404 | 0.784304404 | 0.000000000 |
| Average Precision | 0.556211932 | 0.556211932 | 0.000000000 |
| KS | 0.424438885 | 0.424438885 | 0.000000000 |
| Gini | 0.568608807 | 0.568608807 | 0.000000000 |
| Brier | 0.135284871 | 0.135284871 | 0.000000000 |
| Log loss | 0.428826621 | 0.428826621 | 0.000000000 |
| ECE | 0.011402129 | 0.011402129 | 0.000000000 |
| Mean probability | 0.219568509 | 0.219568509 | 0.000000000 |
| Observed positive rate | 0.221111111 | 0.221111111 | 0.000000000 |

Both raw metric sets reproduce stored Phase-4/5 metadata within 1e-12. All reported-minus-raw deltas are exactly zero, including discrimination: identity did not change rankings, ties, probability quality or endpoint counts.

## Reliability and quality investigation

Ten target quantile bins are computed separately for each model and probability type. Unique internal quantile edges collapse duplicates; ties stay together in the right bin, empty bins are omitted, and constant predictions produce one nonempty bin. ECE is sum(count/N × absolute(mean probability − observed rate)). Actual validation bin count is ten for all four series; the aggregate CSV has 40 rows. Logistic counts are 450 except bins 8/9 with 447/453; XGBoost has 450 in every bin.

Logistic's largest gap is bin 10: mean 0.716762 versus observed 0.668889, gap 0.047873. Bin 6 underpredicts: 0.145370 versus 0.180000. XGBoost's largest gap is bin 10: mean 0.707842 versus observed 0.684444, gap 0.023397; bin 6 is 0.157849 versus 0.180000. Reported bins are identical to raw bins; ECE stays 0.016085905 for Logistic and 0.011402129 for XGBoost. These diagnostics support retaining identity under the declared rule, not perfect calibration.

OOF versus canonical validation means are 0.221233 versus 0.219725 (Logistic) and 0.221101 versus 0.219569 (XGBoost). Standard deviations are 0.195710 versus 0.195350 and 0.197294 versus 0.197299 respectively. Logistic ranges are approximately [9.29e-19, 0.946944] OOF and [3.12e-7, 0.892332] validation; XGBoost ranges are [0.020655, 0.901425] and [0.025090, 0.861990]. These aggregate comparisons reveal no large central distribution discrepancy; they are not a formal distribution-shift test. Mean validation probabilities are within 0.00155 of prevalence 0.221111. Both OOF and validation probabilities have zero exact 0/1 values for each selected mapping.

No selected sigmoid extremes or isotonic plateaus exist because both mappings are identity. Candidate isotonic log loss deteriorates to 0.438717/0.431313 (Logistic/XGBoost); probability calibration therefore cannot be presumed beneficial. No validation metric deteriorated, no ranking changed, and the downstream result agrees with Phase-5 discrimination. Optional calibration-intercept/slope diagnostics are omitted; mandatory reliability/Brier/log-loss/ECE assessment is retained without extra validation fitting.

## Reported-probability comparison

| Reported metric | Logistic | XGBoost | XGBoost − Logistic |
| --- | --- | --- | --- |
| ROC-AUC | 0.765638177 | 0.784304404 | 0.018666227 |
| Average Precision | 0.519684092 | 0.556211932 | 0.036527841 |
| KS | 0.405350576 | 0.424438885 | 0.019088309 |
| Gini | 0.531276353 | 0.568608807 | 0.037332454 |
| Brier | 0.138791607 | 0.135284871 | -0.003506736 |
| Log loss | 0.441318621 | 0.428826621 | -0.012492000 |
| ECE | 0.016085905 | 0.011402129 | -0.004683776 |

**XGBOOST_SELECTED_FOR_DOWNSTREAM**. AUC/AP must be no lower and Brier/log loss no higher, with at least one strict improvement. XGBoost strictly improves all four. No subjective override occurred. ECE and KS/Gini are supplementary. This is NOT final untouched-test confirmation or production approval.

## Paired VALIDATION bootstrap

| XGBoost − Logistic | 95% percentile CI |
| --- | --- |
| roc_auc | 0.011856616 to 0.026106355 |
| average_precision | 0.022063804 to 0.048515345 |
| brier_score | -0.004897304 to -0.002226468 |
| log_loss | -0.016846047 to -0.008589428 |

1,000 requested and successful paired replicates; zero single-class skips; seed 42. Both models and all four metrics use identical row draws with replacement. Percentile intervals condition on the fitted models and development sample; they exclude retraining/model-selection and deployment-shift uncertainty.

## Technical threshold analysis

Selected model: XGBoost. TRAIN OOF max-KS threshold: **0.21430689096450806**, source train_oof_max_ks. Maximum Youden J is approximately 0.436322. Highest finite threshold wins ties within 1e-12; ROC's +infinity sentinel is excluded. The TRAIN-only CSV contains the 19-point 0.05–0.95 grid plus the selected threshold, totaling 20 rows. No VALIDATION threshold optimization occurs.

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

The threshold is NOT a business/lending cut-off. Predicted positives denote a technical classification of the dataset event, not declined applications. Reference 0.50 is retained solely for comparison. No lending action, risk band or internal score is produced.

## Probability and explanation semantics

raw_probability is the underlying classifier's positive-class output. reported_probability is the selected mapping's output. With calibration_method=identity for both models, reported_probability = raw_probability; it is not falsely labeled a transformed calibrated probability. The target remains the dataset-defined next-month default-payment event, not Basel, IFRS 9, regulatory, 12-month or verified 90-DPD PD.

Future SHAP explanations of the underlying model must not automatically be claimed to sum to the calibrated/reported probability. Identity alone does not establish SHAP output units or additivity in probability space. SHAP, score mapping and all Phase-7 functionality remain unimplemented.

## Reproducibility and limitations

The initial real workflow ran twice; all five Phase-6 metadata files were byte-identical, including the retained manifest timestamp. The subsequent pre-commit governance verification reused the reviewed threshold without optimization and preserved all four result files byte-for-byte. Only the current Phase-6 manifest's source provenance and timestamp changed to record the governance fix; historical Phase-4/5 metadata remains byte-identical to HEAD. Runtime: Python 3.14.6, sklearn 1.8.0 and XGBoost 3.2.0. Reproducibility across other runtimes/hardware is not guaranteed. No customer OOF/validation probabilities, predictions or matrices were persisted.

Overlapping OOF training sets and previously selected TRAIN hyperparameters mean calibration-selection CV is not fully nested end-to-end validation. Threshold diagnostics can be optimistic because the final mapping fits all OOF labels. VALIDATION is reused development data; untouched TEST remains necessary later. Quantile ECE depends on binning, and small differences need not generalize. The historical Taiwan snapshot has unresolved codes, no verified point-in-time reconstruction and no out-of-time split. Demographic exclusion does not prove fairness. No regulatory or production readiness is claimed.

TEST SET WAS NOT EVALUATED. TEST SET REMAINS SEALED.

## Reproduce

```powershell
.venv\Scripts\python.exe -m credit_risk.modeling.calibration
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
```

Existing verified data, Phase-3 preprocessing and Phase-4/5 model artifacts are prerequisites. The complete reproduction sequence and test evidence are in the [Phase-6 completion report](phase_reports/phase_06_completion_report.md). No commit or next-phase work is automatic.
