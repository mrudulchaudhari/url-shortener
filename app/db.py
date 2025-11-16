from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from flask import current_app

Base = declarative_base()
SessionLocal = None
engine = None

def init_db(app):
    global engine, SessionLocal
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    app.db_engine = engine
    app.db_session = SessionLocal
    