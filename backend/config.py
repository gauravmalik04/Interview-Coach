from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directories
BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    """Application configuration settings loaded from environment or .env file."""
    
    # App Settings
    APP_NAME: str = "AI Interview Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Hugging Face Settings
    HF_API_TOKEN: Optional[str] = ""
    HF_MODEL_ID: str = "mistralai/Mistral-7B-Instruct-v0.2"
    
    # JWT & Auth Settings
    JWT_SECRET: str = "dev_jwt_secret_ai_interview_secure_key_2026_xyz"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database Settings
    SQLITE_DB_PATH: str = "ai_interview.db"
    SQLITE_CHECKPOINTS_PATH: str = "checkpoints.db"
    
    # Vector DB Settings
    CHROMA_PERSIST_PATH: str = str(BASE_DIR / "chroma_data")
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    
    # Question Loader Settings
    GITHUB_QUESTIONS_URL: str = "https://raw.githubusercontent.com/DopplerHQ/awesome-interview-questions/master/README.md"
    DATA_DIR: str = str(BASE_DIR / "data")
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]
    
    @property
    def database_url(self) -> str:
        """Constructs the asynchronous SQLite database connection URL."""
        db_path = BASE_DIR / self.SQLITE_DB_PATH
        return f"sqlite+aiosqlite:///{db_path.as_posix()}"

    @property
    def checkpoints_db_path(self) -> str:
        """Full path for LangGraph checkpoints SQLite database."""
        return str(BASE_DIR / self.SQLITE_CHECKPOINTS_PATH)

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton settings instance
settings = Settings()
