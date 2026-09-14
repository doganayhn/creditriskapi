# ADR 005 — TRAIN OOF calibration and downstream model selection

Date: 2026-09-14. Status: Implemented in Phase 6; owner technical review precedes the repository checkpoint.

## Context

Phase 4 and Phase 5 provide fixed Logistic Regression and unweighted XGBoost artifacts for the same dataset/split/feature contract. A nonlinear model's discrimination advantage does not establish probability quality. Calibration must not fit or select on project VALIDATION, and TEST must remain sealed. Underlying hyperparameters are frozen.

## Decision

Generate one raw OOF probability for every TRAIN row and model using five stratified shuffled folds with centralized seed 42. Fit fresh Phase-3 preprocessing and the fixed estimator on each fold's training rows. Only the held-out rows receive OOF predictions. Never reuse the full-TRAIN fitted preprocessor inside these folds. Canonical full-TRAIN artifacts are retained for subsequent validation assessment.

Run a separate five-fold stratified TRAIN-only CV over the OOF probability/label pairs. Candidates are exactly identity, sigmoid and isotonic. Identity preserves probability exactly. Sigmoid computes expit(a × logit(clip(p, 1e-6, 1−1e-6)) + b), fitting binary log loss with a >= 0 using public SciPy L-BFGS-B and an analytic gradient. Non-convergence fails explicitly. Clipping is numerical protection for the logit only; it never changes the stored/raw probability definition. Isotonic uses increasing=True and out_of_bounds="clip". No private sklearn APIs or additional dependency is required. See [SciPy L-BFGS-B](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html) and [sklearn IsotonicRegression](https://scikit-learn.org/1.8/modules/generated/sklearn.isotonic.IsotonicRegression.html).

Choose the lowest mean Brier score; candidates within absolute 1e-12 of that minimum tie. Lowest mean log loss breaks that tie within the same tolerance, followed by identity, sigmoid, isotonic in order of simplicity. ECE is diagnostic only. Fit the selected mapping on all TRAIN OOF pairs. Freeze both models' mappings before canonical VALIDATION scoring; verify raw validation metrics against stored prior results. No validation-driven override is allowed.

ECE uses ten target quantile bins: unique internal quantile edges, duplicate boundaries collapsed, equal probabilities assigned together to the right bin, empty bins omitted. Constant predictions produce one bin; actual counts are recorded. ECE is the count-weighted absolute difference between bin mean probability and observed event rate. It depends on binning and is not a regulatory calibration standard. Sigmoid preserves ranking when its slope is positive and clipping introduces no ties; zero slope or clipping can add ties. Isotonic flat regions may change ranking metrics through ties. Calibration is not a discrimination technique.

Select a downstream model only if it has AUC/AP no lower and Brier/log loss no higher than the other, with at least one strict improvement. Otherwise retain MIXED_VALIDATION_RESULT and select no downstream threshold. Compare the frozen reported probabilities with 1,000 paired validation bootstrap replicates, seed 42, percentile 95% intervals; both models and all four metrics use the same row draws. Skip and count single-class draws.

For a resolved model, choose the highest finite TRAIN OOF threshold attaining maximum Youden J (TPR−FPR, the technical maximum KS objective) within 1e-12. ROC's +infinity sentinel is excluded. Produce a TRAIN-only 0.05–0.95 grid in 0.05 steps plus the chosen threshold. Apply only that frozen threshold and reference 0.50 to VALIDATION. These are classification diagnostics, not lending policy or risk bands.

## Actual result

Identity wins for both models, versioned as logistic-calibration-1.0.0 and xgboost-calibration-1.0.0. No fitted transformation is applied and binary path/hash fields are null. Non-identity mappings serialize under ignored artifacts/calibration with SHA-256 identities and strict round-trip checks; synthetic tests exercise both. XGBOOST_SELECTED_FOR_DOWNSTREAM is the deterministic development result. The TRAIN OOF max-KS threshold is 0.21430689096450806. This is not final untouched-test confirmation or production approval.

## Consequences and limitations

The identity result must be retained even though isotonic modestly improves selection-CV ECE: Brier is the declared primary criterion. For Logistic, the identity/isotonic Brier difference is only about 6.46e-7, larger than the fixed numerical tolerance; it is not evidence of a substantial practical difference. Candidate isotonic log loss is worse for both models. No validation result changed because identity was selected.

The OOF models overlap in their training data, and earlier XGBoost tuning already used TRAIN. The second-level CV is not fully nested end-to-end model-selection validation. Threshold diagnostics also use labels that fitted the final mapping and can be optimistic. Project VALIDATION is a reused development set; paired intervals omit retraining, model-selection and population-shift uncertainty. Optional validation calibration-intercept/slope diagnostics are omitted: required reliability, Brier, log loss and ECE suffice here and no extra validation fitting is introduced.

Reported probability estimates the dataset-defined next-month default-payment event. It is not regulatory, Basel/IFRS 9, verified 90-DPD or 12-month PD. Random splitting does not establish out-of-time validation. Future SHAP explanations of the underlying model must not automatically be claimed to sum to the calibrated/reported probability; output units and any mathematical bridge must be validated explicitly. No SHAP, score, business decisions or Phase-7 functionality is implemented. TEST SET REMAINS SEALED.
