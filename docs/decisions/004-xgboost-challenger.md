# Decision

Phase 5 uses XGBoost as a nonlinear challenger to the committed Logistic Regression baseline. Version: `xgboost-challenger-1.0.0`; library: xgboost 3.2.0. Status: implemented for owner technical review. No final production champion is selected.

# Context and Rationale

Gradient-boosted trees can learn nonlinear relationships and interactions that a linear log-odds baseline may miss. This makes XGBoost a useful tabular-data challenger, not a guarantee of superiority. The target, eligible population, split, financial policy and final 103 transformed values remain the same as Phase 4.

Version 3.2.0 provides a working Windows CPU wheel and supports Python >=3.10, preserving this project's >=3.11 requirement. Existing numerical dependencies remain unchanged. The newer 3.4.1 release requires Python >=3.12; upgrading the project's minimum Python version was unnecessary. Installed versions and provenance are recorded.

# Search Design

TRAIN-only RandomizedSearchCV: 24 candidates, shuffled stratified 4-fold CV, seed 42, n_jobs=1, error_score=raise, return_train_score=False. Score ROC-AUC and Average Precision; never accuracy. The authoritative search space and invariant parameters are in configs/xgboost.yaml. There are 96 candidate-fold fits, one search winner refit, one final canonical fit and one temporary sensitivity fit: 99 XGBoost fits per full workflow.

Every CV fit constructs a fresh Phase-3 preprocessor. A small sklearn adapter discards y at the unsupervised boundary because the original preprocessor deliberately rejects target arguments. Medians, scaling and categories are learned only from that fold's training rows. The full-TRAIN Phase-3 fitted artifact is never supplied to CV. Stateless engineering is reused before CV. Project VALIDATION is reserved for final assessment and TEST remains sealed.

Selection uses greatest mean CV ROC-AUC. Scores tied within float64 machine epsilon use greater mean CV AP, then smaller depth, fewer estimators and stronger regularization in lexicographic reg_lambda/reg_alpha/gamma order. An otherwise identical tie uses the earlier sampled candidate. A callable refit implements this rule without subjective override.

# Representation and Zero Semantics

The final challenger uses the verified Phase-3 preprocessor and 103 ordered features. XGBoost trees interpret absent sparse entries as missing; the baseline interprets them as zero. CV and final XGBoost fitting/prediction therefore materialize the same values as dense arrays, with default missing=NaN. This changes storage, not features or numerical values. TRAIN occupies about 17.3 MB as float64, acceptable at this project scale. See the [official sparse/dense FAQ](https://xgboost.readthedocs.io/en/release_3.2.0/faq.html).

# Primary and Sensitivity Models

The primary search/final challenger uses objective=binary:logistic, eval_metric=logloss, tree_method=hist, device=cpu, centralized seed, n_jobs=1 and scale_pos_weight=1.0. No early stopping, validation fitting, TEST scoring or resampling occurs.

After the canonical configuration is fixed, one temporary weighted model uses the same selected parameters and TRAIN negative/positive ratio. It is evaluated only on VALIDATION and never replaces the canonical serialized artifact. Weighting can change the probability scale and does not establish calibrated PD.

# Alternatives Considered

- Reusing full-TRAIN preprocessing inside CV: rejected because it leaks fold holdout statistics.
- Project-validation early stopping: rejected to reserve that partition for comparison.
- Including class weight in search: rejected to isolate weighting as a separate sensitivity diagnostic.
- Larger search or additional model families: unnecessary and outside the bounded scope.
- Sparse XGBoost ingestion without zero handling: changes zero semantics; use dense values instead.
- Final production model selection: deferred to Phase-6 calibration analysis and later requirements.

# Consequences

XGBoost adds nonlinear capacity but loses direct coefficient interpretability. Native gain is a training split diagnostic, not causality, SHAP, a local customer reason or a regulatory adverse-action explanation. Correlated fields distribute importance; gain is not an additive explanation.

Validation point estimates determine one of the three specified provisional discrimination statuses. A paired 1,000-resample validation bootstrap uses identical row indices for both models. This conditions on the fitted models and does not capture search/training/population-shift uncertainty. Raw probabilities still require Phase-6 assessment. No calibration, SHAP, score or lending policy is implemented.

The canonical model is saved in native JSON under ignored artifacts/models with a version and SHA-256 filename, then reloaded to check TRAIN/VALIDATION probabilities. Only trusted XGBoost-produced models may be loaded; see [native model IO guidance](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/saving_model.html). Aggregate metadata is tracked; customer rows/probabilities/matrices are not. Repeated timing measurements can differ even when candidates, scores and model bytes reproduce.
