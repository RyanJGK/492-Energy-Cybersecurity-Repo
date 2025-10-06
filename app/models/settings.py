from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application runtime settings.

    Defaults prioritize read-only, simulation-first behavior for safety.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "OT-DER Telemetry & Simulation API"
    environment: str = "dev"

    # Safety flags
    read_only_mode: bool = True
    enable_simulation: bool = True

    # Optional integrations
    enable_db: bool = False
    db_dsn: str = "postgresql://postgres:postgres@localhost:5432/telemetry"

    enable_mqtt: bool = False
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_tls: bool = False

    enable_ray: bool = False
    ray_address: Optional[str] = None

    # OPA policy endpoint for guardrails
    opa_url: str = "http://localhost:8181/v1/data/control/allow"
    require_dual_approval: bool = True

    # Allowed actions when policy service is unavailable
    # Use default_factory to avoid mutable default list issues
    allowed_actions: List[str] = Field(default_factory=lambda: ["ingest", "simulate"])


settings = Settings()  # Singleton-style settings instance
