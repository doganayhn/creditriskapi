# Ten-phase roadmap

Only an explicitly requested phase may be implemented. Each phase ends with tests and a completion report, followed by technical review by the project owner and any necessary fixes before the owner creates the Git commit. Codex must not automatically commit or start the next phase. Valid phase states are NOT_STARTED, IN_PROGRESS and COMPLETED.

| Phase | Name | Scope | Status |
| --- | --- | --- | --- |
| 1 | Project Foundation & Data Contract | Repository foundation, documentation, configuration, financial definitions, dataset decision framework and leakage policy | COMPLETED |
| 2 | Data Ingestion & Data Quality | Acquisition/ingestion, schema verification, quality checks, EDA and dataset-specific limitations | COMPLETED |
| 3 | Credit Risk Feature Engineering | Feature definitions, preprocessing, transformations, leakage-safe engineering and train/validation/test preparation | COMPLETED |
| 4 | Baseline Risk Model | Fixed Logistic Regression, raw TRAIN/VALIDATION evaluation, coefficients and versioned local artifact; TEST sealed | COMPLETED |
| 5 | XGBoost Risk Model | TRAIN-only fold-local CV, unweighted challenger, separate weighting sensitivity and provisional validation comparison; TEST sealed | COMPLETED |
| 6 | Probability Calibration & Decision Thresholds | Calibration analysis, probability quality, threshold methodology and risk-band strategy | NOT_STARTED |
| 7 | Explainability & Internal Risk Score | Global/local SHAP, semantics, internal score mapping and explanation validation | NOT_STARTED |
| 8 | Production API & Persistence | Versioned FastAPI, PostgreSQL, prediction audit and versioned business rules | NOT_STARTED |
| 9 | Testing, Docker & Model Operations | Integration tests, Dockerization, startup loading, concurrency, security and monitoring foundations | NOT_STARTED |
| 10 | Final Validation & Portfolio Release | End-to-end validation, model card, final README, architecture review, limitations, demo and release preparation | NOT_STARTED |
