from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from backend.shared.env import settings
from backend.shared.db import get_db
from backend.api import auth

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

app = FastAPI(title="NudgeBox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/health")
async def health_check():
    try:
        db = await get_db()
        await db.command("ping")
        return {"status": "ok", "mongo": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to connect to database")

@app.get("/api/events")
async def get_events():
    db = await get_db()
    # Find all events, convert ObjectId to string
    cursor = db.events.find().sort("start_utc", 1)
    events = []
    
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    async for event in cursor:
        event["_id"] = str(event["_id"])
        # Format a local_time_str if missing or None
        if not event.get("local_time_str"):
            event["local_time_str"] = event.get("start_utc") or "TBD"
            
        try:
            # Safely parse ISO format, handling 'Z' suffix
            start_str = event.get("start_utc", "")
            if start_str.endswith("Z"):
                start_str = start_str[:-1] + "+00:00"
            event_time = datetime.fromisoformat(start_str)
            if event_time < now:
                continue
        except Exception:
            pass
            
        events.append(event)
    return events

@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"status": "logged_out"}

@app.post("/api/sync")
async def trigger_sync():
    import os
    from temporalio.client import Client
    from backend.worker.workflows import SyncMailboxWorkflow
    from backend.shared.db import get_db
    
    # Start the Temporal workflow
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    try:
        db = await get_db()
        # Find the authenticated user (for local dev, grab the first one)
        user = await db.users.find_one({})
        if not user:
            return {"status": "error", "error": "No user connected. Please Connect Gmail first."}
            
        user_id = str(user["_id"])
        
        client = await Client.connect(temporal_address)
        handle = await client.start_workflow(
            SyncMailboxWorkflow.run,
            user_id,
            id=f"sync-{user_id}",
            task_queue="nudgebox-tasks"
        )
        return {"status": "sync_started", "workflow_id": handle.id}
    except Exception as e:
        return {"status": "error", "error": str(e)}

from pydantic import BaseModel
class TelegramUpdate(BaseModel):
    chat_id: str

@app.post("/api/telegram")
async def link_telegram(payload: TelegramUpdate):
    db = await get_db()
    # In a real app we'd link this to the current logged in user
    # For now we'll just upsert it to a dummy user
    await db.users.update_one(
        {"user_id": "test-user-123"},
        {"$set": {"telegramChatId": payload.chat_id}},
        upsert=True
    )
    return {"status": "linked"}
