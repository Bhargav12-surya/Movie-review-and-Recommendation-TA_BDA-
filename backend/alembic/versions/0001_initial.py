"""Frozen application schema; no startup creation or synthetic seeds."""
from pathlib import Path
from alembic import op, context
revision='0001_initial'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    sql=(Path(__file__).resolve().parents[1]/'schema_v1.sql').read_text(encoding='utf-8')
    for statement in sql.split(';'):
        if statement.strip():
            op.execute(statement)

def downgrade():
    if context.get_x_argument(as_dictionary=True).get('allow_destructive_downgrade')!='true':
        raise RuntimeError('Destructive rollback requires an explicit reviewed -x allow_destructive_downgrade=true.')
    for name in ["chat_turns","conversations","idempotency","interactions","preferences","watchlists","ratings","review_embeddings","movie_embeddings","movie_summaries","movie_scores","jobs","model_artifacts","predictions","review_revisions","reviews","external_movie_ids","movies","auth_sessions","users"]:
        op.drop_table(name)

