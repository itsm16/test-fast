from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from os import getenv

engine = create_engine(getenv("DATABASE_URL"), echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()