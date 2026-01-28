from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.schemas import ChatRequest

from agents.comparison_agent import comparison_response_agent
from agents.small_talks_agent import answer_small_talk
from agents.summary_agent import summary_response
from agents.factual_agent import factual_response
from agents.questions_agent import analyze_question
from services.intent_gatekeeper import intent_gatekeeper

from services.intent import (
    apply_backend_overrides,
    route_decision,
    compute_intensity_split,
)
from services.periods import snapshot_matches_iso
import pandas as pd
from services.memory import (
    store_signature,
    set_last_metric,
    get_last_metric,
    add_to_memory,
)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models.models import RunSession
from schemas.schemas import RunSessionCreate
from services.snapshot import build_snapshot_from_db

from api.runs import router as runs_router
from api.snapshots import router as snapshots_router
from api.health import router as health_router
from api.imports import router as imports_router
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
