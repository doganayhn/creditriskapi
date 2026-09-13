import hashlib
from http.client import IncompleteRead
import io
import json
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
import zipfile

import pytest

from credit_risk.data import download, source
from credit_risk.data.quality import run_quality


@pytest.fixture
def mocked_source(monkeypatch):
    raw = (Path(__file__).parent / "fixtures/synthetic_credit.xls").read_bytes()
    monkeypatch.setattr(source, "EXPECTED_SHA256", hashlib.sha256(raw).hexdigest())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(source.RAW_FILENAME, raw)
    class Response(io.BytesIO):
        status = 200
        def geturl(self):
            return source.DOWNLOAD_URL
    fetch = Mock(side_effect=lambda *args, **kwargs: Response(buffer.getvalue()))
    monkeypatch.setattr(download, "urlopen", fetch)
    return raw, fetch


def test_sha256(tmp_path):
    path = tmp_path / "known"
    path.write_bytes(b"abc")
    assert download.sha256_file(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_download_and_idempotence(data_project, mocked_source):
    raw, fetch = mocked_source
    first = download.acquire(data_project)
    raw_path = data_project / "data/raw" / source.RAW_FILENAME
    manifest_path = data_project / "data/metadata/dataset_manifest.json"
    times = (raw_path.stat().st_mtime_ns, manifest_path.stat().st_mtime_ns)
    second = download.acquire(data_project)
    assert first == second
    assert raw_path.read_bytes() == raw
    assert first["row_count"] == 4
    assert first["column_count_raw"] == first["column_count_canonical"] == 25
    assert first["retrieved_at"] is not None
    assert times == (raw_path.stat().st_mtime_ns, manifest_path.stat().st_mtime_ns)
    fetch.assert_called_once_with(source.DOWNLOAD_URL, timeout=30)
    assert not list(raw_path.parent.glob("*.tmp"))


def test_existing_file_without_manifest(data_project, mocked_source):
    raw, fetch = mocked_source
    path = data_project / "data/raw" / source.RAW_FILENAME
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    assert download.acquire(data_project)["retrieved_at"] is None
    fetch.assert_not_called()


def test_mismatching_local_file(data_project, mocked_source):
    _, fetch = mocked_source
    path = data_project / "data/raw" / source.RAW_FILENAME
    path.parent.mkdir(parents=True)
    path.write_bytes(b"do not overwrite")
    with pytest.raises(download.AcquisitionError, match="mismatch"):
        download.acquire(data_project)
    assert path.read_bytes() == b"do not overwrite"
    fetch.assert_not_called()


def test_mismatching_download(data_project, mocked_source, monkeypatch):
    monkeypatch.setattr(source, "EXPECTED_SHA256", "0" * 64)
    with pytest.raises(download.AcquisitionError, match="checksum mismatch"):
        download.acquire(data_project)
    assert not (data_project / "data/raw" / source.RAW_FILENAME).exists()


@pytest.mark.parametrize("error", [URLError("offline"), TimeoutError("timed out"), HTTPError(source.DOWNLOAD_URL, 503, "unavailable", None, None), IncompleteRead(b"partial", 100)])
def test_network_failure(data_project, monkeypatch, error):
    monkeypatch.setattr(download, "urlopen", Mock(side_effect=error))
    with pytest.raises(download.AcquisitionError, match="download failed"):
        download.acquire(data_project)
    assert not (data_project / "data/raw" / source.RAW_FILENAME).exists()


def test_bad_archive(data_project, monkeypatch):
    class BadResponse(io.BytesIO):
        status = 200
        def geturl(self):
            return source.DOWNLOAD_URL
    monkeypatch.setattr(download, "urlopen", lambda *args, **kwargs: BadResponse(b"not zip"))
    with pytest.raises(download.AcquisitionError, match="download failed"):
        download.acquire(data_project)


def test_manifest_mismatch(data_project, mocked_source):
    download.acquire(data_project)
    manifest = data_project / "data/metadata/dataset_manifest.json"
    manifest.write_text('{"sha256": "wrong"}', encoding="utf-8")
    with pytest.raises(download.AcquisitionError, match="manifest checksum"):
        download.acquire(data_project)
    assert json.loads(manifest.read_text())["sha256"] == "wrong"


def test_pipeline_independent_of_cwd(data_project, mocked_source, monkeypatch, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    download.acquire(data_project)
    result = run_quality(data_project)
    assert result["rows"] == 4
    assert result["target"]["positive_rate"] == .25
    assert (data_project / "data/metadata/data_quality_summary.json").exists()
    assert not (elsewhere / "data").exists()


@pytest.mark.parametrize("content", ["not json", "[]"])
def test_corrupt_manifest_is_not_silently_replaced(data_project, mocked_source, content):
    download.acquire(data_project)
    path = data_project / "data/metadata/dataset_manifest.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(download.AcquisitionError):
        download.acquire(data_project)
    assert path.read_text(encoding="utf-8") == content


def test_non_uci_redirect_rejected(data_project, monkeypatch):
    class Response(io.BytesIO):
        status = 200
        def geturl(self):
            return "https://example.com/mirror.zip"
    monkeypatch.setattr(download, "urlopen", lambda *a, **kw: Response(b""))
    with pytest.raises(download.AcquisitionError, match="outside"):
        download.acquire(data_project)


def test_publication_race_does_not_overwrite(data_project, mocked_source, monkeypatch):
    def conflicting_link(temporary, destination):
        destination.write_bytes(b"another process wrote this")
        raise FileExistsError()
    monkeypatch.setattr(download.os, "link", conflicting_link)
    with pytest.raises(download.AcquisitionError, match="mismatch"):
        download.acquire(data_project)
    raw_path = data_project / "data/raw" / source.RAW_FILENAME
    assert raw_path.read_bytes() == b"another process wrote this"
    assert not list(raw_path.parent.glob("*.tmp"))
