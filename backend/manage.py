"""Explicit manual administration. No automatic database creation or seeding."""
import argparse
import getpass
import re
from pathlib import Path
from sqlalchemy import select,delete
from backend.app.core.config import ROOT,get_settings
from backend.app.database.session import make_engine,get_session_factory
from backend.app.models import User,Movie,ExternalMovieID,MovieEmbedding
from backend.app.auth.security import PASSWORDS
from backend.app.repositories.catalogue import public_movie
from ml.common.artifacts import safe_path,read_json,sha256

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('create-admin','import-catalogue','embed-catalogue'))
    parser.add_argument('--input');parser.add_argument('--registry');parser.add_argument('--config');parser.add_argument('--model-version')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if not args.execute:raise ValueError('Explicit --execute is required. No database action was performed.')
    engine=make_engine(get_settings());factory=get_session_factory(engine)
    with factory() as session:
        if args.action=='create-admin':
            email=input('Administrator email: ').strip().casefold();name=input('Display name: ').strip()
            password=getpass.getpass('New password (12..128 characters): ')
            if not 12<=len(password)<=128 or '@' not in email or not name:raise ValueError('Invalid administrator account input.')
            if session.scalar(select(User).where(User.email==email)):raise ValueError('Account already exists; no automatic promotion.')
            session.add(User(email=email,display_name=name,password_hash=PASSWORDS.hash(password),is_admin=True));session.commit()
        elif args.action=='import-catalogue':
            from dataset_tools.recordio import load_registry
            from ml.common.data import _rows
            registry=safe_path(args.registry,ROOT);ids,blockers=load_registry(registry)
            if blockers:raise ValueError('Approved canonical registry required.')
            input_path=safe_path(args.input,ROOT);input_hash=sha256(input_path);registry_hash=sha256(registry)
            seen=set()
            for index,row in enumerate(_rows(input_path)):
                if index>=100000 or str(row.get('movie_id')) not in ids or row.get('metadata_use_permitted') is not True or not row.get('license_reference'):
                    raise ValueError('Bounded licensed canonical metadata required; no guessed mappings.')
                identifier=int(row['movie_id'])
                if identifier in seen or session.get(Movie,identifier):raise ValueError('Existing or duplicate catalogue ID; update requires a separately reviewed content-version operation.')
                seen.add(identifier)
                features=dict(row.get('features',{}))
                features['import_provenance']={'license_reference':row['license_reference'],'metadata_input_sha256':input_hash,'canonical_registry_sha256':registry_hash}
                session.add(Movie(id=identifier,title=row['title'],overview=row.get('overview',''),genres=row.get('genres',[]),keywords=row.get('keywords',[]),
                    release_date=row.get('release_date'),runtime_minutes=row.get('runtime_minutes'),original_language=row.get('original_language'),
                    poster_path=row.get('poster_path'),metadata_source=row['metadata_source'],canonical_mapping_approved=True,features=features))
                external_ids=row.get('external_ids',{})
                if external_ids and (row.get('external_mappings_approved') is not True or not row.get('external_mapping_reference')):
                    raise ValueError('External movie mappings require explicit reviewed provenance independent of title matching.')
                for source,external in external_ids.items():
                    if source=='imdb':
                        if not isinstance(external,str) or not re.fullmatch(r'(?:tt)?[0-9]{7,10}',external):raise ValueError('IMDb IDs must preserve their validated original digit strings.')
                        if not external.startswith('tt'):external='tt'+external
                    elif source in {'tmdb','movielens'}:
                        if isinstance(external,bool) or not re.fullmatch(r'[1-9][0-9]*',str(external)):raise ValueError('Positive validated external ID required.')
                    else:raise ValueError('Unsupported external namespace; review its identifier policy before import.')
                    session.add(ExternalMovieID(movie_id=identifier,source=source,external_id=str(external)))
            if sha256(input_path)!=input_hash or sha256(registry)!=registry_hash:raise ValueError('Catalogue input changed during import; transaction is not committed.')
            session.commit()
        else:
            from ml.embeddings.predict import encode
            from ml.common.records import load_config
            config=load_config(safe_path(args.config,ROOT))
            if not args.model_version:raise ValueError('Actual registered embedding model version required.')
            from backend.app.services.artifacts import resolve
            artifact=resolve(session,'embeddings')
            if artifact.version!=args.model_version or safe_path(artifact.config_path,ROOT)!=safe_path(args.config,ROOT):
                raise ValueError('Embedding version/config does not match the approved active artifact.')
            # Small bounded batches; no full catalogue or MovieLens pandas load.
            last=0
            while True:
                rows=session.scalars(select(Movie).where(Movie.id>last,Movie.canonical_mapping_approved.is_(True)).order_by(Movie.id).limit(32)).all()
                if not rows:break
                result=encode([row.title+'\n'+row.overview for row in rows],config)
                for row,vector in zip(rows,result['vectors']):
                    existing=session.get(MovieEmbedding,(row.id,args.model_version))
                    if existing:raise ValueError('Embedding version already exists; no overwrite.')
                    session.add(MovieEmbedding(movie_id=row.id,model_version=args.model_version,content_version=row.content_version,
                        dimension=result['dimension'],embedding=vector.tolist()))
                session.commit();last=rows[-1].id
    engine.dispose()

if __name__=='__main__':main()
