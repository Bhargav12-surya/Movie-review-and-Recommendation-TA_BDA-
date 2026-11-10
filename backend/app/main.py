"""Explicit app factory; no database creation,seeding or weight loading."""
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from backend.app.core.config import get_settings
from backend.app.core.middleware import BoundsMiddleware
from backend.app.core.errors import ServiceUnavailable
from backend.app.database.session import make_engine,get_session_factory

def create_app():
    settings=get_settings()
    @asynccontextmanager
    async def lifespan(app):
        engine=make_engine(settings) if settings.database_password.get_secret_value() else None
        app.state.engine=engine;app.state.session_factory=get_session_factory(engine) if engine else None
        yield
        if engine:engine.dispose()
    app=FastAPI(title='Framewise local movie intelligence',version='0.1.0',lifespan=lifespan,debug=False,docs_url='/docs')
    app.state.engine=None;app.state.session_factory=None
    app.add_middleware(BoundsMiddleware,maximum_bytes=settings.maximum_request_bytes,requests_per_minute=settings.requests_per_minute)
    app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin],allow_credentials=False,
        allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type','Idempotency-Key'])
    @app.exception_handler(RequestValidationError)
    async def validation(request,error):
        return JSONResponse({'error':{'code':'invalid_request','fields':[list(item['loc']) for item in error.errors()]}},422)
    @app.exception_handler(HTTPException)
    async def http_error(request,error):
        return JSONResponse({'error':{'code':error.detail if isinstance(error.detail,str) else 'request_failed'}},error.status_code,headers=error.headers)
    @app.exception_handler(SQLAlchemyError)
    async def database_error(request,error):
        return JSONResponse({'error':{'code':'database_operation_unavailable'}},503)
    @app.exception_handler(ServiceUnavailable)
    async def unavailable(request,error):return JSONResponse({'error':{'code':error.code}},503)
    @app.exception_handler(ValueError)
    async def invalid_state(request,error):return JSONResponse({'error':{'code':'validated_artifact_or_configuration_required'}},503)
    @app.exception_handler(Exception)
    async def unexpected(request,error):return JSONResponse({'error':{'code':'internal_operation_failed'}},500)
    @app.get('/api/v1/health')
    def health():return {'status':'alive','core_inference':'local_only'}
    @app.get('/api/v1/ready')
    def ready(request:Request):
        if request.app.state.engine is None:return JSONResponse({'ready':False,'reason':'database_not_configured'},503)
        try:
            with request.app.state.engine.connect() as connection:
                version=connection.scalar(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
                connection.execute(text('SELECT 1 FROM alembic_version LIMIT 1'))
            return JSONResponse({'ready':bool(version),'pgvector_version':version,'model_readiness':'inspect_approved_registry_separately'},200 if version else 503)
        except SQLAlchemyError:return JSONResponse({'ready':False,'reason':'database_schema_unavailable'},503)
    from backend.app.api.routes import auth,movies,reviews,profile,recommendations,admin,chat
    for module in (auth,movies,reviews,profile,recommendations,admin,chat):app.include_router(module.router,prefix='/api/v1')
    return app
