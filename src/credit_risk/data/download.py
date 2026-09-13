"""Acquire the pinned official XLS and generate its aggregate provenance manifest."""

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import io
import json
import os
from pathlib import Path
import tempfile
from urllib.error import URLError
from urllib.request import urlopen
import zipfile

from credit_risk.config import load_config
from credit_risk.data import source
from credit_risk.data.load import load_source
from credit_risk.data.schema import DataSchemaError, column_mapping


class AcquisitionError(RuntimeError):
    """Acquisition or provenance verification failed; existing raw bytes are retained."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_raw(path: Path) -> str:
    digest = sha256_file(path)
    if digest != source.EXPECTED_SHA256:
        raise AcquisitionError(f"SHA-256 mismatch for {path}; expected {source.EXPECTED_SHA256}, got {digest}. Existing file will not be overwritten; investigate source/version or local corruption.")
    return digest


def write_json(path: Path, value: dict) -> None:
    """Atomically write aggregate metadata; unchanged content retains its timestamp."""
    content = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=".tmp", mode="w", encoding="utf-8", newline="\n") as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _fetch() -> bytes:
    try:
        with urlopen(source.DOWNLOAD_URL, timeout=30) as response:
            if response.status != 200:
                raise AcquisitionError(f"Official source returned HTTP {response.status}")
            if not response.geturl().startswith("https://archive.ics.uci.edu/"):
                raise AcquisitionError("Official source redirected outside the allowed UCI host")
            blob = response.read(20_000_001)
        if len(blob) > 20_000_000:
            raise AcquisitionError("Official archive exceeds the 20 MB safety limit")
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            if archive.namelist() != [source.RAW_FILENAME]:
                raise AcquisitionError("Unexpected official archive members")
            if archive.getinfo(source.RAW_FILENAME).file_size > 20_000_000:
                raise AcquisitionError("Uncompressed source exceeds the 20 MB safety limit")
            raw = archive.read(source.RAW_FILENAME)
    except (URLError, OSError, HTTPException, zipfile.BadZipFile, EOFError) as exc:
        raise AcquisitionError(f"Official download failed (30-second socket timeout): {exc}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != source.EXPECTED_SHA256:
        raise AcquisitionError(f"Downloaded XLS checksum mismatch: {digest}; source update requires explicit investigation")
    return raw


def acquire(project_root: str | Path) -> dict:
    """Reuse matching raw bytes offline; never replace a mismatching existing XLS."""
    config = load_config(project_root)
    if config.target_column != source.TARGET:
        raise DataSchemaError(f"This dataset requires configured target {source.TARGET}")
    raw_path = config.paths.raw / source.RAW_FILENAME
    manifest_path = config.paths.metadata / "dataset_manifest.json"
    retrieved_at = None
    if raw_path.exists():
        verify_raw(raw_path)
    else:
        raw = _fetch()
        config.paths.raw.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=config.paths.raw, delete=False, suffix=".tmp") as stream:
            temporary = Path(stream.name)
            stream.write(raw)
        try:
            # A hard link publishes complete bytes atomically and refuses to overwrite.
            try:
                os.link(temporary, raw_path)
                retrieved_at = datetime.now(timezone.utc).isoformat()
            except FileExistsError:
                verify_raw(raw_path)
        finally:
            temporary.unlink(missing_ok=True)
    digest = verify_raw(raw_path)
    if manifest_path.exists():
        try:
            old = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise AcquisitionError("Existing manifest is unreadable; investigate before regeneration") from exc
        if not isinstance(old, dict) or old.get("sha256") != digest:
            raise AcquisitionError("Existing manifest checksum does not match the pinned raw source")
        # Preserve original acquisition time on idempotent reruns, not file mtime.
        retrieved_at = old.get("retrieved_at")
    frame = load_source(raw_path)
    manifest = {
        "dataset_name": source.DATASET_NAME,
        "source": "UCI Machine Learning Repository",
        "source_url": source.SOURCE_PAGE,
        "download_url": source.DOWNLOAD_URL,
        "uci_dataset_id": 350,
        "doi": source.DOI,
        "license": source.LICENSE,
        "attribution": source.ATTRIBUTION,
        "retrieved_at": retrieved_at,
        "retrieved_at_note": "UTC acquisition time; null if matching bytes pre-existed without a recorded retrieval time",
        "raw_filename": source.RAW_FILENAME,
        "file_size_bytes": raw_path.stat().st_size,
        "sha256": digest,
        "checksum_origin": "Measured from official UCI XLS on 2026-09-13; pinned locally, not published by UCI",
        "row_count": len(frame),
        "column_count_raw": len(column_mapping()),
        "column_count_canonical": len(frame.columns),
        "header_rows_excluded": 2,
        "original_target_column": source.ORIGINAL_TARGET,
        "canonical_target_column": source.TARGET,
        "target_positive_value": 1,
        "target_negative_value": 0,
        "source_to_canonical": column_mapping(),
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        manifest = acquire(args.project_root)
    except (AcquisitionError, DataSchemaError, OSError, ValueError) as exc:
        parser.exit(1, f"Acquisition failed: {exc}\n")
    print(f"Verified {manifest['raw_filename']}: {manifest['row_count']} rows, SHA-256 {manifest['sha256']}; manifest written/unchanged.")


if __name__ == "__main__":
    main()
