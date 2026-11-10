"""Optional offline CPU speech recognition from manually cached CTranslate2 files."""
import json
from ml.common.artifacts import safe_path,read_json,sha256

def transcribe(file,settings,root):
    if not settings.speech_model_path or not settings.speech_permission_path:
        raise ValueError('Offline speech model unavailable; use text input.')
    folder=safe_path(settings.speech_model_path,root)
    record=read_json(safe_path(settings.speech_permission_path,root))
    if record.get('model_license_reviewed') is not True or not record.get('license_reference') or not record.get('model_revision'):
        raise ValueError('Speech model permission is unreviewed.')
    paths=[path for path in folder.rglob('*') if path.is_file()]
    if len(paths)>2000 or not (folder/'model.bin').is_file(): raise ValueError('Cached CTranslate2 model missing.')
    for path in paths:
        if not path.resolve().is_relative_to(folder) or record.get('files_sha256',{}).get(path.relative_to(folder).as_posix())!=sha256(path):
            raise ValueError('Speech model fingerprint differs.')
    from faster_whisper import WhisperModel
    model=WhisperModel(str(folder),device='cpu',compute_type='int8',local_files_only=True)
    segments,info=model.transcribe(file,beam_size=1,vad_filter=False)
    result=[]
    for segment in segments:
        if segment.end>45 or sum(len(part) for part in result)>2000: raise ValueError('Voice input is limited to45seconds/2000characters.')
        result.append(segment.text)
    return {'text':' '.join(result).strip(),'language':info.language,'model_revision':record['model_revision'],'offline':True}
