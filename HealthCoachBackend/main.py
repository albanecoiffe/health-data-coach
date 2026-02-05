from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.schemas import ChatRequest

import pandas as pd
from core.services.memory import (
    store_signature,
    set_last_metric,
    get_last_metric,
    add_to_memory,
)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import SessionLocal, engine
from core.models.RunSession import RunSession
from schemas.schemas import RunSessionCreate
from core.services.run_weeks.builder import rebuild_run_weeks_if_empty

from api.runs import router as runs_router
from api.snapshots import router as snapshots_router
from api.health import router as health_router
from api.imports_csv import router as imports_router
from api.errors import validation_exception_handler
from api.signature import router as signature_router
from api.chat import router as chat_router

app = FastAPI()

app.include_router(chat_router)

app.include_router(health_router)
app.include_router(snapshots_router)

app.include_router(runs_router)
app.include_router(imports_router)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(signature_router)


@app.get("/")
def root():
    return {"status": "ok"}


@app.on_event("startup")
def startup_tasks():
    rebuild_run_weeks_if_empty()
