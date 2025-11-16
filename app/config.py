import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://short:short@db:5432/shortener")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SHORT_DOMAIN = os.getenv("SHORT_DOMAIN", "http://localhost:8000")
    REDIS_TTL_SECONDS = int(os.getenv("REDIS_TTL_SECONDS", 60*60*24))
    CLICK_FLUSH_KEY = "clicks:buffer"
