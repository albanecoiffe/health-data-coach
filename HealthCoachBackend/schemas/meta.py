from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class ChatMeta(BaseModel):
    session_id: str
    user_id: Optional[UUID] = None

    requested_start: Optional[str] = None
    requested_end: Optional[str] = None

    metric: Optional[str] = None
    reply_mode: Optional[str] = None
