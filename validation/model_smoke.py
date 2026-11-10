"""Explicit real local model load/infer/reload check, never training/evaluation."""
import gc
import hashlib
import math
import time
from .io import ROOT,approved,digest,path,read,rows
from .resources import sample


def equivalent(left,right,tolerance=1e-5):
    if type(left) in (int,float) and type(right) in (int,float):return math.isfinite(left) and math.isfinite(right) and math.isclose(left,right,rel_tol=tolerance,abs_tol=tolerance)
    if isinstance(left,dict) and isinstance(right,dict):return set(left)==set(right) and all(equivalent(left[key],right[key],tolerance) for key in left)
    if isinstance(left,list) and isinstance(right,list):return len(left)==len(right) and all(equivalent(a,b,tolerance) for a,b in zip(left,right))
    return type(left)==type(right) and left==right


def evaluate(config_path):
    config_hash=digest(config_path);config=read(config_path);approved(config);source=config['samples_path']
    if config['samples_sha256']!=digest(source):raise ValueError('Inference sample manifest differs.')
    samples=list(rows(source,maximum_rows=4,maximum_bytes=1024**2))
    if not samples:raise ValueError('Supply1..4 legitimate inference samples; never use fabricated demonstration reviews.')
    for row in samples:
        if (row.get('inference_permitted') is not True or row.get('is_synthetic') is not False or row.get('is_deleted') is not False
            or not row.get('consent_or_license_ref') or row.get('language_code')!=config['language_code'] or not isinstance(row.get('text'),str)
            or not 1<=len(row['text'])<=20000 or hashlib.sha256(row['text'].encode()).hexdigest()!=row.get('text_sha256')):
            raise ValueError('Reviewed original bounded inference text/permissions/language required.')
    component=config['component'];device=config.get('device','cpu')
    if device not in {'cpu','cuda'}:raise ValueError('Choose explicit cpu/cuda; no silent fallback for a GPU trial.')
    if component=='sentiment_tfidf' and device!='cpu':raise ValueError('The classical baseline runs on CPU; do not label it a CUDA experiment.')
    inputs=[path(config_path),path(source)]
    if component=='aspect_pipeline':
        inputs += [path(config[name]) for name in ('extraction_config','sentiment_config')]
        for name in ('extraction_run','sentiment_run'):inputs += [path(config[name])/'model_manifest.json',path(config[name])/'input_contract.json']
    else:
        inputs.append(path(config['model_config']))
        directory=path(config['run_directory'])
        inputs += [directory/'training_report.json',directory/'model.json'] if component=='sentiment_tfidf' else [directory/'model_manifest.json',directory/'input_contract.json']
    frozen={str(item.relative_to(ROOT)):digest(item) for item in inputs}
    def unchanged():
        if any(digest(name)!=checksum for name,checksum in frozen.items()):raise ValueError('Model/config/sample inputs changed between reload observations.')
    if frozen[str(path(config_path).relative_to(ROOT))]!=config_hash:raise ValueError('Smoke config changed while preparing inputs.')
    if frozen[str(path(source).relative_to(ROOT))]!=config['samples_sha256']:raise ValueError('Inference samples changed while reading.')
    before=sample();times=[];outputs=[]
    for _ in range(2):
        unchanged()
        started=time.perf_counter()
        if component=='aspect_pipeline':
            from ml.aspect_common.config import load_config
            from ml.aspect_common.cli import inference_example
            from ml.aspect_pipeline.predict import predict
            value=predict([inference_example(row['text'],row['language_code']) for row in samples],load_config(path(config['extraction_config'])),
                str(path(config['extraction_run'])),load_config(path(config['sentiment_config'])),str(path(config['sentiment_run'])),device)
        elif component in {'sentiment_transformer','multilingual_sentiment'}:
            from ml.common.config import load_config
            from ml.common.transformer_engine import predict
            value=predict(load_config(path(config['model_config'])),str(path(config['run_directory'])),[row['text'] for row in samples],config['language_code'],device)
        elif component=='sentiment_tfidf':
            from ml.common.config import load_config
            from ml.sentiment_tfidf.predict import predict
            value=predict(load_config(path(config['model_config'])),path(config['run_directory']),[row['text'] for row in samples],config['language_code'])
        else:raise ValueError('Use supported trained sentiment or aspect pipeline smoke checks; other component reports remain separate evidence.')
        times.append(time.perf_counter()-started);outputs.append(value);gc.collect()
        import sys
        torch=sys.modules.get('torch')
        if torch is not None and torch.cuda.is_initialized():torch.cuda.empty_cache()
        unchanged()
    stable=equivalent(outputs[0],outputs[1]);after=sample()
    predictions=outputs[-1].get('predictions',[]) if isinstance(outputs[-1],dict) else outputs[-1]
    available=bool(predictions) and all(row.get('status')=='analysed' for row in predictions)
    return {'kind':'actual_model_reload_smoke','status':'failed' if not stable else 'passed' if available else 'incomplete','component':component,'device':device,'sample_count':len(samples),
        'samples_sha256':config['samples_sha256'],'config_sha256':config_hash,'input_sha256':frozen,'load_plus_inference_seconds':times,'resources_before':before,'resources_after':after,
        'limitations':'Reload numerical agreement is not accuracy,checkpoint training-resume equivalence,calibration or language validation. Both calls include fresh local loading; resources are sampled,not model peak allocations. No text or predictions are written.'}
