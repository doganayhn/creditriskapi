# Decision

Phase 4 implements one fixed `logistic-baseline-1.0.0` LogisticRegression model. Status: implemented in Phase 4, pending the project owner's technical review and commit. Fit TRAIN only, evaluate TRAIN and VALIDATION only, and keep TEST sealed.

# Context

Phase 3 established a shared 103-column financial feature contract, train-fitted preprocessing and a stratified random 70/15/15 split. A transparent linear log-odds baseline provides a comparison anchor for the future nonlinear challenger. This does not imply every bank uses this implementation.

# Model Specification and Rationale

Use L2 regularization, fixed C=1.0, intercept=True, class_weight=None, solver=lbfgs, max_iter=5000 and tol=1e-8. LBFGS supports the binary CSR design and uses no random sampling; random_state remains None. Limit numerical-library threads to one during fitting. The iteration budget and tight tolerance were fixed for numerical convergence, without a parameter or solver search. Any ConvergenceWarning or iteration-limit exhaustion fails the experiment.

The pinned sklearn 1.8 API expresses L2 with `l1_ratio=0.0`; `penalty` stays at its deprecated sentinel. This is equivalent to the requested `penalty="l2"`, without triggering an avoidable deprecation warning. See the [official 1.8 release notes](https://scikit-learn.org/1.8/whats_new/v1.8.html).

The approximately 22% positive prevalence is not an extreme rare-event setting. An unweighted fit preserves the empirical class prior in the objective and avoids class-weight-induced probability-scale changes before calibration analysis. No resampling, balanced sensitivity model or hyperparameter search is used.

# Alternatives Considered

- Class weighting or resampling: changes the primary fitting objective/prior; unnecessary for this fixed baseline.
- Unregularized Logistic Regression: leaves the related financial feature families without coefficient shrinkage; fixed L2 provides a more stable baseline.
- Solver/C/penalty search: outside the fixed-baseline scope.
- XGBoost: deferred to Phase 5; no challenger is implemented here.
- Calibration: deferred to Phase 6; probability diagnostics alone do not establish calibration.

# Consequences

The baseline is reproducible and exposes coefficients, but its log-odds are linear in transformed inputs. Related raw billing/payment histories, aggregates and ratios share signal; L2 shrinks estimates without resolving identification or causal interpretation. No features were removed. Full one-hot encoding has no omitted reference, so categorical exponentiated coefficients are not conventional odds ratios versus a reference group. Standardized numeric coefficients describe a one-training-standard-deviation change conditional on other inputs; structural dependencies can make that isolated change unrealistic.

Only raw, uncalibrated next-month default-payment probabilities exist. The fixed 0.50 reference threshold is descriptive, never a business cut-off. Bootstrap intervals condition on this fitted model and this validation sample; they omit training/model-selection and population-shift uncertainty. Future XGBoost may represent nonlinearities/interactions differently but must be compared on the same validation population. TEST remains reserved for final evaluation.

Model artifacts use explicit version plus content digest under ignored `artifacts/models/`, as authorized by Phase 4; this refines the earlier generic experiment-directory example. Aggregate manifests identify configuration, code, source, preprocessing, runtime, coefficients and metrics. Existing Phase-3 semantic manifests are pinned to commit 819e449; disagreement requires investigation, never automatic repair. Trusted local joblib loading is required; a checksum does not make arbitrary pickle safe.
