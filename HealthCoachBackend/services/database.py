import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()
print("DEBUG DATABASE_URL =", repr(os.getenv("DATABASE_URL")))


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# DATABASE_URL = os.getenv("DATABASE_URL")
# if not DATABASE_URL:
#    raise RuntimeError("DATABASE_URL is missing. Put it in your .env")
#
## pool_pre_ping évite les connexions mortes (utile avec du serverless / Neon)
# engine = create_engine(
#    DATABASE_URL,
#    pool_pre_ping=True,
# )
#
# SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
#
# Base = declarative_base()
#
#
# def get_db():
#    """
#    Dépendance FastAPI: yield une session DB et la ferme proprement.
#    """
#    db = SessionLocal()
#    try:
#        yield db
#    finally:
#        db.close()
