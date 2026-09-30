from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/contentforge.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def _migrate(engine):
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(runs)"))]
            if "current_agent" not in cols:
                conn.execute(text("ALTER TABLE runs ADD COLUMN current_agent VARCHAR"))
                conn.commit()

try:
    Base.metadata.create_all(bind=engine)
    _migrate(engine)
except Exception:
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
