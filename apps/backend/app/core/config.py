from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "LenQuant Website Fabric API"
    api_prefix: str = "/api"
    mongodb_uri: str = ""
    mongodb_db_name: str = "lenquant"
    session_secret: str = "replace-me"
    jwt_secret: str = "replace-with-a-secure-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24 * 7  # 7 days
    signup_code: str = ""
    verification_token_expiry_hours: int = 48
    password_reset_token_expiry_hours: int = 24
    require_email_verification: bool = True
    frontend_url: str = "http://localhost:3000"
    auth_allowlist_emails: str = "operator@example.com"
    auth_allowlist_domains: str = ""
    resend_api_key: str = ""
    resend_from_email: str = "noreply@lenquant.com"
    backend_cors_origins: str = "http://localhost:3000,http://localhost:3002"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str | None = None
    celery_default_queue: str = "lenquant"
    celery_task_always_eager: bool = True

    # LLM Provider: "gemini" (default for local) or "bedrock" (production)
    llm_provider: str = "gemini"

    # Gemini Configuration (used when llm_provider=gemini)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"
    gemini_vision_model: str = "gemini-2.0-flash"

    # Amazon Bedrock Configuration (used when llm_provider=bedrock)
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-6"
    bedrock_region: str = "us-east-1"
    bedrock_max_tokens: int = 32768  # Increased for full page code generation
    bedrock_timeout_seconds: int = (
        600  # 10 minutes for complex code generation (up from 5min)
    )
    # Fallback models if primary fails 2-3x or times out
    bedrock_fallback_models: list[str] = [
        "amazon.nova-pro-v1:0",
        "us.meta.llama4-scout-17b-instruct-v1:0",
        "mistral.mistral-large-2402-v1:0",
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "us.anthropic.claude-opus-4-6-v1",
    ]

    # Visual Redesign Configuration
    visual_redesign_enabled: bool = True
    visual_redesign_max_iterations: int = 2
    # Default visual redesign quality threshold. Tests assert this is 90
    # so keep the default aligned unless explicitly overridden via env.
    visual_redesign_quality_threshold: int = 90

    # Base URL for rendering public previews used by screenshot QA.
    # Can be overridden via PREVIEW_BASE_URL env var when the frontend
    # runs on a non-default port or host.
    preview_base_url: str = "http://localhost:3000"

    # Compiler service URL for TSX compilation
    compiler_service_url: str = "http://localhost:3001"

    # Asset download / caching settings
    asset_download_enabled: bool = False
    asset_storage_backend: str = "local"  # local | s3 | gcp
    asset_max_file_bytes: int = 1_500_000
    asset_max_aggregate_bytes: int = 12_000_000
    asset_download_timeout: int = 5
    asset_concurrent_downloads: int = 3
    asset_s3_bucket: str | None = None
    asset_s3_region: str = "us-east-1"
    asset_s3_prefix: str = "public/"
    asset_local_path: str = "/tmp/lenquant_assets"
    asset_retention_days: int = 7
    # GCP-specific settings (env names: ASSET_GCP_BUCKET, ASSET_GCP_PROJECT, GCP_SERVICE_ACCOUNT_KEY)
    asset_gcp_bucket: str | None = None
    asset_gcp_project: str | None = None
    # Accept either a JSON string for the service account or a filesystem path
    gcp_service_account_key: str | None = None
    # Signed URL expiry in seconds (ASSET_GCP_SIGNED_URL_EXPIRY)
    asset_gcp_signed_url_expiry: int = 60 * 60
    # Upload chunk size in bytes (ASSET_UPLOAD_CHUNK_SIZE)
    asset_upload_chunk_size: int = 8 * 1024 * 1024
    # Retry attempts for network/storage ops
    asset_retry_max_attempts: int = 5

    # Crawl budget / limits
    crawl_max_pages: int = 10
    crawl_budget_bytes: int = 3_000_000
    crawl_time_limit_seconds: int = 45
    extraction_store_raw_html: bool = True
    extraction_raw_html_max_chars: int = 500_000
    extraction_max_sections_per_page: int = 14
    extraction_enable_visual_capture: bool = True
    extraction_screenshot_width: int = 1440
    extraction_screenshot_height: int = 1200
    extraction_mobile_screenshot_width: int = 390
    extraction_mobile_screenshot_height: int = 844
    extraction_section_screenshot_limit: int = 8
    # Sitemap configuration
    sitemap_url: str | None = None  # Optional custom sitemap URL
    sitemap_gz_enabled: bool = True  # Try .gz compressed sitemaps

    # CTA safety config
    cta_allowed_verbs: str = (
        "Book,Schedule,Request,Explore,Contact,Learn,Discover,Get,Start"
    )
    cta_blocked_phrases: str = (
        "review the preview,see source notes,traceability,operator,admin,internal"
    )

    @property
    def allowlist_emails(self) -> List[str]:
        return [
            email.strip().lower()
            for email in self.auth_allowlist_emails.split(",")
            if email.strip()
        ]

    @property
    def allowlist_domains(self) -> List[str]:
        return [
            domain.strip().lower()
            for domain in self.auth_allowlist_domains.split(",")
            if domain.strip()
        ]

    @property
    def cors_origins(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    def validate_asset_settings(self) -> None:
        """Basic runtime validation for asset-related environment configuration.

        Raises RuntimeError with an actionable message if required settings are missing
        for the selected `asset_storage_backend`.
        """
        backend = (self.asset_storage_backend or "local").lower()
        if backend == "s3":
            if not self.asset_s3_bucket:
                raise RuntimeError(
                    "ASSET_S3_BUCKET is required when ASSET_STORAGE_BACKEND=s3"
                )
        elif backend == "gcp":
            if not self.asset_gcp_bucket:
                raise RuntimeError(
                    "ASSET_GCP_BUCKET is required when ASSET_STORAGE_BACKEND=gcp"
                )
            if not self.gcp_service_account_key:
                raise RuntimeError(
                    "GCP_SERVICE_ACCOUNT_KEY is required when ASSET_STORAGE_BACKEND=gcp"
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
