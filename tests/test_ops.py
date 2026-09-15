"""Synthetic operational diagnostics; no Docker or dataset needed."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4
import numpy as np
import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from credit_risk.ops.audit import audit_rows
from credit_risk.ops.baseline import build_baseline, operations_manifest, publish_baseline
from credit_risk.ops.contracts import contracts
from credit_risk.ops.monitoring import bin_counts, psi, summarize
from credit_risk.ops.run import collect, main
from credit_risk.persistence.database import Database
from credit_risk.persistence.models import Base, PredictionEvent

ROOT = Path(__file__).resolve().parents[1]


def row():
    value = contracts(ROOT)
    return {**value, "request_id": uuid4(), "created_at": datetime.now(timezone.utc), "api_key_id": "synthetic",
        "endpoint_type": "predict", "explainability_version": None, "explanation_requested": False,
        "score_point_decomposition_supported": None, "reason_codes_json": None, "raw_margin": -1.,
        "raw_probability": .2, "reported_probability": .2, "internal_risk_score": 520.,
        "display_score": 520, "inference_latency_ms": 10., "test_set_evaluated": False}


def test_valid_and_empty_audit():
    assert audit_rows([row()], contracts(ROOT))["valid"]
    assert audit_rows([], contracts(ROOT))["rows_checked"] == 0


@pytest.mark.parametrize("field,value,counter", [
    ("model_version", "wrong", "version_mismatch_rows"),
    ("model_artifact_sha256", "wrong", "version_mismatch_rows"),
    ("api_version", "wrong", "version_mismatch_rows"),
    ("calibration_version", "wrong", "version_mismatch_rows"),
    ("calibration_method", "isotonic", "version_mismatch_rows"),
    ("score_version", "wrong", "version_mismatch_rows"),
    ("reported_probability", 1.1, "probability_violation_rows"),
    ("raw_probability", float('nan'), "probability_violation_rows"),
    ("reported_probability", .3, "probability_violation_rows"),
    ("test_set_evaluated", True, "test_flag_violation_rows"),
    ("internal_risk_score", float('inf'), "numeric_violation_rows"),
    ("inference_latency_ms", -1., "numeric_violation_rows"),
    ("endpoint_type", "other", "endpoint_violation_rows"),
    ("endpoint_type", "explain", "explanation_contract_violation_rows"),
])
def test_audit_invalid(field, value, counter):
    r = row(); r[field] = value
    result = audit_rows([r], contracts(ROOT))
    assert result["invalid_rows"] == result[counter] == 1 and not result["valid"]
    assert str(r["request_id"]) not in json.dumps(result)


def test_duplicate_and_explanation():
    r = row()
    assert audit_rows([r,r], contracts(ROOT))["duplicate_request_ids"] == 1
    r.update(endpoint_type="explain", explanation_requested=True,
        explainability_version=contracts(ROOT)["explainability_version"], score_point_decomposition_supported=True)
    assert audit_rows([r], contracts(ROOT))["valid"]


def test_baseline_and_boundaries():
    b = build_baseline(ROOT)
    assert b["source_count"] == 4500 and b["source_population"] == "validation"
    assert sum(b["expected_bin_proportions"]) == pytest.approx(1)
    assert b["expected_mean_score"] == pytest.approx(531.9659941618735)
    assert bin_counts([-100, 0, 1, 2, 100], [0,2]) == [1,2,2]
    assert bin_counts([], [0,2]) == [0,0,0]


def test_psi_and_zero_bins():
    assert psi([1,2,3],[1,2,3]) == 0
    assert psi([0,10],[5,5]) > 0
    assert np.isfinite(psi([0,10],[10,0]))
    a=np.array([.25,.75]); e=np.array([.5,.5])
    assert psi(a,e) == pytest.approx(float(sum((a-e)*np.log(a/e))))


@pytest.mark.parametrize('a,e', [([],[]),([0,0],[1,1]),([-1,2],[1,1]),([1],[1,2]),([float('nan')],[1])])
def test_invalid_psi(a,e):
    with pytest.raises(ValueError): psi(a,e)


def test_summary_quantiles_privacy_and_empty():
    rows=[{**row(), "inference_latency_ms": float(i), "internal_risk_score": 500.+i} for i in range(1,11)]
    b=build_baseline(ROOT); result=summarize(rows,b)
    assert result["event_count"] == result["predict_count"] == 10
    assert result["inference_latency_ms"]["quantiles"] == pytest.approx({'p50':5.5,'p95':9.55,'p99':9.91})
    assert result["internal_score"]["mean"] == 505.5
    assert sum(result["score_bin_counts"]) == 10 and result["sample_size_limited"]
    assert not summarize(rows,b,10)["sample_size_limited"]
    output=json.dumps(result,allow_nan=False)
    assert not any(k in output for k in ('request_id','api_key_id','reason_codes_json','created_at'))
    empty=summarize([],b)
    assert empty["score_psi"] is None and empty["reported_probability"]["mean"] is None


def test_isolated_database_audit_window_and_constraints():
    engine=create_engine('sqlite://'); Base.metadata.create_all(engine); db=Database(engine)
    now=datetime.now(timezone.utc)
    old=row();old['created_at']=now-timedelta(days=2)
    valid=row();wrong=row();wrong['model_version']='wrong'
    with Session(engine) as session:
        session.add_all(PredictionEvent(**r) for r in (old,valid,wrong));session.commit()
    rows=collect(db,now-timedelta(hours=1),now+timedelta(hours=1))
    assert len(rows)==2 and 'reason_codes_json' not in rows[0]
    assert audit_rows(rows,contracts(ROOT))['invalid_rows']==1
    for changes in ({'reported_probability':2.},{'test_set_evaluated':True},{'request_id':valid['request_id']}):
        with Session(engine) as session:
            session.add(PredictionEvent(**{**row(),**changes}))
            with pytest.raises(Exception): session.commit()
            session.rollback()
    db.close()


def test_cli_failure_privacy(monkeypatch,capsys):
    monkeypatch.setenv('DATABASE_URL','secret-invalid-url')
    assert main(['audit'])==1
    output=capsys.readouterr().out
    assert 'secret-invalid-url' not in output and json.loads(output)['test_set_evaluated'] is False


def test_no_fit_and_manifest(monkeypatch):
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LogisticRegression
    from xgboost import XGBClassifier
    from credit_risk.modeling.calibrators import ProbabilityCalibrator
    def forbidden(*a,**k): raise AssertionError('Operations must not fit')
    for cls in (Pipeline, LogisticRegression, XGBClassifier, ProbabilityCalibrator):monkeypatch.setattr(cls,'fit',forbidden)
    b=build_baseline(ROOT); summarize([row()],b);audit_rows([row()],contracts(ROOT))
    m=operations_manifest(ROOT)
    assert m['postgres_validated'] is False and m['api_workers']==1 and m['test_set_evaluated'] is False
    assert m['model_sha256']==contracts(ROOT)['model_artifact_sha256']


def test_baseline_freeze_and_serialization(tmp_path):
    import shutil
    shutil.copytree(ROOT/'data/metadata',tmp_path/'data/metadata')
    first=publish_baseline(tmp_path)
    p=tmp_path/'data/metadata/monitoring_baseline.json';before=p.read_bytes()
    assert publish_baseline(tmp_path)==first and p.read_bytes()==before
    first['score_bin_boundaries'][0]+=1
    p.write_text(json.dumps(first))
    with pytest.raises(ValueError,match='new reviewed version'):publish_baseline(tmp_path)


def test_cli_summary_and_invalid_audit(monkeypatch,capsys):
    import credit_risk.ops.run as run
    class FakeDB:
        def check_ready(self): pass
        def close(self): pass
    monkeypatch.setenv('DATABASE_URL','private-test-url')
    monkeypatch.setenv('CREDIT_RISK_PROJECT_ROOT',str(ROOT))
    monkeypatch.setattr(run.Database,'connect',lambda value:FakeDB())
    monkeypatch.setattr(run,'collect',lambda *a:[row()])
    assert main(['summary'])==0
    value=json.loads(capsys.readouterr().out)
    assert value['summary']['event_count']==1 and value['audit']['valid']
    bad=row();bad['model_version']='wrong'
    monkeypatch.setattr(run,'collect',lambda *a:[bad])
    assert main(['summary'])==1
    value=json.loads(capsys.readouterr().out)
    assert 'summary' not in value and value['audit']['invalid_rows']==1


def test_compose_safety():
    c=yaml.safe_load((ROOT/'compose.yaml').read_text());s=c['services']
    assert set(s)=={'db','migrate','api'} and 'version' not in c
    assert 'ports' not in s['db'] and s['db']['image']=='postgres:17-alpine'
    assert s['api']['ports'][0].startswith('127.0.0.1:') and s['api']['read_only']
    assert s['api']['volumes'][0]['read_only'] and s['api']['volumes'][0]['source']=='./artifacts'
    assert s['api']['depends_on']['migrate']['condition']=='service_completed_successfully'
    assert s['migrate']['depends_on']['db']['condition']=='service_healthy'
    d=(ROOT/'Dockerfile').read_text()
    assert 'USER 10001:10001' in d and ':latest' not in d and '"--workers", "1"' in d
    assert 'COPY artifacts' not in d and 'COPY . .' not in d
    assert 'POSTGRES_PASSWORD:?Set' in s['db']['environment']['POSTGRES_PASSWORD']
