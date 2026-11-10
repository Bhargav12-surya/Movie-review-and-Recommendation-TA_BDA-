from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / 'backend/.env', extra='ignore', case_sensitive=False)
    database_host: str = '127.0.0.1'
    database_port: int = Field(5432, ge=1, le=65535)
    database_name: str = 'movie_intelligence'
    database_user: str = 'movie_app'
    database_password: SecretStr = SecretStr('')
    frontend_origin: str = 'http://localhost:3000'
    registration_enabled: bool = True
    auth_token_ttl_minutes: int = Field(480, ge=5, le=1440)
    maximum_request_bytes: int = Field(2097152, ge=4096, le=8388608)
    requests_per_minute: int = Field(120, ge=10, le=1000)
    maximum_pending_jobs: int = Field(1000, ge=1, le=10000)
    maximum_job_attempts: int = Field(6, ge=1, le=20)
    inference_device: str = 'cpu'
    scoring_config: str = 'scoring/config.example.json'
    scoring_approval: str = 'scoring/approval.example.json'
    hybrid_config: str = 'configs/recommendation/hybrid.json'
    factor_directory: str | None = None
    factor_mapping: str | None = None
    speech_model_path: str | None = None
    speech_permission_path: str | None = None
    poster_cache: str = 'data/processed/posters'
    target_score_policies: dict[str,dict[str,str]] = Field(default_factory=dict)
    discovery_minimum_aspect_score: float | None = Field(None, ge=0, le=100)
    review_event_directory: str = 'data/events/reviews-live'


@lru_cache
def get_settings():
    return BackendSettings()
