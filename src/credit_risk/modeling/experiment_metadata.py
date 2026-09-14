"""Preserve the original record when a historical experiment is reproduced."""

from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path

import pandas as pd

from credit_risk.data.download import sha256_file, write_json

# Explicit modeling dependency closures. Data/features/configuration identities are
# recorded separately by the existing experiment contracts, not by a directory scan.
BASELINE_MODULES = ("__init__.py", "artifacts.py", "baseline.py", "contract.py",
                    "metrics.py", "experiment_metadata.py")
XGBOOST_MODULES = (*BASELINE_MODULES, "comparison.py", "search.py", "xgboost_challenger.py")
TIMING_COLUMNS = ("mean_fit_time", "mean_score_time")


def implementation_hashes(modules: tuple[str, ...], directory: Path | None = None) -> dict:
    directory = directory or Path(__file__).parent
    return {name: sha256_file(directory / name) for name in sorted(modules)}


def publish_experiment(manifest_path: Path, manifest: dict, outputs: dict[str, dict],
                       search_table: pd.DataFrame | None = None) -> dict:
    """Publish once; unchanged reproduction keeps original bytes/provenance/timings.

    Check all scientific identity/result fields before writing any tracked output.
    Historical source hashes describe the original run, not the reproducing code.
    A changed experiment requires an explicit new record, never silent replacement.
    """
    directory = manifest_path.parent
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity = lambda value: {k: v for k, v in value.items()
                                  if k not in {"generated_at", "implementation_sha256"}}
        if identity(previous) != identity(manifest):
            raise ValueError("Historical experiment identity/result changed; metadata was not overwritten")
        for name, result in outputs.items():
            path = directory / name
            if not path.exists() or json.loads(path.read_text(encoding="utf-8")) != result:
                raise ValueError(f"Historical experiment output changed or missing: {name}; metadata was not overwritten")
        if search_table is not None:
            path = directory / "xgboost_search_results.csv"
            if not path.exists():
                raise ValueError("Historical search results missing; metadata was not overwritten")
            # Round-trip parsing avoids introducing float-parser rounding differences.
            old = pd.read_csv(path, float_precision="round_trip")
            new = pd.read_csv(StringIO(search_table.to_csv(index=False)), float_precision="round_trip")
            try:
                pd.testing.assert_frame_equal(old.drop(columns=list(TIMING_COLUMNS)),
                                              new.drop(columns=list(TIMING_COLUMNS)),
                                              check_exact=True, check_dtype=False)
            except (AssertionError, KeyError) as exc:
                raise ValueError("Historical search results changed; metadata was not overwritten") from exc
        return previous  # No writes, including timestamp, provenance or CSV timings.

    record = {**manifest, "generated_at": datetime.now(timezone.utc).isoformat()}
    for name, result in outputs.items():
        write_json(directory / name, result)
    if search_table is not None:
        search_table.to_csv(directory / "xgboost_search_results.csv", index=False, lineterminator="\n")
    write_json(manifest_path, record)
    return record
