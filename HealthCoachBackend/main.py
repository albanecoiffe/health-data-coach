from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api.chat import router as chat_router
from api.imports_csv import router as imports_router
from api.imports_apple import router as imports_apple_router
from api.errors import validation_exception_handler
from api.health import router as health_router
from api.runs import router as runs_router
from api.signature import router as signature_router
from api.snapshots import router as snapshots_router
from core.services.imports.sessions_csv import (
    auto_import_sessions_on_startup,
    start_csv_polling_worker,
)
from core.services.run_weeks.builder import rebuild_run_weeks_if_empty


def root():
    return {"status": "ok"}


def startup_tasks():
    rebuild_run_weeks_if_empty()
    result = auto_import_sessions_on_startup()
    print("📦 Startup CSV import:", result)
    poller = start_csv_polling_worker()
    print("🕒 CSV polling worker:", poller)


def create_app() -> FastAPI:
    app = FastAPI()

    app.include_router(chat_router)
    app.include_router(health_router)
    app.include_router(snapshots_router)
    app.include_router(runs_router)
    app.include_router(imports_router)
    app.include_router(imports_apple_router)
    app.include_router(signature_router)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_api_route("/", root, methods=["GET"])
    app.add_event_handler("startup", startup_tasks)

    return app


app = create_app()
