from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    meta: Optional[dict] = None


class RunSessionCreate(BaseModel):
    user_id: UUID
    start_time: datetime

    distance_km: float
    duration_min: float
    avg_hr: Optional[float] = None

    elevation_m: Optional[float] = None
    active_kcal: Optional[float] = None

    z1_min: float
    z2_min: float
    z3_min: float
    z4_min: float
    z5_min: float

    session_type: Optional[str] = None
    session_detail: Optional[str] = None


class RunSessionMetadataUpdate(BaseModel):
    user_id: UUID
    start_time: datetime
    session_type: Optional[str] = None
    session_detail: Optional[str] = None
