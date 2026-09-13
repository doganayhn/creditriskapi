"""Bounded TRAIN-only randomized search with a fresh preprocessor in every CV fit."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted
from xgboost import XGBClassifier

from credit_risk.config import _read, _check_keys
from credit_risk.features.preprocessing import build_preprocessor, transform_split
from credit_risk.modeling.metrics import binary_target


def load_settings(root: Path) -> dict:
    settings = _read(root / "configs/xgboost.yaml", {"search", "fixed", "space"})
    search = _check_keys(settings["search"], {"n_iter", "cv_folds"}, "xgboost.search")
    if (type(search["n_iter"]) is not int or not 1 <= search["n_iter"] <= 24 or
            type(search["cv_folds"]) is not int or not 2 <= search["cv_folds"] <= 4):
        raise ValueError("Search cost guard requires 1..24 candidates and 2..4 folds")
    fixed = settings["fixed"]
    if fixed != {"objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist",
                 "device": "cpu", "scale_pos_weight": 1.0, "n_jobs": 1}:
        raise ValueError("XGBoost fixed parameters violate canonical CPU/unweighted contract")
    keys = {"n_estimators", "max_depth", "learning_rate", "min_child_weight", "subsample",
            "colsample_bytree", "reg_lambda", "reg_alpha", "gamma"}
    space = _check_keys(settings["space"], keys, "xgboost.space")
    for name, values in space.items():
        if not isinstance(values, list) or not values or len(set(values)) != len(values):
            raise ValueError(f"Search values must be nonempty unique lists: {name}")
        for value in values:
            if type(value) not in (int, float) or not np.isfinite(value) or value < 0:
                raise ValueError(f"Invalid search value for {name}")
            if name in ("max_depth", "n_estimators") and (type(value) is not int or not 1 <= value <= (5 if name == "max_depth" else 700)):
                raise ValueError(f"Search complexity limit exceeded: {name}")
            if name in ("learning_rate", "subsample", "colsample_bytree") and not 0 < value <= 1:
                raise ValueError(f"Invalid fraction for {name}")
    if np.prod([len(v) for v in space.values()]) < search["n_iter"]:
        raise ValueError("Search candidate count exceeds unique combinations")
    return settings


class FoldPreprocessor(TransformerMixin, BaseEstimator):
    """Discard y at the unsupervised boundary; preserve Phase-3's no-target guard."""

    def fit(self, X, y=None):
        self.preprocessor_ = build_preprocessor().fit(X)
        return self

    def transform(self, X):
        check_is_fitted(self, "preprocessor_")
        # XGBoost trees treat absent CSR entries as missing. Densify without changing
        # values so true numeric/one-hot zeros retain the baseline's semantics.
        return transform_split(self.preprocessor_, X).toarray()

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "preprocessor_")
        return self.preprocessor_.get_feature_names_out()


def select_candidate(results: dict) -> int:
    """AUC, then AP within machine epsilon; then depth, trees, stronger regularization."""
    auc = np.asarray(results["mean_test_roc_auc"], dtype=float)
    ap = np.asarray(results["mean_test_average_precision"], dtype=float)
    if not np.isfinite(auc).all() or not np.isfinite(ap).all():
        raise ValueError("Non-finite CV scores cannot select a candidate")
    epsilon = np.finfo(float).eps
    candidates = np.flatnonzero(np.abs(auc - auc.max()) <= epsilon)
    candidates = [int(i) for i in candidates if abs(ap[i] - ap[candidates].max()) <= epsilon]
    def simplicity(i):
        p = results["params"][i]
        return (p["model__max_depth"], p["model__n_estimators"], -p["model__reg_lambda"],
                -p["model__reg_alpha"], -p["model__gamma"], i)
    return min(candidates, key=simplicity)


def build_search(settings: dict, seed: int) -> RandomizedSearchCV:
    pipeline = Pipeline([("preprocessing", FoldPreprocessor()),
                         ("model", XGBClassifier(**settings["fixed"], random_state=seed))])
    return RandomizedSearchCV(
        pipeline, {f"model__{k}": v for k, v in settings["space"].items()},
        n_iter=settings["search"]["n_iter"],
        cv=StratifiedKFold(n_splits=settings["search"]["cv_folds"], shuffle=True, random_state=seed),
        scoring={"roc_auc": "roc_auc", "average_precision": "average_precision"},
        refit=select_candidate, random_state=seed, n_jobs=1, return_train_score=False,
        error_score="raise", verbose=1,
    )


def run_search(X_train_engineered: pd.DataFrame, y_train, settings: dict, seed: int):
    target = binary_target(y_train, len(X_train_engineered))
    search = build_search(settings, seed)
    search.fit(X_train_engineered, target)
    return search


def search_table(search) -> pd.DataFrame:
    results = search.cv_results_
    rows = []
    for i, parameters in enumerate(results["params"]):
        rows.append({"candidate_index": i, "candidate_rank": int(results["rank_test_roc_auc"][i]),
                     "selected": i == search.best_index_, "test_set_evaluated": False,
                     **{key.removeprefix("model__"): value for key, value in parameters.items()},
                     **{key: float(results[key][i]) for key in (
                         "mean_test_roc_auc", "std_test_roc_auc", "mean_test_average_precision",
                         "std_test_average_precision", "mean_fit_time", "mean_score_time")}})
    return pd.DataFrame(rows).sort_values(["candidate_rank", "candidate_index"], kind="stable").reset_index(drop=True)
