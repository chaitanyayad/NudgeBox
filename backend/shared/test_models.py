import pytest
from backend.shared.models import User, AppEvent, Audit
from datetime import datetime
from pydantic import ValidationError

def test_user_validates():
    user_data = {
        "email": "test@example.com",
        "tz": "America/New_York",
        "enc_refresh_token": "enc",
        "dek_wrapped": "dek",
        "created_at": datetime.now()
    }
    user = User(**user_data)
    assert user.email == "test@example.com"

def test_event_validates():
    event_data = {
        "user_id": "u1",
        "kind": "interview",
        "company": "Acme",
        "thread_id": "t1",
        "message_id": "m1",
        "confidence": 0.9,
        "status": "pending",
        "reminders_sent": {},
        "workflow_id": "w1"
    }
    event = AppEvent(**event_data)
    assert event.kind == "interview"

def test_event_rejects_invalid_confidence():
    event_data = {
        "user_id": "u1",
        "kind": "interview",
        "company": "Acme",
        "thread_id": "t1",
        "message_id": "m1",
        "confidence": 1.5,
        "status": "pending",
        "reminders_sent": {},
        "workflow_id": "w1"
    }
    with pytest.raises(ValidationError):
        AppEvent(**event_data)
