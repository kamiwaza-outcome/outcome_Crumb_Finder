from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "RFP Discovery System"
    VERSION: str = "2.0.0"

    # Kamiwaza integration
    KAMIWAZA_ENDPOINT: str = "http://host.docker.internal:7777/api/"
    KAMIWAZA_VERIFY_SSL: bool = False

    # Kamiwaza Platform (for App Garden)
    KAMIWAZA_API_URI: str = "https://host.docker.internal/api"
    KAMIWAZA_FORCE_HTTP: bool = True
    NODE_TLS_REJECT_UNAUTHORIZED: str = "0"

    # CORS settings (for local development)
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:51100"]

    # RFP Discovery Settings
    SAM_API_KEY: str = ""
    GOOGLE_SHEETS_CREDS_PATH: str = "credentials.json"
    SPREADSHEET_ID: Optional[str] = None  # Main sheet for qualified RFPs
    MAYBE_SPREADSHEET_ID: Optional[str] = None  # Sheet for maybe RFPs
    SPAM_SPREADSHEET_ID: Optional[str] = None  # Sheet for all RFPs
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = None  # Drive folder for RFP documents

    # RFP Processing Settings
    DEFAULT_MODEL_NAME: str = "llama-3.1-70b"  # Default Kamiwaza model
    DEFAULT_BATCH_SIZE: int = 10
    DEFAULT_MAX_RFPS: int = 200
    DEFAULT_DAYS_BACK: int = 3

    # Daemon Settings
    RFP_DAEMON_DATA_DIR: str = "data/rfp_daemon"
    RFP_DAEMON_LOG_RETENTION_DAYS: int = 7
    RFP_DAEMON_RUN_RETENTION_DAYS: int = 30

    # Circuit Breaker Settings
    CIRCUIT_BREAKER_THRESHOLD: int = 3
    CIRCUIT_BREAKER_TIMEOUT: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    return Settings()