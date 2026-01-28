from fastapi import APIRouter
from sqlalchemy import text, inspect
from database import engine

router = APIRouter()


@router.get("/health/db")
def db_health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"db": "ok"}


@router.get("/debug/tables")
def list_tables():
    inspector = inspect(engine)
    return inspector.get_table_names()
