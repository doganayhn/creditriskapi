# Architecture Decision Records

Create an ADR only for a consequential decision materially affecting future architecture, such as final dataset selection, serving architecture, calibration strategy, internal score methodology or persistence architecture. Include context, alternatives, decision, rationale, consequences and status. Use a stable sequential filename; preserve superseded decisions with explicit links.

Phase 1 made no final dataset or serving decision. Phase 2 finalized the dataset in [001-dataset-selection.md](001-dataset-selection.md). Phase 3 adopted [002-feature-policy-and-split.md](002-feature-policy-and-split.md). Phase 4 records the fixed model and evaluation boundary in [003-logistic-baseline.md](003-logistic-baseline.md). Serving decisions remain future work. Do not create fake ADR history merely to populate this directory.

Phase 5 adds [004-xgboost-challenger.md](004-xgboost-challenger.md) for fold-local search, controlled comparison, sparse-zero handling, native artifacts and provisional selection.
