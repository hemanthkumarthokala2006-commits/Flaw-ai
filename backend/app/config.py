import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "mysql+aiomysql://root:@localhost:3306/flaw_ai"
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL", "mysql+pymysql://root:@localhost:3306/flaw_ai"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "flaw-ai-secret-key")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )
    ALGORITHM: str = "HS256"
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")


settings = Settings()
