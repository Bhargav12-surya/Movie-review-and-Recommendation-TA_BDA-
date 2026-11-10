"""Project text-free real Parquet current-state snapshots for later comparison."""
import json
from .io import ROOT,approved,digest,path,read,run_directory,write

COLUMNS=('review_id','review_revision','movie_id','operation','model_version','consent_eligible','moderation_eligible','is_synthetic','semantic_hash')


def prepare(config_path):
    config=read(config_path);approved(config)
    if config.get('source_permission_reviewed') is not True:raise ValueError('Review source permission before projection.')
    directory=path(config['parquet_directory'])
    files=sorted(directory.glob('*.parquet'))
    if not files or len(files)>1000 or sum(item.stat().st_size for item in files)>1024**3:raise ValueError('A bounded,existing one-level Parquet snapshot is required.')
    hashes={str(item.relative_to(ROOT)):digest(item,1024**3) for item in files}
    from pyarrow.parquet import ParquetFile
    output=run_directory('phase12');count=0
    with (output/'current_state.jsonl').open('x',encoding='utf-8') as stream:
        for source in files:
            reader=ParquetFile(source)
            if set(COLUMNS)-set(reader.schema_arrow.names):raise ValueError('Actual current-state fields are missing; do not synthesize identifiers or revisions.')
            for batch in reader.iter_batches(batch_size=1000,columns=list(COLUMNS)):
                for row in batch.to_pylist():
                    count+=1
                    if count>100000:raise ValueError('Current-state export exceeds the local trial budget.')
                    stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
    if any(digest(name,1024**3)!=checksum for name,checksum in hashes.items()):raise ValueError('Snapshot changed; partial export is retained without a completion manifest.')
    result={'kind':'current_state_projection','status':'prepared','rows':count,'input_sha256':hashes,'config_sha256':digest(config_path),
        'output_sha256':digest(output/'current_state.jsonl'),'report_path':str((output/'projection.json').relative_to(ROOT)),
        'limitations':'Projection is not replay correctness. Compare independently prepared batch and final stream snapshots; retain quarantined history and restart logs separately.'}
    write(output/'projection.json',result);return result
