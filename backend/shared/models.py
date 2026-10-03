from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal, List
from datetime import datetime

class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    tz: str
    telegram_chat_id: Optional[str] = None
    enc_refresh_token: str
    dek_wrapped: str
    history_id: Optional[str] = None
    created_at: datetime

class RemindersSent(BaseModel):
    r1: bool = False
    r2: bool = False
    r3: bool = False
    r4: bool = False

class AppEvent(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    kind: Literal["interview", "online_assessment", "recruiter_call", "other"]
    company: Optional[str] = None
    role: Optional[str] = None
    start_utc: Optional[str] = None
    deadline_utc: Optional[str] = None
    link: Optional[str] = None
    thread_id: str
    message_id: str
    confidence: float = Field(ge=0, le=1)
    status: Literal["pending", "confirmed", "cancelled", "done"]
    reminders_sent: RemindersSent
    workflow_id: str
    embedding: Optional[List[float]] = None

class Audit(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    action: str
    at: datetime
