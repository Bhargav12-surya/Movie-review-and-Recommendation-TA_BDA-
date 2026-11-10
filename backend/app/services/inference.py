"""Real local trained inference, loaded only on demand by one worker."""
import gc
from backend.app.core.config import ROOT
from backend.app.core.errors import ServiceUnavailable
from .artifacts import resolve

class ModelRuntime:
    def __init__(self,settings): self.settings=settings

    def sentiment(self,session,text,language):
        last=None
        for component in ('multilingual_sentiment','sentiment_transformer'):
            try:
                row=resolve(session,component,language)
                from ml.common.config import load_config
                from ml.common.transformer_engine import predict
                result=predict(load_config(ROOT/row.config_path),str(ROOT/row.run_path),[text],language,self.settings.inference_device)[0]
                if result.get('status')!='analysed': raise ServiceUnavailable('language_unsupported')
                result.update(serving_approved=True,source_component=component)
                return {'component':'sentiment','model_version':row.version,'status':'analysed','payload':result}
            except ServiceUnavailable as error: last=error
        raise last or ServiceUnavailable()

    def aspects(self,session,text,language):
        extraction=resolve(session,'aspect_extraction',language); sentiment=resolve(session,'aspect_sentiment',language)
        from ml.aspect_common.config import load_config
        from ml.aspect_common.cli import inference_example
        from ml.aspect_pipeline.predict import predict
        result=predict([inference_example(text,language)],load_config(ROOT/extraction.config_path),str(ROOT/extraction.run_path),
            load_config(ROOT/sentiment.config_path),str(ROOT/sentiment.run_path),self.settings.inference_device)[0]
        result['dependency_versions']=[extraction.version,sentiment.version]
        return {'component':'aspects','model_version':sentiment.version,'status':'analysed','payload':result}

    def release(self):
        gc.collect()
        import sys
        torch=sys.modules.get('torch')
        if torch is not None and torch.cuda.is_initialized(): torch.cuda.empty_cache()
