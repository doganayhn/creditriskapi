"""Deterministic aggregate final evaluation report, never customer records."""


def table(rows):
    keys = list(rows[0])
    def cell(value):
        return "unavailable" if value is None else f"{value:.8g}" if isinstance(value, float) else str(value)
    return "\n".join(["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"] +
                     ["| " + " | ".join(cell(row[k]) for k in keys) + " |" for row in rows])


def report(result, tables, validation):
    r, identity = result, result["frozen_contract"]
    sections = []
    def section(title, text):
        sections.append(f"## {title}\n\n{text}")
    def metrics(name):
        return table([{"metric": k, "TEST": v} for k, v in r["models"][name].items()])
    section("Evaluation Policy", "TEST remained predictively sealed through Phases 1–9. Phase 10 evaluates the frozen system. "
            "XGBoost was selected on development VALIDATION before this evaluation; TEST never selects or tunes anything. "
            "Reproduction checks identical aggregate bytes and retains the original publication timestamp.")
    section("Frozen Pre-Test Contract", f"Pre-unseal Git HEAD: `{r['pre_unseal_git_head']}`. "
            "The complete component/source/config/metadata hashes and predeclared diagnostic policy are in "
            "[the pre-unseal snapshot](../data/metadata/final_pre_unseal_snapshot.json).\n\n" +
            table([{"component": name, "identity": value} for name, value in {
                "dataset SHA-256": identity["dataset_sha256"], "split": identity["split_version"],
                "seed": identity["split_seed"], "preprocessing": identity["preprocessing_version"],
                "preprocessor SHA-256": identity["preprocessor_sha256"],
                "Logistic SHA-256": identity["models"]["logistic"]["sha256"],
                "XGBoost SHA-256": identity["models"]["xgboost"]["sha256"],
                "calibration": "identity for both models", "score": identity["score_version"],
                "explainability": identity["explainability_version"]}.items()]))
    section("TEST Population", f"Existing stratified random TEST: {r['test_count']:,} rows; {r['negative_count']:,} negatives; "
            f"{r['positive_count']:,} positives; observed default rate {r['observed_default_rate']:.8%}. "
            "TRAIN 21,000 and VALIDATION 4,500 remain separate. This is not temporal or out-of-time validation.")
    section("Target Definition", "`default_next_month` means the workbook's default payment next month. It does not establish "
            "90+ DPD, a 12-month Basel PD, or IFRS 9 lifetime default. The public static dataset describes Taiwan credit-card clients in 2005.")
    section("Final XGBoost Results", metrics("xgboost"))
    section("Final Logistic Baseline Results", metrics("logistic"))
    section("Paired Model Comparison", "XGBoost minus Logistic; lower Brier/log loss is better. Same resampled customers for both models. "
            "Descriptive comparison only; XGBoost remains selected.\n\n" + table([
                {"metric": k, "delta": v, "95% CI": r["bootstrap"]["delta_xgboost_minus_logistic_95_ci"].get(k, "not requested")}
                for k, v in r["paired_deltas_xgboost_minus_logistic"].items()]))
    section("Discrimination", "ROC AUC, AP, KS=max(TPR−FPR), and Gini=2×AUC−1 reuse the development definitions. "
            "Validation-to-TEST differences below are sampling diagnostics, not evidence of no overfitting.\n\n" + table([
                {"model": name, "metric": key, "VALIDATION": validation[name][key], "TEST": r["models"][name][key],
                 "TEST minus VALIDATION": r["models"][name][key] - validation[name][key]}
                for name in ("logistic", "xgboost") for key in ("roc_auc", "average_precision", "ks", "brier_score", "log_loss", "ece")]))
    section("Probability Quality", "Brier and log loss measure the frozen reported probabilities. Identity is a development decision, "
            "not a claim of perfect calibration. Observed rates and predicted means are reported above.")
    section("Calibration", "Raw and reported probabilities match exactly for both models (maximum absolute difference 0). "
            "ECE uses the existing Phase-6 ten quantile bins: duplicate boundaries collapse, ties remain together and empty bins are omitted. "
            "No calibrator was fitted on TEST.\n\n" + table(tables["final_test_reliability.csv"]))
    section("Frozen Technical Threshold", "**TECHNICAL REFERENCE ONLY.** The unchanged TRAIN OOF max-KS threshold is "
            f"{identity['technical_threshold']['value']}. It is not a lending cutoff, recommended threshold or business policy. "
            "Phase 6 has no independent threshold version; its selection-manifest checksum identifies this reference.\n\n" +
            table([{"metric": k, "value": v} for k, v in r["technical_threshold"].items()]))
    section("Internal Score", "Frozen base score 600, good:bad odds 50:1, PDO 20, epsilon 1e-12. Higher probability means lower score. "
            "This internal transformation is not FICO or a lending policy. Standard deviation uses population ddof=0; quantiles use linear interpolation.\n\n" +
            table([{"diagnostic": k, "value": v} for k, v in r["score_validation"].items()]) + "\n\n" +
            table([{"statistic": k, "value": v} for k, v in r["score_summary"].items()]))
    section("Score Deciles", "Decile 1 = lowest score/highest modeled risk; decile 10 = highest score/lowest risk. "
            "Stable existing split position breaks ties. These equal-count evaluation groups are not business risk bands.\n\n" +
            table(tables["final_test_score_deciles.csv"]))
    section("Lift / Gains", "Same risk-descending order as the deciles. Cumulative lift = cumulative observed rate / overall observed rate.\n\n" +
            table(tables["final_test_lift.csv"]))
    section("SHAP Technical Validation", "First 32 rows in the existing TEST order, predeclared before unsealing. "
            "Tree SHAP remains path-dependent raw-margin attribution. Only aggregate residuals are published; global interpretation remains "
            "Phase-7 VALIDATION-based. SHAP is noncausal and does not add directly to probability.\n\n" +
            table([{"check": k, "aggregate": v} for k, v in r["shap_technical_validation"].items()]))
    section("Subgroup Diagnostics", "Sex, age, education and marital-status values come from the aligned, separate review frame. "
            "Literal raw categories and individual ages are preserved. Minimum n=100; smaller groups have unavailable metrics, "
            "and single-class groups have undefined AUC. Demographics never enter inference. See "
            "[subgroup diagnostics](subgroup_diagnostics.md) and the aggregate CSV. These results do not certify fairness or establish causality.")
    b = r["bootstrap"]
    section("Statistical Uncertainty", f"{b['requested_replicates']} requested / {b['successful_replicates']} valid / "
            f"{b['skipped_single_class']} skipped single-class replicates; seed {b['seed']}. {b['method']}. "
            "Intervals condition on this frozen model and historical sample; they exclude training, temporal and deployment uncertainty.\n\n" +
            table([{"XGBoost metric": k, "95% CI": v} for k, v in b["xgboost_95_ci"].items()]))
    section("Limitations", "Historical static Taiwan 2005 data, selection of existing credit-card clients, unresolved category semantics, "
            "no modern OOT validation and no production/regulatory certification. Subgroup uncertainty and proxies remain. "
            "See [limitations](limitations.md) and [model card](model_card.md). Row-level TEST arrays remain in memory only.")
    section("What Was NOT Done", "No retraining, preprocessing refit, calibration fit, TEST tuning, model reselection, new threshold, "
            "new score parameters, lending decision, credit-limit recommendation, risk bands, regulatory validation, cloud deployment or frontend.")
    return ("# Final Evaluation\n\n" + "\n\n".join(sections) + "\n").encode()
