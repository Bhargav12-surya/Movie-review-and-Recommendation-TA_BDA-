"""Copy an explicitly approved artifact allowlist into a new verifiable directory."""
import hashlib
from pathlib import Path
from .io import ROOT,approved,digest,path,read,run_directory,write


def prepare(config_path):
    config=read(config_path);approved(config);entries=config.get('files',[])
    if not entries or len(entries)>500:raise ValueError('A nonempty reviewed allowlist of at most500 files is required.')
    maximum=config.get('maximum_total_bytes',64*1024**2)
    if type(maximum) is not int or not 1<=maximum<=8*1024**3:raise ValueError('Declare a bounded budget at most8GiB.')
    validated=[];total=0;seen=set()
    for item in entries:
        source=path(item['path']);relative=source.relative_to(ROOT)
        if (relative.parts[0] in {'data','logs','temp'} or source.suffix.lower() in {'.db','.sqlite','.sqlite3','.pem','.key'} or
            source.name.startswith('.env') or item.get('redistribution_permitted') is not True or item.get('contains_private_data') is not False or
            not item.get('license_reference') or not item.get('reviewed_by')):
            raise ValueError('Raw/restricted/private/credential files cannot enter the shareable bundle.')
        if relative in seen or not source.is_file():raise ValueError('Unique existing allowlist entries are required.')
        seen.add(relative);total+=source.stat().st_size
        if total>maximum:raise ValueError('Approved bundle storage budget exceeded.')
        if digest(source,maximum)!=item.get('sha256'):raise ValueError('Allowlisted source hash changed.')
        validated.append((source,relative,item))
    directory=run_directory('bundle');manifest=[]
    for source,relative,item in validated:
        target=directory/'files'/relative;target.parent.mkdir(parents=True,exist_ok=True);checksum=hashlib.sha256()
        with source.open('rb') as incoming,target.open('xb') as outgoing:
            for chunk in iter(lambda:incoming.read(1024*1024),b''):outgoing.write(chunk);checksum.update(chunk)
        if checksum.hexdigest()!=item['sha256']:raise ValueError('Source changed during copy; partial directory is retained and has no completion manifest.')
        manifest.append({'path':relative.as_posix(),'sha256':item['sha256'],'bytes':target.stat().st_size,'license_reference':item['license_reference']})
    result={'kind':'reviewed_distribution_bundle','status':'prepared','files':manifest,'total_bytes':total,'config_sha256':digest(config_path),
        'limitations':'Prepared is not academic acceptance. Source code has no automatically selected license; preserve notices and confirm all listed distribution rights.'}
    write(directory/'manifest.json',result)
    return {**result,'directory':str(directory.relative_to(ROOT))}
