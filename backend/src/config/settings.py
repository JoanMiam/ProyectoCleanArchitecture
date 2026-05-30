from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = (
        "postgresql+asyncpg://inspections_user:inspections_pass@localhost:5432/inspections_db"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO / S3
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin123"
    s3_bucket: str = "evidences"

    # Evidence upload limits
    evidence_max_file_size_bytes: int = 10 * 1024 * 1024
    evidence_allowed_mime_types: str = "image/jpeg,image/png,image/webp,application/pdf"

    # Auth
    jwt_secret: str = "dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def allowed_evidence_mime_types(self) -> frozenset[str]:
        return frozenset(
            mime_type.strip().lower()
            for mime_type in self.evidence_allowed_mime_types.split(",")
            if mime_type.strip()
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
