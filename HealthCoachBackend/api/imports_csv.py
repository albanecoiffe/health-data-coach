from pathlib import Path

from fastapi import APIRouter, UploadFile, File
import pandas as pd

from core.services.imports.sessions_csv import (
    import_sessions_csv_file,
    import_sessions_dataframe,
    resolve_sessions_csv_path,
)

router = APIRouter()


@router.post("/upload-weeks-csv")
async def upload_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    df.to_csv("weeks_received.csv", index=False)
    return {"status": "ok", "rows": len(df)}


@router.post("/upload-sessions-csv")
@router.post("/api/upload-sessions-csv")
async def upload_sessions_csv(
    file: UploadFile = File(...),
    user_id: str | None = None,
    import_now: bool = True,
):
    content = await file.read()

    target_path = resolve_sessions_csv_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    Path(target_path).write_bytes(content)

    df = pd.read_csv(Path(target_path))
    payload = {
        "status": "stored",
        "rows": int(len(df)),
        "path": str(target_path),
    }

    if import_now:
        payload["import"] = import_sessions_dataframe(df, user_id=user_id)

    return payload


@router.post("/api/import-sessions-csv")
def import_saved_sessions_csv(
    user_id: str | None = None, csv_path: str | None = None
):
    return import_sessions_csv_file(csv_path=csv_path, user_id=user_id)
