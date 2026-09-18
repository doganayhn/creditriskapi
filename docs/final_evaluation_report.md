# Final Evaluation

## Evaluation Policy

TEST remained predictively sealed through Phases 1–9. Phase 10 evaluates the frozen system. XGBoost was selected on development VALIDATION before this evaluation; TEST never selects or tunes anything. Reproduction checks identical aggregate bytes and retains the original publication timestamp.

## Frozen Pre-Test Contract

Pre-unseal Git HEAD: `43082644706e321225ba2d96fdfa01090ac920e8`. The complete component/source/config/metadata hashes and predeclared diagnostic policy are in [the pre-unseal snapshot](../data/metadata/final_pre_unseal_snapshot.json).

| component | identity |
| --- | --- |
| dataset SHA-256 | 30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933 |
| split | sorted_id_two_stage_stratified_v1 |
| seed | 42 |
| preprocessing | train_median_scale_onehot_v1 |
| preprocessor SHA-256 | e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4 |
| Logistic SHA-256 | a05feadd329d36515f3e66f3ca984af52401d90702a7fea2bf3f71834c2fa07c |
| XGBoost SHA-256 | 2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef |
| calibration | identity for both models |
| score | internal-risk-score-1.0.0 |
| explainability | xgboost-shap-1.0.0 |

## TEST Population

Existing stratified random TEST: 4,500 rows; 3,504 negatives; 996 positives; observed default rate 22.13333333%. TRAIN 21,000 and VALIDATION 4,500 remain separate. This is not temporal or out-of-time validation.

## Target Definition

`default_next_month` means the workbook's default payment next month. It does not establish 90+ DPD, a 12-month Basel PD, or IFRS 9 lifetime default. The public static dataset describes Taiwan credit-card clients in 2005.

## Final XGBoost Results

| metric | TEST |
| --- | --- |
| roc_auc | 0.78014627 |
| average_precision | 0.55493342 |
| ks | 0.43652693 |
| gini | 0.56029254 |
| brier_score | 0.13517626 |
| log_loss | 0.43003453 |
| mean_predicted_probability | 0.22103783 |
| observed_positive_rate | 0.22133333 |
| ece | 0.018104312 |

## Final Logistic Baseline Results

| metric | TEST |
| --- | --- |
| roc_auc | 0.76032125 |
| average_precision | 0.52981208 |
| ks | 0.40494512 |
| gini | 0.5206425 |
| brier_score | 0.13815888 |
| log_loss | 0.44034703 |
| mean_predicted_probability | 0.22051946 |
| observed_positive_rate | 0.22133333 |
| ece | 0.013705673 |

## Paired Model Comparison

XGBoost minus Logistic; lower Brier/log loss is better. Same resampled customers for both models. Descriptive comparison only; XGBoost remains selected.

| metric | delta | 95% CI |
| --- | --- | --- |
| roc_auc | 0.019825019 | [0.01259593267182057, 0.02776220752932609] |
| average_precision | 0.025121344 | [0.01276574648749785, 0.03683073927217406] |
| ks | 0.031581807 | not requested |
| brier_score | -0.0029826241 | [-0.004322056572153404, -0.0017884316541933378] |
| log_loss | -0.010312502 | [-0.014268838128956267, -0.006639594393630964] |

## Discrimination

ROC AUC, AP, KS=max(TPR−FPR), and Gini=2×AUC−1 reuse the development definitions. Validation-to-TEST differences below are sampling diagnostics, not evidence of no overfitting.

| model | metric | VALIDATION | TEST | TEST minus VALIDATION |
| --- | --- | --- | --- | --- |
| logistic | roc_auc | 0.76563818 | 0.76032125 | -0.0053169259 |
| logistic | average_precision | 0.51968409 | 0.52981208 | 0.010127987 |
| logistic | ks | 0.40535058 | 0.40494512 | -0.00040545303 |
| logistic | brier_score | 0.13879161 | 0.13815888 | -0.0006327238 |
| logistic | log_loss | 0.44131862 | 0.44034703 | -0.00097159038 |
| logistic | ece | 0.016085905 | 0.013705673 | -0.0023802317 |
| xgboost | roc_auc | 0.7843044 | 0.78014627 | -0.0041581336 |
| xgboost | average_precision | 0.55621193 | 0.55493342 | -0.0012785098 |
| xgboost | ks | 0.42443888 | 0.43652693 | 0.012088045 |
| xgboost | brier_score | 0.13528487 | 0.13517626 | -0.00010861231 |
| xgboost | log_loss | 0.42882662 | 0.43003453 | 0.0012079071 |
| xgboost | ece | 0.011402129 | 0.018104312 | 0.0067021838 |

## Probability Quality

Brier and log loss measure the frozen reported probabilities. Identity is a development decision, not a claim of perfect calibration. Observed rates and predicted means are reported above.

## Calibration

Raw and reported probabilities match exactly for both models (maximum absolute difference 0). ECE uses the existing Phase-6 ten quantile bins: duplicate boundaries collapse, ties remain together and empty bins are omitted. No calibrator was fitted on TEST.

| model | bin | count | minimum_probability | maximum_probability | mean_probability | observed_default_rate | absolute_calibration_gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | 1 | 450 | 1.2414075e-08 | 0.075025238 | 0.052752875 | 0.053333333 | 0.00058045837 |
| logistic | 2 | 450 | 0.075104905 | 0.09448565 | 0.085483468 | 0.082222222 | 0.0032612462 |
| logistic | 3 | 450 | 0.094495715 | 0.10970515 | 0.10275761 | 0.11333333 | 0.010575727 |
| logistic | 4 | 450 | 0.10970528 | 0.12280749 | 0.1161334 | 0.12222222 | 0.0060888173 |
| logistic | 5 | 450 | 0.12283351 | 0.13655189 | 0.12956298 | 0.15333333 | 0.023770354 |
| logistic | 6 | 450 | 0.13655704 | 0.1608301 | 0.14775968 | 0.15777778 | 0.010018101 |
| logistic | 7 | 450 | 0.1608384 | 0.21812688 | 0.18438903 | 0.18 | 0.0043890336 |
| logistic | 8 | 450 | 0.21825502 | 0.31526044 | 0.26451767 | 0.23333333 | 0.031184339 |
| logistic | 9 | 450 | 0.31545233 | 0.56903169 | 0.41176906 | 0.43333333 | 0.02156427 |
| logistic | 10 | 450 | 0.5698381 | 0.89824132 | 0.71006883 | 0.68444444 | 0.025624386 |
| xgboost | 1 | 450 | 0.023769366 | 0.0564433 | 0.0452577 | 0.044444444 | 0.00081325555 |
| xgboost | 2 | 450 | 0.056507505 | 0.077434838 | 0.066714304 | 0.075555556 | 0.0088412518 |
| xgboost | 3 | 450 | 0.077455446 | 0.096700042 | 0.087010306 | 0.071111111 | 0.015899195 |
| xgboost | 4 | 450 | 0.096732743 | 0.12008624 | 0.10853261 | 0.13111111 | 0.022578496 |
| xgboost | 5 | 450 | 0.12013161 | 0.14427505 | 0.13204582 | 0.12888889 | 0.0031569326 |
| xgboost | 6 | 450 | 0.14430627 | 0.17541423 | 0.1587434 | 0.19777778 | 0.039034379 |
| xgboost | 7 | 450 | 0.1754317 | 0.23250045 | 0.20094666 | 0.17333333 | 0.027613328 |
| xgboost | 8 | 450 | 0.23262468 | 0.33623204 | 0.27968382 | 0.26 | 0.019683817 |
| xgboost | 9 | 450 | 0.33676136 | 0.57988799 | 0.42734394 | 0.44888889 | 0.021544953 |
| xgboost | 10 | 450 | 0.5810948 | 0.86199474 | 0.70409974 | 0.68222222 | 0.021877517 |

## Frozen Technical Threshold

**TECHNICAL REFERENCE ONLY.** The unchanged TRAIN OOF max-KS threshold is 0.21430689096450806. It is not a lending cutoff, recommended threshold or business policy. Phase 6 has no independent threshold version; its selection-manifest checksum identifies this reference.

| metric | value |
| --- | --- |
| label | TECHNICAL REFERENCE ONLY |
| business_policy | False |
| threshold | 0.21430689 |
| predicted_positive_count | 1464 |
| predicted_positive_rate | 0.32533333 |
| tn | 2688 |
| fp | 816 |
| fn | 348 |
| tp | 648 |
| precision | 0.44262295 |
| recall | 0.65060241 |
| specificity | 0.76712329 |
| f1 | 0.52682927 |
| false_positive_rate | 0.23287671 |
| false_negative_rate | 0.34939759 |

## Internal Score

Frozen base score 600, good:bad odds 50:1, PDO 20, epsilon 1e-12. Higher probability means lower score. This internal transformation is not FICO or a lending policy. Standard deviation uses population ddof=0; quantiles use linear interpolation.

| diagnostic | value |
| --- | --- |
| inverse_ranking_verified | True |
| probability_roc_auc | 0.78014627 |
| negative_score_roc_auc | 0.78014627 |
| auc_absolute_difference | 0 |
| inverse_max_absolute_error | 4.4408921e-16 |
| probability_clipping_count | 0 |

| statistic | value |
| --- | --- |
| count | 4500 |
| mean | 531.7552 |
| std | 32.560549 |
| min | 434.26376 |
| max | 594.32381 |
| probability_clipping_count | 0 |
| probability_clipping_rate | 0 |
| p01 | 450.16867 |
| p05 | 462.17656 |
| p10 | 477.80857 |
| p25 | 514.7169 |
| p50 | 538.48573 |
| p75 | 554.94894 |
| p90 | 568.35629 |
| p95 | 574.36588 |
| p99 | 583.74006 |

## Score Deciles

Decile 1 = lowest score/highest modeled risk; decile 10 = highest score/lowest risk. Stable existing split position breaks ties. These equal-count evaluation groups are not business risk bands.

| decile | count | min_score | max_score | mean_score | mean_reported_probability | observed_default_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 450 | 434.26376 | 477.67988 | 461.58155 | 0.70409974 | 0.68222222 |
| 2 | 450 | 477.82287 | 506.67891 | 495.73834 | 0.42734394 | 0.44888889 |
| 3 | 450 | 506.74731 | 521.56144 | 514.55123 | 0.27968382 | 0.26 |
| 4 | 450 | 521.58152 | 531.77747 | 527.0438 | 0.20094666 | 0.17333333 |
| 5 | 450 | 531.78095 | 538.48209 | 535.28415 | 0.1587434 | 0.19777778 |
| 6 | 450 | 538.48938 | 544.57631 | 541.49467 | 0.13204582 | 0.12888889 |
| 7 | 450 | 544.5887 | 551.58441 | 547.93787 | 0.10853261 | 0.13111111 |
| 8 | 450 | 551.59521 | 558.60648 | 555.00547 | 0.087010306 | 0.071111111 |
| 9 | 450 | 558.6148 | 568.35281 | 563.36049 | 0.066714304 | 0.075555556 |
| 10 | 450 | 568.38758 | 594.32381 | 575.55442 | 0.0452577 | 0.044444444 |

## Lift / Gains

Same risk-descending order as the deciles. Cumulative lift = cumulative observed rate / overall observed rate.

| decile | cumulative_count | cumulative_population_percentage | cumulative_defaults_captured | cumulative_default_capture_percentage | cumulative_lift |
| --- | --- | --- | --- | --- | --- |
| 1 | 450 | 10 | 307 | 30.823293 | 3.0823293 |
| 2 | 900 | 20 | 509 | 51.104418 | 2.5552209 |
| 3 | 1350 | 30 | 626 | 62.851406 | 2.0950469 |
| 4 | 1800 | 40 | 704 | 70.682731 | 1.7670683 |
| 5 | 2250 | 50 | 793 | 79.618474 | 1.5923695 |
| 6 | 2700 | 60 | 851 | 85.441767 | 1.4240295 |
| 7 | 3150 | 70 | 910 | 91.365462 | 1.3052209 |
| 8 | 3600 | 80 | 942 | 94.578313 | 1.1822289 |
| 9 | 4050 | 90 | 976 | 97.991968 | 1.0887996 |
| 10 | 4500 | 100 | 996 | 100 | 1 |

## SHAP Technical Validation

First 32 rows in the existing TEST order, predeclared before unsealing. Tree SHAP remains path-dependent raw-margin attribution. Only aggregate residuals are published; global interpretation remains Phase-7 VALIDATION-based. SHAP is noncausal and does not add directly to probability.

| check | aggregate |
| --- | --- |
| additivity | {'max_absolute_error': 2.087559551000595e-06, 'mean_absolute_error': 7.753480986139039e-07, 'p50_absolute_error': 6.796326488256454e-07, 'p95_absolute_error': 2.011338438023813e-06, 'p99_absolute_error': 2.073464638669975e-06} |
| probability_reconstruction | {'max_absolute_error': 4.5319165642432324e-08, 'mean_absolute_error': 8.782621651638733e-09, 'p50_absolute_error': 3.4859401962239467e-09, 'p95_absolute_error': 3.1715600604109704e-08, 'p99_absolute_error': 4.481592173588567e-08} |
| shap_linked_probability_reconstruction | {'max_absolute_error': 1.9434926157302357e-07, 'mean_absolute_error': 7.719179684643682e-08, 'p50_absolute_error': 7.048121847957889e-08, 'p95_absolute_error': 1.722012469493328e-07, 'p99_absolute_error': 1.895404353999264e-07} |
| sample_count | 32 |
| sample_policy | first rows in existing deterministic TEST order |
| score_point_decomposition_supported | True |
| score_point_max_absolute_residual | 6.0062894e-05 |
| score_point_mean_absolute_residual | 2.2044168e-05 |

## Subgroup Diagnostics

Sex, age, education and marital-status values come from the aligned, separate review frame. Literal raw categories and individual ages are preserved. Minimum n=100; smaller groups have unavailable metrics, and single-class groups have undefined AUC. Demographics never enter inference. See [subgroup diagnostics](subgroup_diagnostics.md) and the aggregate CSV. These results do not certify fairness or establish causality.

## Statistical Uncertainty

1000 requested / 1000 valid / 0 skipped single-class replicates; seed 42. paired row bootstrap with replacement; percentile 95%; linear interpolation. Intervals condition on this frozen model and historical sample; they exclude training, temporal and deployment uncertainty.

| XGBoost metric | 95% CI |
| --- | --- |
| roc_auc | [0.7627072303638124, 0.79666808856661] |
| average_precision | [0.5242178097008217, 0.5875282476873623] |
| brier_score | [0.12851859526912665, 0.14240428288419854] |
| log_loss | [0.4128780665821535, 0.4492039829419416] |

## Limitations

Historical static Taiwan 2005 data, selection of existing credit-card clients, unresolved category semantics, no modern OOT validation and no production/regulatory certification. Subgroup uncertainty and proxies remain. See [limitations](limitations.md) and [model card](model_card.md). Row-level TEST arrays remain in memory only.

## What Was NOT Done

No retraining, preprocessing refit, calibration fit, TEST tuning, model reselection, new threshold, new score parameters, lending decision, credit-limit recommendation, risk bands, regulatory validation, cloud deployment or frontend.
