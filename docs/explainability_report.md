# Explainability report

## Objective

Explain the frozen selected XGBoost model in declared units, validate the explanation numerically, and provide aggregate importance and in-memory diagnostic local drivers without changing training, calibration, model selection or technical thresholds.

## Selected Model

`xgboost-challenger-1.0.0`, binary:logistic, XGBoost 3.2.0. Artifact SHA-256 `2900f0cfe341400daeffeed7b0ef212d0a317113a657a4fcf73c332caec755ef`. Preprocessor SHA-256 `e8f6ce776bd44c48871c585c5d472676ad8c418da39c513c1019bf36070ee8b4`. Calibration is `xgboost-calibration-1.0.0`, identity, with no calibrator binary. Phase-6 model selection and all nine XGBoost validation metrics reproduce unchanged.

## Explainability Population

All 4,500 VALIDATION rows and 103 transformed features. No TRAIN predictions or TEST explanations. Dataset SHA-256 `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`. The data adapter verifies structural splits and drops TRAIN/TEST before feature transformation for this consumer. Real row-level probabilities, scores, SHAP arrays and reasons exist only in memory and are never persisted.

## Why Tree SHAP

SHAP 0.51.0 supplies the public `shap.TreeExplainer` API for the frozen tree model. Its Python minimum preserves this project's Python 3.11 minimum, and the installed wheel works with the actual Python 3.14.6/XGBoost 3.2.0 runtime. Explicit path-dependent semantics use the model's recorded training path counts, with no background dataset supplied and no model fit. No explainer binary is serialized. See [SHAP TreeExplainer documentation](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html) and [SHAP 0.51.0](https://pypi.org/project/shap/0.51.0/).

## Explained Output Space

`model_output="raw"`, `feature_perturbation="tree_path_dependent"`, exact Tree SHAP (`approximate=False`). Values are contributions to raw default log-odds. Canonical CSR values are materialized densely for both native XGBoost and SHAP, preserving trained zero semantics. They do not sum directly to raw or calibrated probability.

## SHAP Additivity Validation

Native raw margin is obtained independently through `predict(..., output_margin=True)`. Base margin plus all 103 signed SHAP values reproduces it with maximum absolute residual 4.25636244472e-06, mean 7.48812189057e-07, p50 5.16367435921e-07, p95 2.09110512515e-06, p99 2.653722986e-06. All pass absolute margin tolerance 1e-5, independently of SHAP's own additivity check.

## Probability Reconstruction

`sigmoid(raw_margin)` reproduces native positive-class probability: maximum error 7.20322632652e-08, mean 6.99643408433e-09, passing 1e-7. `sigmoid(base + sum(SHAP))` maximum error is 4.2400324457e-07; its bound is margin tolerance / 4 + probability tolerance. Native float32 arithmetic accounts for small residuals; there is no probability-space additivity claim.

## Transformed Feature Lineage

All 103 unique names exactly match the committed Phase-3 order/trace: 39 numeric plus 64 one-hot columns, derived from 45 inputs. Missing mappings: zero. Identifier, target and demographic predictors: zero. Standardized numeric contributions describe the model's transformed inputs; no unit conversion into currency is implied. Source attribution retains engineered features as sources, with original canonical origins available in the Phase-3 trace.

## Source-Level Aggregation

For each row, sum signed child-column contributions sharing the same Phase-3 `input_feature`, then calculate each source's global mean absolute contribution. This produces 45 source features. It is not the sum of child mean absolute importances: opposing values can cancel locally. Maximum row-total residual against transformed sums: 0.0. Full signed sources are available in memory; top-k drivers need not reconstruct the full margin alone.

## Feature-Family Aggregation

Apply the same local signed summation to seven documented families: credit_limit, repayment_status, bill_amount, payment_amount, bill_to_limit, payment_to_limit and delay_summary. Prefixes map the corresponding monthly/summary features; the three documented-delay summaries form delay_summary. This explanation grouping is versioned as `source_family_signed_sum_v1` and is more granular than the historical native-gain grouping. No prior gain metadata changes. Maximum row-total residual: 0.0.

## Global SHAP Results

Rank by descending mean absolute margin contribution, breaking ties by ascending feature name. Normalization is within each aggregation level; zero-total importance is represented by zeros. The artifact records means, signed means, normalized magnitudes and ranks for all features. Tables show top ten transformed/source features and all families.

| Rank | Feature | Mean absolute margin SHAP | Mean signed margin SHAP | Normalized importance |
| --- | --- | ---: | ---: | ---: |
| 1 | `numeric__months_with_documented_delay` | 0.326189915 | -0.080610505 | 0.159748 |
| 2 | `numeric__max_documented_delay` | 0.257720088 | -0.006763552 | 0.126216 |
| 3 | `numeric__recent_documented_delay_flag` | 0.221549400 | -0.090698657 | 0.108502 |
| 4 | `numeric__bill_amount_std` | 0.073593053 | -0.007387203 | 0.036041 |
| 5 | `numeric__credit_limit` | 0.073320612 | -0.010527729 | 0.035908 |
| 6 | `repayment__repayment_status_2005_09_status_2` | 0.073225777 | -0.022906877 | 0.035862 |
| 7 | `repayment__repayment_status_2005_09_status_1` | 0.063872836 | 0.026210494 | 0.031281 |
| 8 | `numeric__bill_amount_2005_09` | 0.056085503 | -0.006705196 | 0.027467 |
| 9 | `numeric__bill_to_limit_2005_08` | 0.055891157 | -0.007209040 | 0.027372 |
| 10 | `numeric__payment_amount_2005_04` | 0.054120229 | -0.001728133 | 0.026505 |

| Rank | Feature | Mean absolute margin SHAP | Mean signed margin SHAP | Normalized importance |
| --- | --- | ---: | ---: | ---: |
| 1 | `months_with_documented_delay` | 0.326189915 | -0.080610505 | 0.167537 |
| 2 | `max_documented_delay` | 0.257720088 | -0.006763552 | 0.132370 |
| 3 | `recent_documented_delay_flag` | 0.221549400 | -0.090698657 | 0.113792 |
| 4 | `repayment_status_2005_09` | 0.153144796 | -0.010481783 | 0.078658 |
| 5 | `bill_amount_std` | 0.073593053 | -0.007387203 | 0.037799 |
| 6 | `credit_limit` | 0.073320612 | -0.010527729 | 0.037659 |
| 7 | `bill_amount_2005_09` | 0.056085503 | -0.006705196 | 0.028807 |
| 8 | `bill_to_limit_2005_08` | 0.055891157 | -0.007209040 | 0.028707 |
| 9 | `payment_amount_2005_04` | 0.054120229 | -0.001728133 | 0.027797 |
| 10 | `bill_to_limit_2005_09` | 0.053883630 | -0.006991986 | 0.027676 |

| Rank | Feature | Mean absolute margin SHAP | Mean signed margin SHAP | Normalized importance |
| --- | --- | ---: | ---: | ---: |
| 1 | `delay_summary` | 0.713980984 | -0.178072714 | 0.466748 |
| 2 | `payment_amount` | 0.207690520 | -0.035965749 | 0.135773 |
| 3 | `bill_to_limit` | 0.190300417 | -0.028126337 | 0.124404 |
| 4 | `repayment_status` | 0.157955354 | -0.016301717 | 0.103260 |
| 5 | `bill_amount` | 0.145616367 | -0.014982690 | 0.095193 |
| 6 | `credit_limit` | 0.073320612 | -0.010527729 | 0.047932 |
| 7 | `payment_to_limit` | 0.040828456 | -0.006304388 | 0.026691 |

Documented-delay summaries dominate the magnitude ranking in this validation sample. This measures contribution magnitude, not a universal direction: an individual row's signed contribution determines direction. Related repayment, amount and ratio features can share attribution.

## XGBoost Gain vs SHAP

Top-ten overlap: 5/10. Shared features are the three delay summaries and September repayment categories 1 and 2. Gain measures average training split-loss improvement; these SHAP magnitudes describe validation predictions under the declared path-dependent semantics. Their rankings answer different questions. This comparison is diagnostic only and makes no feature-selection/model change; no optional rank correlation was calculated.

## Local Diagnostic Reason Codes

`explain_record` accepts exactly the 19 financial fields and uses frozen engineering/preprocessing/model inference. It returns raw and reported probabilities, margin/base, continuous/display score, versions, all 45 signed source contributions and up to five positive and five negative source drivers. Positive margin contributions increase modeled default risk and lower score points; negative contributions do the reverse. Sort by signed magnitude within direction, then source name lexically; omit zero drivers. No demographics, customer identifier, target, causal label or adverse-action designation enters the schema.

SYNTHETIC / DEMONSTRATION ONLY: fabricated limit 200,000, six repayment codes -1, bills/payments 20,000; a variant changes latest repayment code to 2 and latest payment to zero; another changes six bills to 180,000. These do not represent real people. All three passed 45-source local reconstruction. Only aggregate pass/residual fields are saved; no customer examples are exported.

## Interpretation Rules

Drivers describe modeled contributions relative to the SHAP base under the chosen perturbation semantics. They do not establish causal effects, recommended customer actions or a legal reason for credit denial. Magnitude rankings are not directions, and top-five excerpts omit other contributors. Undocumented repayment codes retain their literal categories; no new financial meaning is assigned.

## Calibration Boundary

`base margin + sum(SHAP margin) ≈ raw margin`; sigmoid then gives raw probability. Current identity calibration makes raw probability equal reported probability. SHAP values never directly sum to either probability. For future non-identity calibration, margin explanations and score-from-reported-probability remain possible as independent operations, but the current local/CLI contract fails clearly pending a new integration and exact additive score-point output is disabled by the score guard.

## SHAP-to-Score-Point Mathematics

With identity calibration and no numerical clipping, `score = offset - factor * margin`; therefore `score_base = offset - factor * base_margin` and `score_point_i = -factor * shap_margin_i`. Transformed, source and family sums all reconstruct the score within 1e-3 points. Maximum measured residual: 0.000121609856023; mean source residual: 2.17157377108e-05. Exact refers to the algebra; the native float32 probability/margin outputs cause the reported numerical residual. See [internal risk score](internal_risk_score.md).

## Regulatory / Causality Limitations

Historical/static UCI data and reused development validation do not establish OOT performance, causality, fairness, regulatory explainability or production readiness. Feature correlation and path-dependent attribution can alter how credit is shared. Excluding demographics does not remove proxies. These are model diagnostics, not regulatory adverse-action reasons. The score is project-specific.

## Test Set Policy

TEST SET WAS NOT EVALUATED. TEST SET REMAINS SEALED. No TEST probability, SHAP, score, reason code or performance metric was produced. The existing preparation CLI's structural checks remain separate from predictive evaluation.

## Phase-8 Boundary

API, PostgreSQL, audit persistence and business rules remain unimplemented. A future explicitly requested phase should expose separate model/calibration/explanation/score identities and declared units. No lending policy, risk bands, authentication, Docker, monitoring or final TEST evaluation is added here.
