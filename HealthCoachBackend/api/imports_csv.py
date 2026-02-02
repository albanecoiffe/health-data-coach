from fastapi import APIRouter, UploadFile, File
import pandas as pd

router = APIRouter()


@router.post("/upload-weeks-csv")
async def upload_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    df.to_csv("weeks_received.csv", index=False)
    return {"status": "ok", "rows": len(df)}


@router.post("/upload-sessions-csv")
async def upload_sessions_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    df.to_csv("sessions_received.csv", index=False)
    return {"status": "ok", "rows": len(df)}
