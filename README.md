# Credit Risk Scoring & Explainability System

A portfolio fintech project intended to estimate borrower default risk from information available at scoring time, explain model outputs and eventually expose auditable predictions through a versioned API.

## Current status
Phase 1 is COMPLETED. Implemented scope is project governance, financial/data documentation and a minimal tested configuration package. No dataset has been ingested and no model has been trained. Phases 2–10 remain NOT_STARTED. See the [Phase 1 completion report](docs/phase_reports/phase_01_completion_report.md).

## Intended architecture
Public dataset → validation → leakage-safe preprocessing/features → baseline/challenger → calibration when justified → PD → explainability/internal score → versioned policy → API → persistence/audit. All components in this flow are planned for Phases 2–10; only the foundation exists now.

## Development
Python 3.11 or newer is required. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
```

On POSIX use `.venv/bin/python` for the last two commands. Runtime dependency: PyYAML; development dependency: pytest. Configuration is explicit YAML, not environment-driven; `.env.example` documents this. Loading creates no directories and changes no random generators.

```python
from pathlib import Path
from credit_risk.config import load_config

config = load_config(Path.cwd())  # Explicit repository root
print(config.random_seed, config.paths.raw, config.target_column)
```

`configs/base.yaml` owns the seed and relative paths. `configs/experiment.yaml` owns the experiment name and nullable target. Both are mandatory; unknown/missing keys and invalid values fail explicitly. Paths resolve from the supplied root, independent of the working directory. The target remains `null` until Phase 2 verifies its meaning and schema. Configurations remain external to the package; wheel users must supply the configuration directory in their project root.

## Ten-phase plan
1. Foundation and data contract
2. Ingestion and data quality
3. Feature engineering
4. Baseline risk model
5. XGBoost challenger
6. Calibration and thresholds
7. Explainability and internal risk score
8. API and persistence
9. Testing, Docker and operations
10. Final validation and portfolio release

See [ROADMAP.md](ROADMAP.md) for scope/status and [AGENTS.md](AGENTS.md) for instruction precedence. Each phase follows phase prompt → Codex implementation → tests → phase completion report → technical review by the project owner. If issues exist, apply fixes and verify them; if no issues remain, the project owner creates the Git commit. The next phase starts only when explicitly requested. Codex must not automatically commit or start the next phase.

## Repository layout
`src/credit_risk/config.py` contains the sole functional foundation component. `configs/` holds configuration; `tests/` covers foundation behavior. `data/{raw,interim,processed}`, `artifacts/`, `notebooks/` and feature/model/explanation package directories reserve future work. Generated data/artifacts, secrets and environments are ignored by Git.

## Limitations
Dataset selection is provisional. Target horizon, empirical quality, prevalence and eligible predictors await Phase 2. Static public datasets may not support true temporal validation. Raw model probabilities must not be called calibrated PD, and underlying-model SHAP must not be described as additive calibrated-PD explanations. XGBoost, SHAP, API, PostgreSQL, Docker and model operations are not implemented.

This repository is educational / portfolio work, not a regulatory or production lending authority. Outputs are not real lending decisions; no real lending decision should rely on this project.
