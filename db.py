import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


DATABASE_URL = os.environ.get('DATABASE_URL', "postgresql://postgres:pass@db:5432/urls")
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    """
    create and return a new SQLAlchemy session

    """
    return SessionLocal()


def init_db():
    """
    Create DB tables (for local/dev use).
    """

    Base.metadata.create_all(bind=engine)