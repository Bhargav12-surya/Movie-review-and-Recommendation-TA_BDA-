"""Run only through an explicit Alembic command; no URL interpolation/logging."""
from alembic import context
from backend.app.core.config import get_settings
from backend.app.database.session import make_engine
from backend.app.models import Base

target_metadata=Base.metadata
if context.is_offline_mode():
    raise RuntimeError("Offline SQL rendering is disabled to avoid serializing credentials; review frozen schema_v1.sql.")
engine=make_engine(get_settings())
with engine.connect() as connection:
    context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()

