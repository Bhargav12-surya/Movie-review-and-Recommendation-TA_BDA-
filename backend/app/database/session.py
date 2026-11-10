from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker
from fastapi import Request


def make_engine(settings):
    if not settings.database_password.get_secret_value():
        raise ValueError('Set the local database password; no default credential is supplied.')
    url = URL.create('postgresql+psycopg', username=settings.database_user,
        password=settings.database_password.get_secret_value(), host=settings.database_host,
        port=settings.database_port, database=settings.database_name)
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=2, echo=False,
        hide_parameters=True, connect_args={'connect_timeout': 5, 'options': '-c statement_timeout=15000 -c lock_timeout=5000'})


def get_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)


def get_session(request:Request):
    factory = request.app.state.session_factory
    if factory is None:
        from fastapi import HTTPException
        raise HTTPException(503, detail='database_not_configured')
    with factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
