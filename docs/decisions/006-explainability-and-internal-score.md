# ADR 006 — Explainability and internal risk score

## Status

Implemented in Phase 7; subject to project-owner technical review before commit. Model/calibration choices from Phase 6 remain unchanged.

## Context

The selected frozen binary logistic XGBoost model uses identity calibration. Explanations must distinguish raw margin, probability, score and business policy, preserve the 103-column Phase-3 lineage and avoid exporting real customer rows. Exact TRAIN OOF probabilities were not retained, and retraining is forbidden.

## Decision

Use SHAP 0.51.0 public TreeExplainer, explicitly raw output and tree_path_dependent perturbation with the model's training path counts. Verify native margin/probability consistency and independent SHAP additivity on all VALIDATION rows. Materialize the canonical numeric matrix densely for trained zero semantics. No explainer binary is necessary.

Aggregate signed local columns to Phase-3 source inputs before global magnitude; aggregate sources to seven documented families the same way. Rank source-level local drivers by signed magnitude with lexical ties. They are model diagnostics, not causal or regulatory adverse-action explanations.

Version the internal score separately: base 600, good:bad odds 50, PDO 20, factor=20/ln(2), offset=600-factor*ln(50). Canonical score uses reported probability and remains continuous; epsilon=1e-12 is solely numerical protection. No cosmetic bounds, FICO equivalence, business cutoff or risk bands exist.

Allow exact score-point attribution only when binary logistic raw-margin SHAP, identity calibration, V1 log-odds mapping and no numerical clipping make it valid. Use score_base=offset-factor*base_margin and points=-factor*SHAP. Disable unsupported additive output explicitly when assumptions change.

Keep TRAIN OOF score statistics unavailable under the owner's explicit clarification. Do not regenerate OOF models or substitute in-sample training scores. Preserve historical metadata and Phase-1–6 reports. Persist only five aggregate Phase-7 artifacts.

## Alternatives considered

Probability-space SHAP would change the requested interpretation and dependency/background semantics. Native gain alone does not supply additive local explanations. Summing child absolute importances fails signed local cancellation. Cosmetic score ranges distort the requested mapping. Recreating discarded OOF predictions violates the no-retraining instruction.

SHAP 0.50.0 failed a dry-run dependency resolution on Python 3.14 because of unavailable pinned llvmlite; the dry run did not modify the environment. SHAP 0.52.0 would raise the project minimum to Python 3.12. Version 0.51.0 preserves Python 3.11 and passed actual XGBoost 3.2.0 integration on Python 3.14.6. See [release metadata](https://pypi.org/project/shap/0.51.0/) and [public TreeExplainer API](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html).

## Rationale

Raw log-odds provide an independently verifiable additive model space and, in the current identity case, an affine mapping to score points. Local-first aggregation preserves totals and captures cancellation. Explicit versions keep model, calibration, explainability and internal score independently auditable without inventing business semantics.

## Consequences

Attribution remains noncausal and sensitive to correlations/path-dependent semantics. Native floating-point residuals require explicit measured tolerances. TRAIN OOF score distribution is unavailable. Frozen artifact/runtime requirements remain strict. Future non-identity consumers need reviewed integration; they cannot reuse exact score attribution silently. TEST, serving, persistence, policy, Docker and operations remain outside this phase.
