# Internal risk score

## Purpose

A versioned project-specific representation of reported default probability: `internal-risk-score-1.0.0`. It is not a new predictive model, FICO score, regulatory score, creditworthiness certification or business-decision policy. No risk bands or lending cutoff are defined.

## Probability Source

Use `reported_probability` from frozen `xgboost-challenger-1.0.0` and `xgboost-calibration-1.0.0` (identity). Reported probability currently equals raw probability for the dataset's next-month default-payment event; no invented 12-month or regulatory horizon. The original probability is retained.

## Score Formula

`S = offset + factor * ln((1-p)/p)` for reported probability p, using only numerical epsilon protection below. Canonical score is continuous float64. Optional display score rounds to nearest integer, ties to even; it does not change the underlying probability or canonical score. Changing V1 parameters requires a new reviewed version.

## Base Score

600.

## Base Odds

Good:bad odds 50:1, equivalent to p = 1/51. These are representation parameters, not empirical population odds.

## PDO

20 points to double good:bad odds. Increasing odds from 50:1 to 100:1 raises score from 600 to 620.

## Factor and Offset

`factor = 20 / ln(2) = 28.85390081777927`.

`offset = 600 - factor * ln(50) = 487.1228762045055`.

## Direction

Higher probability strictly lowers score on the unclipped interval. Exact probability ties retain exact score ties. Numerical clipping can create ties at extreme tails. There is no cosmetic score range: values below zero or above familiar consumer-score ranges are permitted.

## Worked Mathematical Examples

Hypothetical probabilities only: p = 1/51 maps to 600; p = 1/101 maps to 620; p = 0.5 maps to offset 487.122876205. These are mathematical demonstrations, not observed customer data or lending recommendations.

## Inverse Mapping

`p = sigmoid((offset - S)/factor)`. Actual VALIDATION maximum round-trip error: 4.4408920985e-16. At clipped endpoints the inverse returns the protected probability rather than the original 0/1. Probability AUC and AUC(-score) both equal 0.7843044036157966; difference zero. Actual inverse ranking including ties passed.

## Score Distribution

TRAIN OOF: unavailable. Phase 6 retained aggregate OOF diagnostics only; nonlinear score moments and quantiles cannot be recovered from them. The project owner explicitly chose no retraining. No full-TRAIN in-sample scores were substituted.

VALIDATION uses all 4,500 rows. Standard deviation is population standard deviation (ddof=0); quantiles use NumPy's linear interpolation. Epsilon 1e-12 protects logarithms by clipping p to [epsilon, 1-epsilon] only for score computation; invalid, empty, NaN/infinite or out-of-range probabilities fail. Actual clipping count/rate: zero/zero.

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

## Score Deciles

Stable sort by descending continuous score, with original validation row position breaking exact ties, followed by ten equal-count partitions. Each row appears exactly once; ties may cross a boundary. Decile 1 has highest scores/lowest modeled risk; decile 10 has lowest scores/highest modeled risk. These bins are sample-specific diagnostics, not reusable thresholds or risk bands. Observed rates need not be perfectly monotonic because of sampling noise.

| Decile | Count | Score min | Score max | Mean score | Mean reported probability | Observed default rate |
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

## Technical Threshold Equivalent

Frozen Phase-6 probability threshold 0.21430689096450806 maps to `technical_reference_score = 524.6086295466075`. Source: `phase6_train_oof_max_ks_probability_threshold`. This is a diagnostic reference, explicitly not a business cutoff or underwriting decision. No threshold was optimized in Phase 7.

## SHAP Score-Point Decomposition

Binary logistic raw probability is sigmoid(margin); current calibration is identity. Thus log good:bad odds = -margin and `score = offset - factor * margin`.

With `margin = base_margin + sum(shap_i)`, use `score_base_value = offset - factor * base_margin`, and `score_point_i = -factor * shap_i`. Aggregate signed SHAP locally to sources/families before the same conversion. Positive default-risk SHAP therefore contributes negative score points.

The largest measured score reconstruction residual across transformed, source and family levels is 0.000121609856023 points, below 1e-3 tolerance. Mean source residual is 2.17157377108e-05. This is an exact algebraic mapping with measured native floating-point error, not a claim of bitwise exact sums.

The decomposition guard requires binary logistic objective, raw-margin SHAP, identity calibration, V1 log-odds score and no probability clipping. Otherwise `score_point_decomposition_supported=false`, without additive score outputs. Raw-margin SHAP and conversion from a valid reported probability remain independent capabilities; the current frozen local/CLI consumer rejects a changed calibration contract.

## Limitations

Static historical data, no true OOT split, reused validation and unopened TEST limit generalization claims. No fairness, causality, regulatory, FICO or lending-policy claim follows from this representation. TRAIN OOF score statistics remain unavailable by explicit owner instruction. No model was retrained or reselected for Phase 7. No customer-level scores or explanations are persisted; only aggregate diagnostics are written. Model and preprocessor binaries remain trusted, local and ignored. No explainer binary is needed.
