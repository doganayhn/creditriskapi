"""Explicit local Compose validation, synthetic only. Never prints credentials/rows.

Run after building the image. Stops/starts only the selected Compose project;
never deletes volumes. A dedicated test project/database is required.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import urllib.error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--project', default='creditrisk-phase9')
    args = parser.parse_args()
    # Compose parses the env file; keep its resolved config strictly in memory.
    prefix=['docker','compose','--env-file',args.env_file,'-p',args.project]
    report={"synthetic_only":True,"test_set_evaluated":False,"checks":{},"commands":[]}

    def command(parts, *, source=None, expected=0, compose=True, env=None):
        run=subprocess.run((prefix if compose else [])+parts, input=source, text=True,
            capture_output=True, timeout=240, env=env)
        label=' '.join((prefix if compose else [])+parts[:])
        report['commands'].append(label if source is None else label+' [stdin Python; no secrets]')
        print('CHECK: '+' '.join(parts[:4]), flush=True)
        if run.returncode != expected:
            # Never include command output, environment or SQL in exceptions.
            raise RuntimeError('Command failed: '+ ' '.join(parts[:3]))
        return run.stdout

    config=json.loads(command(['config','--format','json']))
    env=config['services']['api']['environment']
    key=env['CREDIT_RISK_API_KEY']; dburl=env['DATABASE_URL']
    password=config['services']['db']['environment']['POSTGRES_PASSWORD']
    port=config['services']['api']['ports'][0]['published']; base=f'http://127.0.0.1:{port}'
    financial={'credit_limit':200000}
    for month in ('09','08','07','06','05','04'):
        financial.update({f'repayment_status_2005_{month}':-1,f'bill_amount_2005_{month}':20000,f'payment_amount_2005_{month}':20000})

    def request(path, authenticated=True, payload=None):
        headers={'Content-Type':'application/json'}
        if authenticated:headers['X-API-Key']=key
        req=urllib.request.Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        try: response=urllib.request.urlopen(req,timeout=40)
        except urllib.error.HTTPError as exc: response=exc
        with response: return response.status,json.load(response),dict(response.headers)

    def ready():
        start=time.monotonic()
        while time.monotonic()-start < 150:
            try:
                if request('/v1/health/ready')[0]==200:return round(time.monotonic()-start,3)
            except (OSError,ValueError):pass
            time.sleep(2)
        raise RuntimeError('API readiness timed out')

    def python(source):
        return command(['exec','-T','api','python','-'],source=source)

    def canonical(value):return {k:v for k,v in value.items() if k not in {'request_id','timestamp'}}

    def check_rows(responses):
        # Only this run's request IDs are queried; no assumption that DB is empty.
        code='''
import json,os
from uuid import UUID
from sqlalchemy import select
from credit_risk.persistence.database import Database
from credit_risk.persistence.models import PredictionEvent
expected=json.loads(INPUT)
db=Database.connect(os.environ['DATABASE_URL'])
with db.engine.connect() as c:
 for response in expected:
  row=c.execute(select(PredictionEvent.__table__).where(PredictionEvent.request_id==UUID(response['request_id']))).mappings().one()
  for field in ('raw_margin','raw_probability','reported_probability','internal_risk_score','display_score','model_version','calibration_version','score_version'):
   assert row[field]==response[field]
  assert row['created_at'].utcoffset().total_seconds()==0
  assert not row['test_set_evaluated']
  assert os.environ['CREDIT_RISK_API_KEY'] not in str(dict(row))
  if 'explanation' in response:
   assert row['reason_codes_json']=={k:response['explanation'][k] for k in ('risk_increasing_drivers','risk_decreasing_drivers')}
   for drivers in row['reason_codes_json'].values():
    assert len(drivers)<=5
    for d in drivers: assert set(d)=={'source_feature','direction','shap_margin_contribution','score_point_contribution'}
  else: assert row['reason_codes_json'] is None
db.close()
print('audit rows matched')
'''.replace('INPUT',repr(json.dumps(responses)))
        assert 'audit rows matched' in python(code)

    command(['up','-d','db']);command(['run','--rm','migrate']);command(['up','-d','api'])
    report['initial_readiness_seconds']=ready()
    assert request('/v1/health/live')[0]==200
    assert request('/v1/predict',False,financial)[0]==401
    report['checks']['health_auth']=True
    code='''
import json,os,platform,importlib.metadata as m
from pathlib import Path
from sqlalchemy import inspect,text
from credit_risk.persistence.database import Database
from credit_risk.service.runtime import load_runtime
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from credit_risk.modeling.calibrators import ProbabilityCalibrator
def forbidden(*a,**k):raise AssertionError('No fit allowed')
for cls in (Pipeline,LogisticRegression,XGBClassifier,ProbabilityCalibrator):cls.fit=forbidden
r=load_runtime('/app')
assert os.getuid()!=0 and len(r.feature_names)==103
assert r.calibration['method']=='identity'
for path in ('data/raw','data/interim','data/processed','.env','.git','.venv'): assert not Path('/app',path).exists()
db=Database.connect(os.environ['DATABASE_URL']);db.check_ready()
with db.engine.connect() as c:
 version=c.execute(text('show server_version')).scalar_one()
 i=inspect(c);columns=i.get_columns('prediction_events')
 assert str(next(x['type'] for x in columns if x['name']=='request_id'))=='UUID'
 assert next(x['type'] for x in columns if x['name']=='created_at').timezone
 indexes={tuple(x['column_names']) for x in i.get_indexes('prediction_events')}
 assert {('created_at',),('model_version',),('api_key_id',)}<=indexes
 assert not {'credit_limit','customer_id','raw_input','features','shap_values'} & {x['name'] for x in columns}
 result={'uid':os.getuid(),'gid':os.getgid(),'postgresql':version,'python':platform.python_version(),
 'versions':{p:m.version(p) for p in ('fastapi','sqlalchemy','alembic','psycopg','xgboost','shap')},
 'model_sha256':r.model_manifest['artifact_sha256'],'preprocessor_sha256':r.preprocessing_manifest['serialization_sha256'],
 'feature_width':len(r.feature_names),'calibration':r.calibration['method']}
db.close();print(json.dumps(result))
'''
    report['runtime']=json.loads(python(code))
    report['checks']['postgres_schema_frozen_runtime_nonroot_no_data']=True
    assert 'No broken requirements' in command(['exec','-T','api','python','-m','pip','check'])
    cid=command(['ps','-q','api']).strip()
    info=json.loads(command(['docker','inspect',cid],compose=False))[0]
    assert info['HostConfig']['ReadonlyRootfs']
    assert any(m['Destination']=='/app/artifacts' and not m['RW'] for m in info['Mounts'])
    image=info['Image'];image_info=json.loads(command(['docker','image','inspect',image],compose=False))[0]
    assert all(secret not in json.dumps(image_info) for secret in (key,password,dburl))
    report['image_bytes']=image_info['Size']
    command(['docker','run','--rm','--read-only','--entrypoint','python',image,'-c',
        "from pathlib import Path; assert all(not Path('/app',p).exists() for p in ('artifacts','data/raw','data/interim','data/processed','.env','.git','.venv'))"],compose=False)
    missing= subprocess.run(['docker','run','--rm','--read-only','--entrypoint','python',image,'-c',
        "from credit_risk.service.runtime import load_runtime; load_runtime('/app')"],capture_output=True,text=True,timeout=60)
    assert missing.returncode!=0
    assert 'FileNotFoundError' in missing.stderr
    report['checks']['image_privacy_readonly_missing_artifacts']=True
    responses=[]
    for endpoint in ('predict','explain'):
        status,value,_=request('/v1/'+endpoint,payload=financial);assert status==200
        assert value['raw_probability']==value['reported_probability']
        assert not {'decision','recommendation','risk_band'} & set(value)
        responses.append(value)
    check_rows(responses);report['checks']['predict_explain_persistence']=True
    command(['restart','api']);ready()
    again=[]
    for endpoint,prior in zip(('predict','explain'),responses):
        status,value,_=request('/v1/'+endpoint,payload=financial);assert status==200
        assert canonical(value)==canonical(prior) and value['request_id']!=prior['request_id']
        again.append(value)
    check_rows(responses+again);report['checks']['api_restart_determinism']=True
    command(['restart','db']);ready();check_rows(responses+again)
    report['checks']['database_restart_persistence']=True
    command(['stop','db'])
    try:
        assert request('/v1/health/ready')[0]==503
        for endpoint in ('predict','explain'):
            assert request('/v1/'+endpoint,payload=financial)[0]==503
    finally:
        command(['start','db']);ready()
    report['checks']['database_failure_recovery']=True
    def concurrent(n):
        endpoint='predict' if n%2==0 else 'explain'
        status,value,_=request('/v1/'+endpoint,payload=financial);assert status==200
        assert canonical(value)==canonical(responses[n%2])
        return value
    with ThreadPoolExecutor(max_workers=10) as pool: concurrent_rows=list(pool.map(concurrent,range(10)))
    assert len({r['request_id'] for r in concurrent_rows})==10
    check_rows(concurrent_rows);report['concurrent_requests']=10
    report['checks']['concurrency_unique_isolated_no_deadlock']=True
    logs=command(['logs','--no-color'])
    assert all(secret not in logs for secret in (key,password,dburl))
    assert all(token not in logs for token in ('credit_limit','reported_probability','internal_risk_score','risk_increasing_drivers','SELECT ','INSERT INTO'))
    assert 'Application shutdown complete' in logs
    report['checks']['graceful_shutdown_and_initial_logs_privacy']=True
    # Separate process restart gives a fresh 3-request allowance without sleeps.
    reduced={**os.environ,'RATE_LIMIT_REQUESTS_PER_MINUTE':'3'}
    command(['up','-d','--no-deps','--force-recreate','api'],env=reduced);ready()
    try:
        for _ in range(3):assert request('/v1/predict',payload=financial)[0]==200
        status,_,headers=request('/v1/predict',payload=financial)
        assert status==429 and int({k.lower():v for k,v in headers.items()}['retry-after'])>0
        assert request('/v1/health/live')[0]==200
        report['checks']['rate_limit_retry_after']=True
        logs=command(['logs','--no-color'])
        assert all(secret not in logs for secret in (key,password,dburl))
        assert all(token not in logs for token in ('credit_limit','reported_probability','internal_risk_score','risk_increasing_drivers','SELECT ','INSERT INTO'))
        report['checks']['logs_privacy']=True
    finally:
        command(['up','-d','--no-deps','--force-recreate','api']);ready()
    for action in ('audit','summary'):
        result=json.loads(command(['exec','-T','api','python','-m','credit_risk.ops.run',action]))
        assert result['audit']['valid'];report[action]=result
    report['checks']['aggregate_operations']=True
    # Evidence stays in ignored local storage; it contains aggregates only.
    output=Path('.local/phase9_validation.json');output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'result':'PASS','checks':report['checks'],'concurrent_requests':10,'test_set_evaluated':False}))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Exception text may contain assertion input in future changes; omit it.
        import traceback
        frames=traceback.extract_tb(exc.__traceback__)
        print(json.dumps({'result':'FAIL','error_type':type(exc).__name__,'line':frames[-1].lineno,'test_set_evaluated':False}))
        raise SystemExit(1)
