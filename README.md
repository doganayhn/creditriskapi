# Credit Risk Scoring & Explainability System

A portfolio fintech project intended to estimate borrower default risk from information available at scoring time, explain model outputs and eventually expose auditable predictions through a versioned API.

## Current status
Phases 1–2 are COMPLETED. Implemented scope includes configuration, official UCI 350 acquisition, strict loading/canonicalization and descriptive quality profiling. No model has been trained. Phases 3–10 remain NOT_STARTED. See the [Phase 2 completion report](docs/phase_reports/phase_02_completion_report.md); the [Phase 1 completion report](docs/phase_reports/phase_01_completion_report.md) remains historical evidence.

## Intended architecture
Public dataset → validation → leakage-safe preprocessing/features → baseline/challenger → calibration when justified → PD → explainability/internal score → versioned policy → API → persistence/audit. Dataset acquisition and validation are implemented; preprocessing, modeling and subsequent components remain planned for Phases 3–10.

## Development
Python 3.11 or newer is required. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
```

On POSIX use `.venv/bin/python` for the last two commands. Runtime dependencies: PyYAML, pandas and xlrd (original XLS reader); HTTP uses the standard library. Development dependency: pytest. Configuration is explicit YAML, not environment-driven; `.env.example` documents this. Configuration loading creates no directories and changes no random generators.

```python
from pathlib import Path
from credit_risk.config import load_config

config = load_config(Path.cwd())  # Explicit repository root
print(config.random_seed, config.paths.raw, config.target_column)
```

`configs/base.yaml` owns the seed and relative data/artifact/metadata paths. `configs/experiment.yaml` owns the experiment name and target, now `default_next_month`. Both files are mandatory; unknown/missing keys and invalid values fail explicitly. Paths resolve from the supplied root, independent of the working directory. Configurations remain external to the package; wheel users must supply the configuration directory in their project root.

## Acquire and profile the official dataset

```powershell
.venv\Scripts\python.exe -m credit_risk.data.download
.venv\Scripts\python.exe -m credit_risk.data.quality
```

Both commands accept `--project-root PATH`; by default the CLI uses the current directory as the root. Download requires HTTPS access to UCI and a filesystem supporting hard links for atomic no-overwrite publication. It reuses a matching file offline and fails on a changed checksum, unexpected workbook schema or invalid target. Do not manually edit the raw XLS. The checksum pins the bytes verified from UCI, not a publisher-signed version. A different official version requires investigation and an explicit update.

The original workbook stays ignored under `data/raw/`. The manifest and quality summary under `data/metadata/` contain only aggregate/schema information and are intended for Git. Profiling does not download anything, change raw values, fit preprocessing or produce a modeled dataset. The automated suite uses mocks and a four-row synthetic XLS fixture, with no live network or real-data dependency.

See the [dataset card](docs/dataset_card.md), [quality report](docs/data_quality_report.md), [physical contract](docs/data_contract.md) and [selection ADR](docs/decisions/001-dataset-selection.md) for attribution, target meaning, observed issues and traceability.

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
`src/credit_risk/config.py` handles configuration; `src/credit_risk/data/` contains acquisition, loading, schema and quality code. `tests/` covers foundation/data behavior. `data/raw/` holds the ignored original XLS; `data/metadata/` holds aggregate provenance and profiling JSON. Interim/processed data, artifacts, notebooks and feature/model/explanation components remain reserved for later work. Customer records, generated artifacts, secrets and environments are ignored by Git.

## Limitations
The selected historical Taiwan credit-card dataset contains 30,000 rows, 25 columns and 6,636 positive next-month labels (22.12%). True nulls and ID/exact-row duplicates are absent, but undocumented category codes and negative bill values remain. The source does not specify a regulatory default threshold or event-level scoring dates. Within-row monthly history does not support true out-of-time validation. Feature eligibility, including demographic use and code treatment, remains a Phase-3 decision. Raw model probabilities must not be called calibrated PD, and underlying-model SHAP must not be described as additive calibrated-PD explanations. XGBoost, SHAP, API, PostgreSQL, Docker and model operations are not implemented.

This repository is educational / portfolio work, not a regulatory or production lending authority. Outputs are not real lending decisions; no real lending decision should rely on this project.
