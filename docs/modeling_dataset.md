# Modeling dataset contract

Phase 3 prepares data; it does not train a predictive model. The V1 target remains `default_next_month` with the dataset-defined next-month event and existing limitations.

## Consumer API

```python
from pathlib import Path
from credit_risk.config import load_config
from credit_risk.features.prepare import verify_dataset_manifest, prepare_dataset

root = Path.cwd()
config = load_config(root)
canonical, dataset_sha256 = verify_dataset_manifest(root)
prepared = prepare_dataset(canonical, config.split, config.random_seed)
train = prepared.partitions["train"]
X_train, y_train = train.X, train.y
review_train = train.review
feature_names = prepared.feature_names
```

`verify_dataset_manifest` checks the raw pin against the Phase-2 manifest, source schema and loaded dimensions. The CLI also checks the configured target. `prepare_dataset` is the in-memory lifecycle for canonical input: split first, select raw financial fields, engineer each partition, fit preprocessing once on train, and transform all three partitions. Its generic canonical-input API permits synthetic tests; callers loading official data must use the identity-verification boundary first.

## Partitions and alignment

Every eligible customer belongs to exactly one stratified random partition. Canonical rows are first sorted by unique customer_id, making assignment invariant to input ordering. Two sklearn `train_test_split` calls use the same centralized seed (42 in current config): a 30% temporary set, then half that set for test. Train/validation/test are 70/15/15. Invalid IDs or insufficient target-class representation fail explicitly. There is no out-of-time or vintage claim.

Each `PreparedSplit` contains `X` (CSR float64 matrix), `y` (a Series named only `default_next_month`), and `review` (customer_id, sex, age, education, marital_status). Matrix row order matches y/review; their Series/DataFrame indices match each other. Do not independently sort any one component. No excluded field enters X. Review fields remain available for future fairness work, without becoming primary predictors.

## Primary inputs and final columns

19 raw financial fields produce 26 stateless derived fields. The engineered input contract has 39 numeric fields and 6 categorical repayment fields, in an exact enforced order. The real train-fitted encoder produces 64 one-hot columns, yielding 103 final columns. Complete ordered names and per-column canonical/original-source lineage are in [feature_manifest.json](../data/metadata/feature_manifest.json).

| Partition | Rows | Negative | Positive | Positive rate | Matrix shape |
| --- | --- | --- | --- | --- | --- |
| Train | 21,000 | 16,355 | 4,645 | 22.119048% | 21,000 × 103 |
| Validation | 4,500 | 3,505 | 995 | 22.111111% | 4,500 × 103 |
| Test | 4,500 | 3,504 | 996 | 22.133333% | 4,500 × 103 |

All real matrices pass efficient finite checks on sparse stored values; implicit zeros are finite. All targets are complete and binary. Row coverage is complete and customer overlap is zero. These counts are integrity evidence, not model evaluation.

## Preprocessing lifecycle

The sklearn Pipeline consists of a strict schema guard followed by a ColumnTransformer. Numeric: SimpleImputer(strategy="median") then StandardScaler. Categorical: SimpleImputer(strategy="constant", fill_value="status_missing", keep_empty_features=True) then OneHotEncoder(handle_unknown="ignore", sparse_output=True). All fitting, including vocabulary discovery, uses only train. The schema guard rejects target/ID/demographics, extra or misordered features, nonnumeric values, infinity and entirely missing training numeric columns. Pipeline fitting with y is rejected.

Stateless feature engineering accepts only the 19-field financial allowlist. It is deliberately separate from the fitted preprocessor, which expects 45 engineered fields. Future inference must use the same engineering version and input order. Unknown valid repayment codes are preserved as tokens and safely ignored by the encoder if absent during training. Missing categories use a distinct token; if that token was absent during training, its one-hot block is also zero. No test-dependent vocabulary expansion is allowed.

The public `fit_preprocessor(train_features)` helper requires a training-only input by contract. The orchestration enforces its use on the training branch, and tests verify this. An arbitrary DataFrame cannot prove its provenance by itself; future callers must preserve the documented split discipline.

## Serialization and local outputs

The CLI serializes the fitted preprocessor under the configured ignored artifact directory's `preprocessing/` subdirectory, using a SHA-256 filename. It reloads that trusted local object and checks training transforms for equality. The aggregate preprocessing manifest records its relative path/hash, versions, input names, shapes and generation time. Joblib uses pickle-compatible loading: only load artifacts created by this project in a trusted environment. A matching hash does not make an untrusted pickle safe.

Matrices, customer-level assignments and review frames are returned in memory and are not exported or tracked. Recreate them from source/config/code. Any future local exports belong only under ignored processed/artifact paths.

## Reproducibility and sealed test set

Run `python -m credit_risk.features.prepare` from the root, or supply `--project-root PATH`. Preparation is local-only and refuses changed raw/manifest identity. The three aggregate manifests record dataset SHA-256, split algorithm/seed/fractions, feature/preprocessing versions, ordered feature lineage and runtime versions. The preprocessing manifest includes hashes of feature implementation files. Unchanged metadata retains its generation timestamp and is not rewritten.

The test set is reserved for later final evaluation. Phase 3 transforms it with train-fitted state and checks only shape, finite values, labels, class counts and partition integrity. No feature comparison, target-association analysis or performance metric is computed. Future cross-validation must refit preprocessing inside each training fold rather than reusing globally fitted training statistics across fold boundaries.
