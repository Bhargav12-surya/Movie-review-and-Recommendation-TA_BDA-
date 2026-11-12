"""Application UUIDs, canonical movie IDs and revisioned evidence stay separate."""
import uuid
from sqlalchemy import Column, String, Text, Integer, BigInteger, Boolean, DateTime, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, func, text as sql_text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


def uid():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sql_text('gen_random_uuid()'))


def created():
    return Column(DateTime(timezone=True), nullable=False, server_default=func.now())


def obj():
    return Column(JSONB, nullable=False, default=dict, server_default=sql_text("'{}'::jsonb"))


def arr():
    return Column(JSONB, nullable=False, default=list, server_default=sql_text("'[]'::jsonb"))


class User(Base):
    __tablename__='users'
    id=uid(); email=Column(String(254), nullable=False, unique=True); display_name=Column(String(80), nullable=False)
    password_hash=Column(Text, nullable=False); is_active=Column(Boolean, nullable=False, default=True, server_default=sql_text('true'))
    is_admin=Column(Boolean, nullable=False, default=False, server_default=sql_text('false')); created_at=created()


class AuthSession(Base):
    __tablename__='auth_sessions'
    id=uid(); user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash=Column(String(64), nullable=False, unique=True); expires_at=Column(DateTime(timezone=True), nullable=False); created_at=created()


class Movie(Base):
    __tablename__='movies'
    id=Column(BigInteger, primary_key=True, autoincrement=False)
    title=Column(String(300), nullable=False, index=True); overview=Column(Text, nullable=False, default='', server_default='')
    release_date=Column(String(10)); runtime_minutes=Column(Integer); original_language=Column(String(20))
    poster_path=Column(Text); backdrop_path=Column(Text); genres=arr(); keywords=arr(); features=obj()
    metadata_source=Column(String(80), nullable=False); canonical_mapping_approved=Column(Boolean, nullable=False, default=False, server_default=sql_text('false'))
    content_version=Column(Integer, nullable=False, default=1, server_default='1'); evidence_version=Column(Integer, nullable=False, default=0, server_default='0'); created_at=created()
    __table_args__=(CheckConstraint('id>0 AND content_version>0 AND evidence_version>=0'), CheckConstraint('runtime_minutes IS NULL OR runtime_minutes>0'))


class ExternalMovieID(Base):
    __tablename__='external_movie_ids'
    movie_id=Column(BigInteger, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True)
    source=Column(String(40), primary_key=True); external_id=Column(String(120), nullable=False)
    __table_args__=(UniqueConstraint('source','external_id'),)


class Review(Base):
    __tablename__='reviews'
    id=uid(); user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    movie_id=Column(BigInteger, ForeignKey('movies.id'), nullable=False, index=True)
    revision=Column(Integer, nullable=False, default=1, server_default='1'); text=Column(Text, nullable=False)
    text_sha256=Column(String(64), nullable=False); language_code=Column(String(16), nullable=False)
    user_rating=Column(Numeric(2,1)); training_permitted=Column(Boolean, nullable=False, default=False, server_default=sql_text('false'))
    evidence_permitted=Column(Boolean, nullable=False, default=False, server_default=sql_text('false'))
    consent_version=Column(String(80), nullable=False); moderation_status=Column(String(20), nullable=False, default='published', server_default='published')
    moderation_permitted=Column(Boolean, nullable=False, default=False, server_default=sql_text('false'))
    analysis_status=Column(String(24), nullable=False, default='pending', server_default='pending')
    is_deleted=Column(Boolean, nullable=False, default=False, server_default=sql_text('false')); is_synthetic=Column(Boolean, nullable=False, default=False, server_default=sql_text('false'))
    created_at=created(); updated_at=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__=(CheckConstraint('revision>0'), CheckConstraint('user_rating IS NULL OR (user_rating>=0.5 AND user_rating<=5 AND mod(user_rating*2,1)=0)'),
        CheckConstraint("analysis_status IN ('pending','running','complete','partial','unavailable','failed','unsupported','cancelled')"),
        Index('reviews_movie_created', 'movie_id','created_at'))


class ReviewRevision(Base):
    __tablename__='review_revisions'
    review_id=Column(UUID(as_uuid=True), ForeignKey('reviews.id', ondelete='CASCADE'), primary_key=True); revision=Column(Integer, primary_key=True)
    text=Column(Text, nullable=False); text_sha256=Column(String(64), nullable=False); language_code=Column(String(16), nullable=False)
    training_permitted=Column(Boolean, nullable=False); evidence_permitted=Column(Boolean, nullable=False); created_at=created()
    __table_args__=(CheckConstraint('revision>0'),)


class Prediction(Base):
    __tablename__='predictions'
    id=uid(); review_id=Column(UUID(as_uuid=True), ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False, index=True)
    review_revision=Column(Integer, nullable=False); component=Column(String(40), nullable=False); model_version=Column(String(128), nullable=False)
    status=Column(String(30), nullable=False); payload=obj(); created_at=created()
    __table_args__=(UniqueConstraint('review_id','review_revision','component','model_version'),CheckConstraint('review_revision>0'))


class ModelArtifact(Base):
    __tablename__='model_artifacts'
    id=uid(); component=Column(String(40), nullable=False); version=Column(String(128), nullable=False)
    config_path=Column(Text, nullable=False); run_path=Column(Text, nullable=False); manifest_sha256=Column(String(64), nullable=False)
    approved=Column(Boolean, nullable=False, default=False, server_default=sql_text('false')); language_scope=arr(); approval_reference=Column(Text, nullable=False)
    created_at=created(); __table_args__=(UniqueConstraint('component','version'),UniqueConstraint('version'),)


class Job(Base):
    __tablename__='jobs'
    id=uid(); kind=Column(String(40), nullable=False); dedupe_key=Column(String(220), nullable=False, unique=True)
    payload=obj(); status=Column(String(20), nullable=False, default='queued', server_default='queued'); attempts=Column(Integer, nullable=False, default=0, server_default='0')
    available_at=Column(DateTime(timezone=True), nullable=False, server_default=func.now()); locked_at=Column(DateTime(timezone=True)); locked_by=Column(String(80)); last_error=Column(String(80))
    created_at=created(); updated_at=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__=(CheckConstraint("status IN ('queued','running','succeeded','failed','unavailable','cancelled')"),CheckConstraint('attempts>=0'),
        CheckConstraint("status!='running' OR (locked_at IS NOT NULL AND locked_by IS NOT NULL)"),Index('jobs_ready','status','available_at'))


class MovieScore(Base):
    __tablename__='movie_scores'
    id=uid(); movie_id=Column(BigInteger, ForeignKey('movies.id', ondelete='CASCADE'), nullable=False, index=True)
    score_type=Column(String(20), nullable=False); target_key=Column(String(80)); evidence_version=Column(Integer, nullable=False)
    score=Column(Numeric(6,3)); payload=obj(); model_version=Column(String(128), nullable=False); method_version=Column(String(128), nullable=False)
    is_stale=Column(Boolean, nullable=False, default=False, server_default=sql_text('false')); created_at=created()
    __table_args__=(CheckConstraint('score IS NULL OR (score>=0 AND score<=100)'),)


class MovieSummary(Base):
    __tablename__='movie_summaries'
    id=uid(); movie_id=Column(BigInteger, ForeignKey('movies.id', ondelete='CASCADE'), nullable=False, index=True)
    evidence_version=Column(Integer, nullable=False); payload=obj(); is_stale=Column(Boolean, nullable=False, default=False, server_default=sql_text('false')); created_at=created()


class MovieEmbedding(Base):
    __tablename__='movie_embeddings'
    movie_id=Column(BigInteger, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True); model_version=Column(String(128), primary_key=True)
    content_version=Column(Integer, nullable=False); dimension=Column(Integer, nullable=False); embedding=Column(Vector(), nullable=False)
    __table_args__=(CheckConstraint('dimension>0 AND dimension<=4096 AND vector_dims(embedding)=dimension'),)


class ReviewEmbedding(Base):
    __tablename__='review_embeddings'
    review_id=Column(UUID(as_uuid=True), ForeignKey('reviews.id', ondelete='CASCADE'), primary_key=True); model_version=Column(String(128), primary_key=True)
    review_revision=Column(Integer, nullable=False); dimension=Column(Integer, nullable=False); embedding=Column(Vector(), nullable=False)
    __table_args__=(CheckConstraint('dimension>0 AND dimension<=4096 AND vector_dims(embedding)=dimension'),)


class Rating(Base):
    __tablename__='ratings'
    user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    movie_id=Column(BigInteger, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True)
    value=Column(Numeric(2,1), nullable=False); updated_at=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__=(CheckConstraint('value>=0.5 AND value<=5 AND mod(value*2,1)=0'),)


class Watchlist(Base):
    __tablename__='watchlists'
    user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    movie_id=Column(BigInteger, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True); created_at=created()


class Preference(Base):
    __tablename__='preferences'
    user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    genres=obj(); themes=obj(); personalization_permitted=Column(Boolean, nullable=False, default=False, server_default=sql_text('false'))
    updated_at=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Interaction(Base):
    __tablename__='interactions'
    id=uid(); user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    movie_id=Column(BigInteger, ForeignKey('movies.id', ondelete='CASCADE'), nullable=False)
    event_type=Column(String(30), nullable=False); payload=obj(); created_at=created()


class Idempotency(Base):
    __tablename__='idempotency'
    user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    scope=Column(String(80), primary_key=True); key_hash=Column(String(64), primary_key=True)
    payload_hash=Column(String(64), nullable=False); response=obj(); created_at=created()


class Conversation(Base):
    __tablename__='conversations'
    id=uid(); user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    state=obj(); created_at=created(); updated_at=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ChatTurn(Base):
    __tablename__='chat_turns'
    id=uid(); conversation_id=Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    user_id=Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    query=Column(Text, nullable=False); reply=obj(); status=Column(String(20), nullable=False, default='pending', server_default='pending'); created_at=created()
